"""Workflow Sub-Agent Harness dispatch domain.

Pure-Python, deterministic, dependency-free first runtime slice for the
Workflow Sub-Agent Harness contract
(``docs/workflow-subagent-harness-contract.md`` /
``docs/workflow-subagent-usage-checklist.md`` /
``docs/workflows-subagent-harness-architecture.md``).

This module owns the typed shapes Prime issues and accepts when bounded
harness work runs in a separate workflow / sub-agent context:

- frozen domain dataclasses:
  :class:`WorkflowInputRecord`, :class:`WorkflowPromptBudget`,
  :class:`WorkflowGateContext`, :class:`WorkflowInputPacket`,
  :class:`WorkflowWorkOrder`, :class:`WorkflowHeartbeat`,
  :class:`WorkflowResultSummary`, :class:`WorkflowErrorSummary`,
  :class:`WorkflowResteerRequest`, :class:`WorkflowResteerChanges`,
  :class:`WorkflowPromotionDecision`;
- closed enums: :class:`WorkflowHarness`, :class:`WorkflowPhase`,
  :class:`WorkflowFailureKind`;
- pure dispatch helper :func:`dispatch_work_order` that invokes a registered
  fake/stub handler, converts handler exceptions to a
  :class:`WorkflowErrorSummary`, validates the result shape, enforces tier
  proof / gate requirements, handles :class:`WorkflowResteerRequest`, and
  never exposes heartbeat history in its return value;
- input / path / tool validation helpers for allowed paths, forbidden paths,
  summarize-only mode, timeout values, nesting cap, and bounded text fields;
- promotion / acceptance helper :func:`promote_workflow_result` that rejects
  tier-4 results without ``requires_human_gate=True``;
- prompt-drag guards that reject raw transcript / log / file / search return
  fields or unsafe free text before they can enter a result summary.

Hard rules enforced here (per contract):

- No live workflow execution, no process / session control, no model calls,
  no network, no UI / Electron / Bifrost behavior, no Echo / FileMap durable
  writes, no provider / account calls, no FileMap registration, no
  branch / worktree movement.
- Final Prime-visible return payloads never include heartbeat history, raw
  transcripts, raw logs, raw search / file bodies, free-text plans, or
  unsafe display content. Returning such content from a handler is a
  dispatch failure, not a successful result.
- Tier-3+ orders without ``gate_context`` are rejected before the handler
  is invoked.
- Tier-2+ results without a non-empty ``proof_trail`` are rejected after
  the handler returns and become a typed ``PROOF_UNAVAILABLE`` error.
- Tier-4 results without ``requires_human_gate=True`` are blocked at the
  promotion helper.
- Nesting depth (``parent`` chain) is hard-capped at
  :data:`WORKFLOW_NESTING_CAP`; attempts to exceed produce ``INPUT_INVALID``.
- Path scope inside :class:`WorkflowInputPacket` is rejected when ``inputs``
  reference paths outside ``allowed_paths`` or inside ``forbidden_paths``.
- Bounded text fields are length-capped and unsafe-marker-checked.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Callable, Optional, Union


# ---------------------------------------------------------------------------
# Bounds, sentinels, and unsafe markers
# ---------------------------------------------------------------------------

WORKFLOW_NESTING_CAP = 2

MIN_RISK_TIER = 1
MAX_RISK_TIER = 4

MAX_PROJECT_LENGTH = 48
MAX_GOAL_SUMMARY_LENGTH = 500
MAX_HEARTBEAT_SUMMARY_LENGTH = 200
MAX_RESULT_SUMMARY_LENGTH = 1000
MAX_ERROR_SUMMARY_LENGTH = 500
MAX_RESTEER_REASON_LENGTH = 300
MAX_NEXT_ACTION_LENGTH = 200
MAX_NOTES_LENGTH = 200
MAX_ACTION_LENGTH = 96
MAX_INTENT_LENGTH = 200
MAX_RESULT_SHAPE_LENGTH = 96
MAX_WORK_ORDER_ID_LENGTH = 96
MAX_SOURCE_LENGTH = 48
MAX_KIND_LENGTH = 48
MAX_REF_LENGTH = 256
MAX_SUMMARY_FIELD_LENGTH = 300
MAX_TOOL_NAME_LENGTH = 48
MAX_PATH_PREFIX_LENGTH = 256
MAX_PROOF_REF_LENGTH = 96
MAX_POLICY_DECISION_LENGTH = 32
MAX_DISPLAY_STRING_LENGTH = 1024
MAX_PAYLOAD_DEPTH = 6

MIN_TIME_BUDGET_SECONDS = 1
MAX_TIME_BUDGET_SECONDS = 60 * 60 * 6
MIN_HARD_TIMEOUT_SECONDS = 1
MAX_HARD_TIMEOUT_SECONDS = 60 * 60 * 12

MAX_INPUTS_PER_PACKET = 64
MAX_PATHS_PER_PACKET = 32
MAX_TOOLS_PER_PACKET = 16
MAX_OUTPUTS_PER_RESULT = 128
MAX_PARTIAL_OUTPUTS = 64
MAX_PROOF_TRAIL_ENTRIES = 64
MAX_RESTEER_INPUTS = 32
MAX_GATE_PROOF_HANDLES = 32

# Policy-decision vocabulary mirrored from
# ``meridian_core.cognition_policy`` shape names. Kept as a closed string
# set here so this slice does not import policy code.
_ALLOWED_POLICY_DECISIONS = frozenset({"ALLOW", "WARN", "DENY"})

# Free-text markers that signal a prompt-drag leak. Matched
# case-insensitively against any free-text field that flows back to Prime.
_UNSAFE_FREE_TEXT_MARKERS = (
    "raw_transcript",
    "raw transcript",
    "begin transcript",
    "end transcript",
    "begin chat",
    "raw_chat",
    "raw chat",
    "raw_search",
    "raw search",
    "raw_search_results",
    "raw_log",
    "raw logs",
    "raw stdout",
    "raw stderr",
    "stdout dump",
    "stderr dump",
    "raw_html",
    "raw html",
    "raw_css",
    "raw css",
    "<html",
    "<style",
    "<script",
    "browser_console",
    "browser console dump",
    "raw_file_body",
    "raw file body",
    "scratch_reasoning",
    "model_scratch",
    "model_payload",
    "model response:",
    "free_text_plan",
    "freeform plan:",
    "heartbeat_history",
    "api_key",
    "apikey",
    "bearer ",
    "authorization:",
    "credential",
    "password",
    "secret_key",
    "private_key",
    "git checkout",
    "git rebase",
    "git merge",
    "git reset",
    "git push",
    "worktree",
    "branch_movement",
    "scott_message:",
    "prime_message:",
)

# Field / mapping-key names that are not allowed in any handler return
# payload (output records, partial outputs, proof trail entries). The
# dispatch helper rejects any handler return that exposes one of these.
_UNSAFE_FIELD_NAMES = frozenset({
    "transcript",
    "transcripts",
    "raw_transcript",
    "raw_chat",
    "chat_log",
    "raw_log",
    "raw_logs",
    "log",
    "logs",
    "stdout",
    "stderr",
    "raw_stdout",
    "raw_stderr",
    "raw_file",
    "raw_file_body",
    "file_body",
    "file_bodies",
    "raw_html",
    "raw_css",
    "html_dump",
    "css_dump",
    "browser_console",
    "console_dump",
    "raw_search",
    "raw_search_results",
    "search_results_raw",
    "scratch",
    "scratch_reasoning",
    "model_scratch",
    "model_response_text",
    "free_text_plan",
    "plan_prose",
    "freeform_plan",
    "heartbeats",
    "heartbeat_history",
    "scott_message",
    "prime_message",
    "credentials",
    "api_key",
    "secret",
    "secrets",
    "bearer_token",
    "password",
    "private_key",
})

# Absolute-path prefixes that, if embedded in a display string, mean the
# string is leaking a real filesystem location.
_FILESYSTEM_PATH_PREFIXES = (
    "/tmp/",
    "/etc/",
    "/var/",
    "/usr/",
    "/home/",
    "/Users/",
    "/opt/",
    "/Library/",
    "/Volumes/",
    "/proc/",
    "/dev/",
    "/root/",
    "/mnt/",
    "/srv/",
)

# Characters permitted in repository-relative path prefixes.
_PATH_PREFIX_ALLOWED_EXTRA = (".", "-", "_", "/")
_IDENTIFIER_ALLOWED_EXTRA = (".", "-", "_")

# UTC timestamp bounds. The slice only accepts ISO-8601-ish UTC strings
# ending with ``Z`` — e.g. ``2026-06-07T16:20:00Z`` or
# ``2026-06-07T16:20:00.123456Z``. Local-time, offset (``+00:00``), or
# unbounded free text is rejected.
_UTC_TIMESTAMP_MIN_LENGTH = 20  # YYYY-MM-DDTHH:MM:SSZ
_UTC_TIMESTAMP_MAX_LENGTH = 27  # YYYY-MM-DDTHH:MM:SS.ffffffZ
_UTC_TIMESTAMP_MIN_YEAR = 2000
_UTC_TIMESTAMP_MAX_YEAR = 2199


# ---------------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------------

class WorkflowValidationError(ValueError):
    """Raised when a workflow domain object fails construction-time validation."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkflowHarness(Enum):
    """Closed set of harnesses that may own a workflow work order."""

    ECHO = "echo"
    ATLAS = "atlas"
    AEGIS = "aegis"
    RELAY = "relay"
    BIFROST = "bifrost"
    BEACON = "beacon"
    SESSION_LIFECYCLE = "session_lifecycle"


class WorkflowPhase(Enum):
    """Closed set of heartbeat phases a sub-agent may report."""

    STARTED = "started"
    WORKING = "working"
    WAITING_FOR_TOOL = "waiting_for_tool"
    WAITING_FOR_GATE = "waiting_for_gate"
    WARNING = "warning"
    FINALIZING = "finalizing"


class WorkflowFailureKind(Enum):
    """Closed set of typed failure kinds for ``WorkflowErrorSummary``."""

    TIMEOUT = "timeout"
    TOOL_DENIED = "tool_denied"
    INPUT_INVALID = "input_invalid"
    PROOF_UNAVAILABLE = "proof_unavailable"
    GATE_REQUIRED = "gate_required"
    INTERNAL_ERROR = "internal_error"
    RESTEER_REQUESTED = "resteer_requested"


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def _contains_unsafe_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _UNSAFE_FREE_TEXT_MARKERS)


def _looks_like_filesystem_path(value: str) -> bool:
    if not value:
        return False
    if (
        len(value) >= 3
        and value[0].isalpha()
        and value[1] == ":"
        and value[2] in ("\\", "/")
    ):
        return True
    if "\\" in value:
        return True
    if value.startswith("/"):
        return True
    lowered = value.lower()
    for prefix in _FILESYSTEM_PATH_PREFIXES:
        if prefix.lower() in lowered:
            return True
    return False


def _is_safe_free_text(value: str, *, max_length: int) -> bool:
    if len(value) > max_length:
        return False
    if "\x00" in value:
        return False
    if "\r" in value:
        return False
    if _contains_unsafe_marker(value):
        return False
    if _looks_like_filesystem_path(value):
        return False
    return True


def _validate_free_text(name: str, value: object, *, max_length: int,
                        allow_empty: bool = True) -> str:
    if value is None:
        if allow_empty:
            return ""
        raise WorkflowValidationError(f"{name} must be a non-empty string")
    if not isinstance(value, str):
        raise WorkflowValidationError(f"{name} must be a string")
    if not value:
        if allow_empty:
            return ""
        raise WorkflowValidationError(f"{name} must be a non-empty string")
    if not _is_safe_free_text(value, max_length=max_length):
        raise WorkflowValidationError(
            f"{name} contains unsafe content or exceeds bound"
        )
    return value


def _is_safe_identifier(value: str, *, max_length: int) -> bool:
    if not value or len(value) > max_length:
        return False
    for ch in value:
        if not (ch.isalnum() or ch in _IDENTIFIER_ALLOWED_EXTRA):
            return False
    return True


def _validate_identifier(name: str, value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise WorkflowValidationError(f"{name} must be a string")
    if not _is_safe_identifier(value, max_length=max_length):
        raise WorkflowValidationError(
            f"{name} must be a bounded identifier"
        )
    return value


def _is_valid_utc_timestamp(value: str) -> bool:
    """Strict deterministic check for an ISO UTC timestamp ending with ``Z``.

    Accepts:

    - ``YYYY-MM-DDTHH:MM:SSZ`` (length 20)
    - ``YYYY-MM-DDTHH:MM:SS.fZ`` ... ``YYYY-MM-DDTHH:MM:SS.ffffffZ``
      (length 22..27, 1–6 fractional digits)

    Rejects: missing ``Z`` suffix, ``+00:00`` offset, naive local-time
    strings, free text like ``"t"`` or ``"now"``, out-of-range
    year/month/day/hour/minute/second values, and lengths outside the
    accepted range. Pure-Python, dependency-free.
    """
    if not isinstance(value, str):
        return False
    if not value.endswith("Z"):
        return False
    if len(value) < _UTC_TIMESTAMP_MIN_LENGTH or len(value) > _UTC_TIMESTAMP_MAX_LENGTH:
        return False
    body = value[:-1]
    if "T" not in body:
        return False
    date_part, _, time_part = body.partition("T")
    if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
        return False
    year_s, month_s, day_s = date_part[:4], date_part[5:7], date_part[8:10]
    if not (year_s.isdigit() and month_s.isdigit() and day_s.isdigit()):
        return False
    year, month, day = int(year_s), int(month_s), int(day_s)
    if not (_UTC_TIMESTAMP_MIN_YEAR <= year <= _UTC_TIMESTAMP_MAX_YEAR):
        return False
    if not (1 <= month <= 12):
        return False
    if not (1 <= day <= 31):
        return False
    sec_part, dot, frac = time_part.partition(".")
    if len(sec_part) != 8 or sec_part[2] != ":" or sec_part[5] != ":":
        return False
    hour_s, minute_s, second_s = sec_part[:2], sec_part[3:5], sec_part[6:8]
    if not (hour_s.isdigit() and minute_s.isdigit() and second_s.isdigit()):
        return False
    hour, minute, second = int(hour_s), int(minute_s), int(second_s)
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 60):
        return False
    if dot:
        if not frac or len(frac) > 6 or not frac.isdigit():
            return False
    return True


def _is_safe_path_prefix(value: str) -> bool:
    if not value or len(value) > MAX_PATH_PREFIX_LENGTH:
        return False
    if value.startswith("/") or value.startswith("\\"):
        return False
    if value.startswith("~"):
        return False
    if ".." in value:
        return False
    if "\\" in value:
        return False
    if len(value) >= 2 and value[1] == ":":
        return False
    if value.startswith("./"):
        return False
    for ch in value:
        if not (ch.isalnum() or ch in _PATH_PREFIX_ALLOWED_EXTRA):
            return False
    return True


def _validate_path_prefix_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise WorkflowValidationError(f"{name} must be a tuple")
    if len(value) > MAX_PATHS_PER_PACKET:
        raise WorkflowValidationError(
            f"{name} exceeds the path-prefix cap"
        )
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            raise WorkflowValidationError(
                f"{name} entries must be strings"
            )
        if not _is_safe_path_prefix(entry):
            raise WorkflowValidationError(
                f"{name} entry {entry!r} is not a safe repo-relative prefix"
            )
        if entry in seen:
            raise WorkflowValidationError(
                f"{name} entry {entry!r} is duplicated"
            )
        seen.add(entry)
    return value


def _validate_tool_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise WorkflowValidationError(f"{name} must be a tuple")
    if len(value) > MAX_TOOLS_PER_PACKET:
        raise WorkflowValidationError(f"{name} exceeds tool cap")
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            raise WorkflowValidationError(f"{name} entries must be strings")
        if not _is_safe_identifier(entry, max_length=MAX_TOOL_NAME_LENGTH):
            raise WorkflowValidationError(
                f"{name} entry {entry!r} is not a safe tool name"
            )
        if entry in seen:
            raise WorkflowValidationError(
                f"{name} entry {entry!r} is duplicated"
            )
        seen.add(entry)
    return value


def _path_matches_prefix(path: str, prefix: str) -> bool:
    """Segment-aware path prefix match.

    Exact match (``path == prefix``) is allowed. A child path requires a
    slash boundary so that prefix ``src/atlas`` does not match
    ``src/atlas2/file.py`` or ``src/atlas-secret/file.py`` (raw
    ``str.startswith`` would have). Prefixes that already end with ``/``
    keep that slash boundary built in.
    """
    if not prefix:
        return False
    if path == prefix:
        return True
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path.startswith(prefix + "/")


def is_path_in_scope(
    path: str,
    *,
    allowed_paths: tuple[str, ...],
    forbidden_paths: tuple[str, ...],
) -> bool:
    """Return whether ``path`` is inside ``allowed_paths`` and not inside
    ``forbidden_paths``.

    Forbidden prefixes always win — a path matching any forbidden prefix is
    denied even when it also matches an allowed prefix. This mirrors the
    contract rule "``forbidden_paths`` overlap with ``allowed_paths``
    always denies the forbidden subset." Matching is segment-aware
    (see :func:`_path_matches_prefix`); a sibling escape like
    ``src/atlas2/file.py`` against prefix ``src/atlas`` is denied.
    """
    if not isinstance(path, str) or not path:
        return False
    if not _is_safe_path_prefix(path):
        return False
    for forbidden in forbidden_paths:
        if _path_matches_prefix(path, forbidden):
            return False
    for allowed in allowed_paths:
        if _path_matches_prefix(path, allowed):
            return True
    return False


# ---------------------------------------------------------------------------
# Prompt-drag payload validation (handler returns)
# ---------------------------------------------------------------------------

def _is_safe_output_string(value: str) -> bool:
    if len(value) > MAX_DISPLAY_STRING_LENGTH:
        return False
    if "\x00" in value:
        return False
    if _contains_unsafe_marker(value):
        return False
    # Output strings may include forward-slash refs but must not be raw
    # absolute filesystem paths.
    if _looks_like_filesystem_path(value):
        return False
    return True


def _validate_safe_payload(name: str, value: object, *, depth: int = 0) -> None:
    """Recursively validate a handler-return payload value.

    Rejects: unsafe field/key names, unsafe free-text content, oversized
    strings, raw bytes, raw filesystem paths, and unbounded recursion.
    """
    if depth > MAX_PAYLOAD_DEPTH:
        raise WorkflowValidationError(
            f"{name} payload nesting exceeds {MAX_PAYLOAD_DEPTH}"
        )
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str):
        if not _is_safe_output_string(value):
            raise WorkflowValidationError(
                f"{name} contains unsafe / oversized string content"
            )
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise WorkflowValidationError(
            f"{name} contains raw bytes; payloads must be structured text"
        )
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise WorkflowValidationError(
                    f"{name} mapping keys must be strings"
                )
            if k.lower() in _UNSAFE_FIELD_NAMES:
                raise WorkflowValidationError(
                    f"{name} payload exposes forbidden field {k!r}"
                )
            _validate_safe_payload(f"{name}.{k}", v, depth=depth + 1)
        return
    if isinstance(value, tuple):
        for idx, item in enumerate(value):
            _validate_safe_payload(f"{name}[{idx}]", item, depth=depth + 1)
        return
    if isinstance(value, list):
        # Handlers are required to return tuples for ordered payloads;
        # mutable lists are rejected so dispatch results stay immutable.
        raise WorkflowValidationError(
            f"{name} contains a list; structured payloads must be tuples"
        )
    if isinstance(value, set) or isinstance(value, frozenset):
        raise WorkflowValidationError(
            f"{name} contains a set; payloads must be ordered tuples or mappings"
        )
    if is_dataclass(value):
        # Walk dataclass fields with their declared names.
        for f in fields(value):
            if f.name.lower() in _UNSAFE_FIELD_NAMES:
                raise WorkflowValidationError(
                    f"{name} payload exposes forbidden field {f.name!r}"
                )
            _validate_safe_payload(
                f"{name}.{f.name}",
                getattr(value, f.name),
                depth=depth + 1,
            )
        return
    if isinstance(value, Enum):
        return
    raise WorkflowValidationError(
        f"{name} contains unsupported payload type {type(value).__name__!r}"
    )


# ---------------------------------------------------------------------------
# Input packet pieces
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowInputRecord:
    """One typed entry inside :class:`WorkflowInputPacket.inputs`.

    ``source`` tags the origin (e.g. ``"echo"``, ``"atlas"``, ``"scott"``).
    ``kind`` declares the entry shape — common values are ``"memory_hit"``,
    ``"atlas_hit"``, ``"file_path"``, and ``"config"``. When
    ``kind == "file_path"`` the entry's ``ref`` must satisfy the packet's
    allowed / forbidden path scope.
    """

    source: str
    kind: str
    ref: str = ""
    summary: str = ""

    def __post_init__(self) -> None:
        _validate_identifier("input.source", self.source,
                             max_length=MAX_SOURCE_LENGTH)
        _validate_identifier("input.kind", self.kind,
                             max_length=MAX_KIND_LENGTH)
        if not isinstance(self.ref, str):
            raise WorkflowValidationError("input.ref must be a string")
        if self.ref:
            if len(self.ref) > MAX_REF_LENGTH:
                raise WorkflowValidationError(
                    "input.ref exceeds the bounded length"
                )
            if _contains_unsafe_marker(self.ref):
                raise WorkflowValidationError(
                    "input.ref contains unsafe content"
                )
            if "\n" in self.ref or "\r" in self.ref or "\x00" in self.ref:
                raise WorkflowValidationError(
                    "input.ref must be a single bounded line"
                )
        _validate_free_text(
            "input.summary",
            self.summary,
            max_length=MAX_SUMMARY_FIELD_LENGTH,
        )


@dataclass(frozen=True)
class WorkflowPromptBudget:
    """Carry-over of the calling Relay ``PromptBudgetPlan`` cap.

    Pure value object — this slice does not import Relay. Both token caps
    must be positive integers.
    """

    max_prompt_tokens: int
    max_response_tokens: int
    notes: str = ""

    def __post_init__(self) -> None:
        for name, val in (
            ("max_prompt_tokens", self.max_prompt_tokens),
            ("max_response_tokens", self.max_response_tokens),
        ):
            if not isinstance(val, int) or isinstance(val, bool):
                raise WorkflowValidationError(f"{name} must be an int")
            if val <= 0:
                raise WorkflowValidationError(f"{name} must be > 0")
        _validate_free_text(
            "prompt_budget.notes",
            self.notes,
            max_length=MAX_NOTES_LENGTH,
        )


@dataclass(frozen=True)
class WorkflowGateContext:
    """Tier-2+ gate context carried by Prime into the input packet.

    ``policy_decision`` must be one of :data:`_ALLOWED_POLICY_DECISIONS`
    (``ALLOW`` / ``WARN`` / ``DENY``). ``proof_handles`` is the structured
    set of proof refs the sub-agent must produce or reference.
    """

    policy_decision: str
    proof_handles: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.policy_decision, str):
            raise WorkflowValidationError(
                "gate_context.policy_decision must be a string"
            )
        if self.policy_decision not in _ALLOWED_POLICY_DECISIONS:
            raise WorkflowValidationError(
                "gate_context.policy_decision is outside the allowed set"
            )
        if not isinstance(self.proof_handles, tuple):
            raise WorkflowValidationError(
                "gate_context.proof_handles must be a tuple"
            )
        if len(self.proof_handles) > MAX_GATE_PROOF_HANDLES:
            raise WorkflowValidationError(
                "gate_context.proof_handles exceeds bound"
            )
        seen: set[str] = set()
        for handle in self.proof_handles:
            if not isinstance(handle, str):
                raise WorkflowValidationError(
                    "gate_context.proof_handles entries must be strings"
                )
            if not _is_safe_identifier(handle, max_length=MAX_PROOF_REF_LENGTH):
                raise WorkflowValidationError(
                    "gate_context.proof_handles entry is not a safe ref"
                )
            if handle in seen:
                raise WorkflowValidationError(
                    "gate_context.proof_handles contains a duplicate"
                )
            seen.add(handle)
        _validate_free_text(
            "gate_context.notes",
            self.notes,
            max_length=MAX_NOTES_LENGTH,
        )


@dataclass(frozen=True)
class WorkflowInputPacket:
    """The only context the workflow sub-agent receives.

    Immutable. The sub-agent has no implicit access to Prime's memory,
    conversation, or Scott's chat — only what is declared here.
    """

    project: str
    goal_summary: str
    inputs: tuple[WorkflowInputRecord, ...]
    allowed_tools: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    prompt_budget: WorkflowPromptBudget
    gate_context: Optional[WorkflowGateContext] = None

    def __post_init__(self) -> None:
        _validate_identifier(
            "input.project", self.project, max_length=MAX_PROJECT_LENGTH,
        )
        _validate_free_text(
            "input.goal_summary",
            self.goal_summary,
            max_length=MAX_GOAL_SUMMARY_LENGTH,
            allow_empty=False,
        )
        if not isinstance(self.inputs, tuple):
            raise WorkflowValidationError("input.inputs must be a tuple")
        if len(self.inputs) > MAX_INPUTS_PER_PACKET:
            raise WorkflowValidationError(
                "input.inputs exceeds the per-packet cap"
            )
        for entry in self.inputs:
            if not isinstance(entry, WorkflowInputRecord):
                raise WorkflowValidationError(
                    "input.inputs entries must be WorkflowInputRecord"
                )
        _validate_tool_tuple("input.allowed_tools", self.allowed_tools)
        _validate_path_prefix_tuple("input.allowed_paths", self.allowed_paths)
        _validate_path_prefix_tuple(
            "input.forbidden_paths", self.forbidden_paths,
        )
        for entry in self.inputs:
            if entry.kind == "file_path":
                if not is_path_in_scope(
                    entry.ref,
                    allowed_paths=self.allowed_paths,
                    forbidden_paths=self.forbidden_paths,
                ):
                    raise WorkflowValidationError(
                        f"input.inputs file_path ref {entry.ref!r} is outside "
                        "allowed_paths or inside forbidden_paths"
                    )
        if not isinstance(self.prompt_budget, WorkflowPromptBudget):
            raise WorkflowValidationError(
                "input.prompt_budget must be a WorkflowPromptBudget"
            )
        if self.gate_context is not None and not isinstance(
            self.gate_context, WorkflowGateContext,
        ):
            raise WorkflowValidationError(
                "input.gate_context must be a WorkflowGateContext or None"
            )

    @property
    def is_summarize_only(self) -> bool:
        """Whether this packet is in summarize-only mode.

        An empty ``allowed_tools`` tuple means the sub-agent may not invoke
        tools — it must summarize only what is already in ``inputs``.
        """
        return len(self.allowed_tools) == 0


# ---------------------------------------------------------------------------
# Work order
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowWorkOrder:
    """The complete, self-contained instruction to a workflow sub-agent.

    Immutable. A reissue is a new order with a new id.
    """

    work_order_id: str
    harness: WorkflowHarness
    action: str
    intent: str
    risk_tier: int
    input: WorkflowInputPacket
    expected_result_shape: str
    time_budget_seconds: int
    hard_timeout_seconds: int
    created_at: str
    parent_work_order_id: str = ""
    depth: int = 0

    def __post_init__(self) -> None:
        _validate_identifier(
            "work_order_id",
            self.work_order_id,
            max_length=MAX_WORK_ORDER_ID_LENGTH,
        )
        if not isinstance(self.harness, WorkflowHarness):
            raise WorkflowValidationError("harness must be a WorkflowHarness")
        if not isinstance(self.action, str) or not self.action:
            raise WorkflowValidationError("action must be a non-empty string")
        if len(self.action) > MAX_ACTION_LENGTH:
            raise WorkflowValidationError("action exceeds bound")
        # action vocabulary is per-harness; we only enforce shape here:
        # bounded length, dot-separated identifier, no whitespace, no
        # unsafe markers.
        for ch in self.action:
            if not (ch.isalnum() or ch in _IDENTIFIER_ALLOWED_EXTRA):
                raise WorkflowValidationError(
                    "action must be a dot-separated identifier"
                )
        _validate_free_text(
            "intent", self.intent,
            max_length=MAX_INTENT_LENGTH, allow_empty=False,
        )
        if not isinstance(self.risk_tier, int) or isinstance(self.risk_tier, bool):
            raise WorkflowValidationError("risk_tier must be an int")
        if not MIN_RISK_TIER <= self.risk_tier <= MAX_RISK_TIER:
            raise WorkflowValidationError(
                f"risk_tier must lie within [{MIN_RISK_TIER}, {MAX_RISK_TIER}]"
            )
        if not isinstance(self.input, WorkflowInputPacket):
            raise WorkflowValidationError(
                "input must be a WorkflowInputPacket"
            )
        _validate_identifier(
            "expected_result_shape",
            self.expected_result_shape,
            max_length=MAX_RESULT_SHAPE_LENGTH,
        )
        for name, val, lo, hi in (
            ("time_budget_seconds", self.time_budget_seconds,
             MIN_TIME_BUDGET_SECONDS, MAX_TIME_BUDGET_SECONDS),
            ("hard_timeout_seconds", self.hard_timeout_seconds,
             MIN_HARD_TIMEOUT_SECONDS, MAX_HARD_TIMEOUT_SECONDS),
        ):
            if not isinstance(val, int) or isinstance(val, bool):
                raise WorkflowValidationError(f"{name} must be an int")
            if not lo <= val <= hi:
                raise WorkflowValidationError(
                    f"{name} must lie within [{lo}, {hi}]"
                )
        if self.time_budget_seconds > self.hard_timeout_seconds:
            raise WorkflowValidationError(
                "time_budget_seconds must not exceed hard_timeout_seconds"
            )
        if not isinstance(self.created_at, str) or not self.created_at:
            raise WorkflowValidationError(
                "created_at must be a non-empty timestamp string"
            )
        if not _is_valid_utc_timestamp(self.created_at):
            raise WorkflowValidationError(
                "created_at must be an ISO UTC timestamp ending with 'Z' "
                "(e.g. 2026-06-07T16:20:00Z)"
            )
        if not isinstance(self.parent_work_order_id, str):
            raise WorkflowValidationError(
                "parent_work_order_id must be a string"
            )
        if self.parent_work_order_id:
            if not _is_safe_identifier(
                self.parent_work_order_id,
                max_length=MAX_WORK_ORDER_ID_LENGTH,
            ):
                raise WorkflowValidationError(
                    "parent_work_order_id is not a safe identifier"
                )
        if not isinstance(self.depth, int) or isinstance(self.depth, bool):
            raise WorkflowValidationError("depth must be an int")
        if self.depth < 0 or self.depth > WORKFLOW_NESTING_CAP:
            raise WorkflowValidationError(
                f"depth must lie within [0, {WORKFLOW_NESTING_CAP}]"
            )
        if self.depth > 0 and not self.parent_work_order_id:
            raise WorkflowValidationError(
                "nested orders (depth > 0) require parent_work_order_id"
            )
        if self.depth == 0 and self.parent_work_order_id:
            raise WorkflowValidationError(
                "depth == 0 orders must not carry parent_work_order_id"
            )


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowHeartbeat:
    """Lightweight, operational status update from a running sub-agent.

    Heartbeats are operational, not narrative. They are never stored in
    Echo, never injected into Prime's prompt, and never aggregated into
    the dispatch return value.
    """

    work_order_id: str
    sequence: int
    emitted_at: str
    phase: WorkflowPhase
    summary: str
    progress_estimate: Optional[float] = None
    next_action: str = ""

    def __post_init__(self) -> None:
        _validate_identifier(
            "heartbeat.work_order_id",
            self.work_order_id,
            max_length=MAX_WORK_ORDER_ID_LENGTH,
        )
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise WorkflowValidationError(
                "heartbeat.sequence must be an int"
            )
        if self.sequence < 0:
            raise WorkflowValidationError(
                "heartbeat.sequence must be non-negative"
            )
        if not isinstance(self.emitted_at, str) or not self.emitted_at:
            raise WorkflowValidationError(
                "heartbeat.emitted_at must be a non-empty string"
            )
        if not _is_valid_utc_timestamp(self.emitted_at):
            raise WorkflowValidationError(
                "heartbeat.emitted_at must be an ISO UTC timestamp ending "
                "with 'Z' (e.g. 2026-06-07T16:21:00Z)"
            )
        if not isinstance(self.phase, WorkflowPhase):
            raise WorkflowValidationError(
                "heartbeat.phase must be a WorkflowPhase"
            )
        _validate_free_text(
            "heartbeat.summary",
            self.summary,
            max_length=MAX_HEARTBEAT_SUMMARY_LENGTH,
            allow_empty=False,
        )
        if self.progress_estimate is not None:
            if isinstance(self.progress_estimate, bool):
                raise WorkflowValidationError(
                    "heartbeat.progress_estimate must be a float in [0, 1]"
                )
            if not isinstance(self.progress_estimate, (int, float)):
                raise WorkflowValidationError(
                    "heartbeat.progress_estimate must be numeric"
                )
            if not 0.0 <= float(self.progress_estimate) <= 1.0:
                raise WorkflowValidationError(
                    "heartbeat.progress_estimate must lie within [0, 1]"
                )
        _validate_free_text(
            "heartbeat.next_action",
            self.next_action,
            max_length=MAX_NEXT_ACTION_LENGTH,
        )


# ---------------------------------------------------------------------------
# Resteer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowResteerChanges:
    """Structured delta a sub-agent suggests when it cannot finish the
    original order but believes a tighter one would succeed.

    Tuple-override fields (``allowed_paths``, ``forbidden_paths``,
    ``allowed_tools``) use tri-state semantics:

    - ``None`` (the default) means "no change" — :func:`apply_resteer`
      passes the original packet's value through.
    - A tuple (including the empty tuple ``()``) means "explicit
      override" — :func:`apply_resteer` replaces the original packet's
      value, even when the override is the empty tuple (e.g. force
      summarize-only via ``allowed_tools=()`` or intentionally clear
      ``forbidden_paths``).

    Other fields use the default-is-no-change convention: empty string
    for string fields, ``0`` for ``risk_tier`` / timeouts.
    ``additional_inputs`` is always appended to the original packet's
    ``inputs`` (an empty tuple means "no additions").

    The delta is intentionally not a freeform plan — Prime applies the
    delta to construct a new :class:`WorkflowWorkOrder` via
    :func:`apply_resteer`.
    """

    action: str = ""
    intent: str = ""
    expected_result_shape: str = ""
    risk_tier: int = 0
    allowed_paths: Optional[tuple[str, ...]] = None
    forbidden_paths: Optional[tuple[str, ...]] = None
    allowed_tools: Optional[tuple[str, ...]] = None
    additional_inputs: tuple[WorkflowInputRecord, ...] = ()
    time_budget_seconds: int = 0
    hard_timeout_seconds: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        if self.action:
            _validate_identifier(
                "resteer.action", self.action, max_length=MAX_ACTION_LENGTH,
            )
        if self.intent:
            _validate_free_text(
                "resteer.intent", self.intent,
                max_length=MAX_INTENT_LENGTH,
            )
        if self.expected_result_shape:
            _validate_identifier(
                "resteer.expected_result_shape",
                self.expected_result_shape,
                max_length=MAX_RESULT_SHAPE_LENGTH,
            )
        if not isinstance(self.risk_tier, int) or isinstance(self.risk_tier, bool):
            raise WorkflowValidationError("resteer.risk_tier must be an int")
        if self.risk_tier != 0 and not (
            MIN_RISK_TIER <= self.risk_tier <= MAX_RISK_TIER
        ):
            raise WorkflowValidationError(
                "resteer.risk_tier must be 0 (no change) or a valid tier"
            )
        if self.allowed_paths is not None:
            _validate_path_prefix_tuple(
                "resteer.allowed_paths", self.allowed_paths,
            )
        if self.forbidden_paths is not None:
            _validate_path_prefix_tuple(
                "resteer.forbidden_paths", self.forbidden_paths,
            )
        if self.allowed_tools is not None:
            _validate_tool_tuple(
                "resteer.allowed_tools", self.allowed_tools,
            )
        if not isinstance(self.additional_inputs, tuple):
            raise WorkflowValidationError(
                "resteer.additional_inputs must be a tuple"
            )
        if len(self.additional_inputs) > MAX_RESTEER_INPUTS:
            raise WorkflowValidationError(
                "resteer.additional_inputs exceeds bound"
            )
        for entry in self.additional_inputs:
            if not isinstance(entry, WorkflowInputRecord):
                raise WorkflowValidationError(
                    "resteer.additional_inputs entries must be "
                    "WorkflowInputRecord"
                )
        for name, val in (
            ("resteer.time_budget_seconds", self.time_budget_seconds),
            ("resteer.hard_timeout_seconds", self.hard_timeout_seconds),
        ):
            if not isinstance(val, int) or isinstance(val, bool):
                raise WorkflowValidationError(f"{name} must be an int")
            if val < 0:
                raise WorkflowValidationError(f"{name} must be >= 0")
        _validate_free_text(
            "resteer.notes", self.notes, max_length=MAX_NOTES_LENGTH,
        )


@dataclass(frozen=True)
class WorkflowResteerRequest:
    """A sub-agent's recommendation that Prime issue a tighter / different
    bounded order.

    Restart vs. resteer mirrors ``docs/prime-restart-resteer-logic.md``:
    *restart* reissues the same order in a fresh sub-agent context;
    *resteer* requires Prime to construct a new order from this delta.
    """

    original_work_order_id: str
    reason: str
    suggested_changes: WorkflowResteerChanges
    do_not_retry: bool = False

    def __post_init__(self) -> None:
        _validate_identifier(
            "resteer.original_work_order_id",
            self.original_work_order_id,
            max_length=MAX_WORK_ORDER_ID_LENGTH,
        )
        _validate_free_text(
            "resteer.reason",
            self.reason,
            max_length=MAX_RESTEER_REASON_LENGTH,
            allow_empty=False,
        )
        if not isinstance(self.suggested_changes, WorkflowResteerChanges):
            raise WorkflowValidationError(
                "resteer.suggested_changes must be a WorkflowResteerChanges"
            )
        if not isinstance(self.do_not_retry, bool):
            raise WorkflowValidationError(
                "resteer.do_not_retry must be a bool"
            )


# ---------------------------------------------------------------------------
# Result / error summaries
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowResultSummary:
    """The final, typed success return from a sub-agent.

    ``summary`` is the **only** free-text field Prime is shown by default.
    ``outputs`` is a tuple of structured records matching ``result_shape``
    — never raw prose, raw transcripts, raw logs, raw search results, or
    raw file bodies (the dispatch helper rejects those before this object
    leaves the workflow context).
    """

    work_order_id: str
    harness: WorkflowHarness
    result_shape: str
    summary: str
    outputs: tuple = ()
    proof_trail: tuple[str, ...] = ()
    tokens_used: int = 0
    time_used_seconds: float = 0.0
    next_action_recommendation: str = ""
    requires_human_gate: bool = False

    def __post_init__(self) -> None:
        _validate_identifier(
            "result.work_order_id",
            self.work_order_id,
            max_length=MAX_WORK_ORDER_ID_LENGTH,
        )
        if not isinstance(self.harness, WorkflowHarness):
            raise WorkflowValidationError(
                "result.harness must be a WorkflowHarness"
            )
        _validate_identifier(
            "result.result_shape",
            self.result_shape,
            max_length=MAX_RESULT_SHAPE_LENGTH,
        )
        _validate_free_text(
            "result.summary",
            self.summary,
            max_length=MAX_RESULT_SUMMARY_LENGTH,
            allow_empty=False,
        )
        if not isinstance(self.outputs, tuple):
            raise WorkflowValidationError("result.outputs must be a tuple")
        if len(self.outputs) > MAX_OUTPUTS_PER_RESULT:
            raise WorkflowValidationError(
                "result.outputs exceeds bound"
            )
        if not isinstance(self.proof_trail, tuple):
            raise WorkflowValidationError(
                "result.proof_trail must be a tuple"
            )
        if len(self.proof_trail) > MAX_PROOF_TRAIL_ENTRIES:
            raise WorkflowValidationError(
                "result.proof_trail exceeds bound"
            )
        for entry in self.proof_trail:
            if not isinstance(entry, str):
                raise WorkflowValidationError(
                    "result.proof_trail entries must be strings"
                )
            if not _is_safe_identifier(entry, max_length=MAX_PROOF_REF_LENGTH):
                raise WorkflowValidationError(
                    "result.proof_trail entry is not a safe ref"
                )
        if not isinstance(self.tokens_used, int) or isinstance(
            self.tokens_used, bool,
        ):
            raise WorkflowValidationError(
                "result.tokens_used must be an int"
            )
        if self.tokens_used < 0:
            raise WorkflowValidationError(
                "result.tokens_used must be non-negative"
            )
        if isinstance(self.time_used_seconds, bool) or not isinstance(
            self.time_used_seconds, (int, float),
        ):
            raise WorkflowValidationError(
                "result.time_used_seconds must be numeric"
            )
        if float(self.time_used_seconds) < 0.0:
            raise WorkflowValidationError(
                "result.time_used_seconds must be non-negative"
            )
        _validate_free_text(
            "result.next_action_recommendation",
            self.next_action_recommendation,
            max_length=MAX_NEXT_ACTION_LENGTH,
        )
        if not isinstance(self.requires_human_gate, bool):
            raise WorkflowValidationError(
                "result.requires_human_gate must be a bool"
            )


@dataclass(frozen=True)
class WorkflowErrorSummary:
    """The final, typed failure return from a sub-agent."""

    work_order_id: str
    harness: WorkflowHarness
    failure_kind: WorkflowFailureKind
    summary: str
    partial_outputs: tuple = ()
    proof_trail: tuple[str, ...] = ()
    resteer_request: Optional[WorkflowResteerRequest] = None
    tokens_used: int = 0
    time_used_seconds: float = 0.0

    def __post_init__(self) -> None:
        _validate_identifier(
            "error.work_order_id",
            self.work_order_id,
            max_length=MAX_WORK_ORDER_ID_LENGTH,
        )
        if not isinstance(self.harness, WorkflowHarness):
            raise WorkflowValidationError(
                "error.harness must be a WorkflowHarness"
            )
        if not isinstance(self.failure_kind, WorkflowFailureKind):
            raise WorkflowValidationError(
                "error.failure_kind must be a WorkflowFailureKind"
            )
        _validate_free_text(
            "error.summary",
            self.summary,
            max_length=MAX_ERROR_SUMMARY_LENGTH,
            allow_empty=False,
        )
        if not isinstance(self.partial_outputs, tuple):
            raise WorkflowValidationError(
                "error.partial_outputs must be a tuple"
            )
        if len(self.partial_outputs) > MAX_PARTIAL_OUTPUTS:
            raise WorkflowValidationError(
                "error.partial_outputs exceeds bound"
            )
        if not isinstance(self.proof_trail, tuple):
            raise WorkflowValidationError(
                "error.proof_trail must be a tuple"
            )
        if len(self.proof_trail) > MAX_PROOF_TRAIL_ENTRIES:
            raise WorkflowValidationError(
                "error.proof_trail exceeds bound"
            )
        for entry in self.proof_trail:
            if not isinstance(entry, str):
                raise WorkflowValidationError(
                    "error.proof_trail entries must be strings"
                )
            if not _is_safe_identifier(entry, max_length=MAX_PROOF_REF_LENGTH):
                raise WorkflowValidationError(
                    "error.proof_trail entry is not a safe ref"
                )
        if self.resteer_request is not None and not isinstance(
            self.resteer_request, WorkflowResteerRequest,
        ):
            raise WorkflowValidationError(
                "error.resteer_request must be a WorkflowResteerRequest or None"
            )
        if (
            self.failure_kind == WorkflowFailureKind.RESTEER_REQUESTED
            and self.resteer_request is None
        ):
            raise WorkflowValidationError(
                "RESTEER_REQUESTED errors must carry a resteer_request"
            )
        if not isinstance(self.tokens_used, int) or isinstance(
            self.tokens_used, bool,
        ):
            raise WorkflowValidationError(
                "error.tokens_used must be an int"
            )
        if self.tokens_used < 0:
            raise WorkflowValidationError(
                "error.tokens_used must be non-negative"
            )
        if isinstance(self.time_used_seconds, bool) or not isinstance(
            self.time_used_seconds, (int, float),
        ):
            raise WorkflowValidationError(
                "error.time_used_seconds must be numeric"
            )
        if float(self.time_used_seconds) < 0.0:
            raise WorkflowValidationError(
                "error.time_used_seconds must be non-negative"
            )


# ---------------------------------------------------------------------------
# Promotion / acceptance decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowPromotionDecision:
    """Typed verdict from :func:`promote_workflow_result`.

    A workflow result may not silently change durable state — promotion of
    results goes through review / proof gates appropriate to the work
    order's risk tier (per contract §"Review and Proof Expectations").

    ``accepted=True`` means **every** gate this slice can verify is
    satisfied — including the explicit external signals the caller must
    supply for tier-3+ (Review Console pass) and tier-4 (Scott human
    approval). Defaulting those caller signals to False therefore blocks
    durable promotion of high-tier results by construction.

    Field semantics:

    - ``accepted``: True iff the caller may promote ``result`` into
      durable state right now.
    - ``reason``: human-readable explanation for the verdict.
    - ``policy_decision_required``: tier-2+ orders must carry a
      ``gate_context`` whose ``policy_decision == "ALLOW"`` before
      durable promotion.
    - ``requires_review_console``: tier-3+ promotion requires the
      caller-supplied ``review_console_pass=True``.
    - ``requires_human_gate``: tier-4 promotion requires the
      caller-supplied ``human_approval=True`` AND
      ``result.requires_human_gate=True`` on the result itself.
    """

    accepted: bool
    reason: str
    policy_decision_required: bool
    requires_review_console: bool
    requires_human_gate: bool


# ---------------------------------------------------------------------------
# Handler typing
# ---------------------------------------------------------------------------

HandlerReturn = Union[
    "WorkflowResultSummary",
    "WorkflowErrorSummary",
    "WorkflowResteerRequest",
]

WorkflowHandler = Callable[
    [WorkflowWorkOrder, Callable[[WorkflowHeartbeat], None]],
    HandlerReturn,
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _make_error(
    work_order: WorkflowWorkOrder,
    failure_kind: WorkflowFailureKind,
    summary: str,
    *,
    partial_outputs: tuple = (),
    proof_trail: tuple[str, ...] = (),
    resteer_request: Optional[WorkflowResteerRequest] = None,
) -> WorkflowErrorSummary:
    safe_summary = summary if summary else failure_kind.value
    # Defensive: redact any leak markers from the failure summary the
    # dispatch synthesizes from a handler exception.
    if not _is_safe_free_text(safe_summary, max_length=MAX_ERROR_SUMMARY_LENGTH):
        safe_summary = failure_kind.value
    return WorkflowErrorSummary(
        work_order_id=work_order.work_order_id,
        harness=work_order.harness,
        failure_kind=failure_kind,
        summary=safe_summary,
        partial_outputs=partial_outputs,
        proof_trail=proof_trail,
        resteer_request=resteer_request,
    )


def _validate_result_payloads(result: WorkflowResultSummary) -> None:
    _validate_safe_payload("result.outputs", result.outputs)
    _validate_safe_payload("result.proof_trail", result.proof_trail)
    _validate_safe_payload("result.summary", result.summary)
    _validate_safe_payload(
        "result.next_action_recommendation",
        result.next_action_recommendation,
    )


def _validate_error_payloads(error: WorkflowErrorSummary) -> None:
    _validate_safe_payload("error.partial_outputs", error.partial_outputs)
    _validate_safe_payload("error.proof_trail", error.proof_trail)
    _validate_safe_payload("error.summary", error.summary)


def dispatch_work_order(
    work_order: WorkflowWorkOrder,
    handler: WorkflowHandler,
    *,
    heartbeat_sink: Optional[Callable[[WorkflowHeartbeat], None]] = None,
) -> Union[WorkflowResultSummary, WorkflowErrorSummary]:
    """Invoke ``handler`` for ``work_order`` and return its typed summary.

    Pure / local. No live workflow execution, no process / session control,
    no model calls, no network. The handler is the fake / stub harness
    being tested.

    Guarantees:

    - Catches handler exceptions and converts them to
      :class:`WorkflowErrorSummary` with ``failure_kind=INTERNAL_ERROR``.
      The orchestrator never sees a bare exception bubble up.
    - Rejects tier-3+ orders without ``gate_context`` *before* the handler
      is invoked, returning ``failure_kind=GATE_REQUIRED``.
    - Rejects results whose ``result_shape`` does not equal the order's
      ``expected_result_shape`` (``failure_kind=INPUT_INVALID``).
    - Rejects tier-2+ results without a non-empty ``proof_trail``
      (``failure_kind=PROOF_UNAVAILABLE``).
    - Rejects results whose ``harness`` or ``work_order_id`` do not match
      the order (``failure_kind=INPUT_INVALID``).
    - Wraps a returned :class:`WorkflowResteerRequest` in a
      :class:`WorkflowErrorSummary` with
      ``failure_kind=RESTEER_REQUESTED``.
    - Heartbeats emitted via the sink never appear in the return value —
      :class:`WorkflowResultSummary` / :class:`WorkflowErrorSummary` carry
      no heartbeat list.
    - Rejects nested orders beyond :data:`WORKFLOW_NESTING_CAP`
      (``failure_kind=INPUT_INVALID``).
    - Rejects any handler return whose payload exposes a forbidden field
      name or carries raw transcript / log / file / search content
      (``failure_kind=INPUT_INVALID``).
    """
    if not isinstance(work_order, WorkflowWorkOrder):
        raise WorkflowValidationError(
            "dispatch_work_order requires a WorkflowWorkOrder"
        )
    if not callable(handler):
        raise WorkflowValidationError(
            "dispatch_work_order requires a callable handler"
        )

    if work_order.depth > WORKFLOW_NESTING_CAP:
        # Construction already enforces this; belt-and-suspenders.
        return _make_error(
            work_order,
            WorkflowFailureKind.INPUT_INVALID,
            "work order exceeds nesting cap",
        )

    if work_order.risk_tier >= 3 and work_order.input.gate_context is None:
        return _make_error(
            work_order,
            WorkflowFailureKind.GATE_REQUIRED,
            "tier-3+ order missing gate_context",
        )

    def _emit(hb: object) -> None:
        if not isinstance(hb, WorkflowHeartbeat):
            return
        if hb.work_order_id != work_order.work_order_id:
            return
        if heartbeat_sink is not None:
            heartbeat_sink(hb)

    try:
        raw = handler(work_order, _emit)
    except WorkflowValidationError as exc:
        return _make_error(
            work_order,
            WorkflowFailureKind.INPUT_INVALID,
            f"handler validation error: {exc}",
        )
    except Exception:
        return _make_error(
            work_order,
            WorkflowFailureKind.INTERNAL_ERROR,
            "handler raised an unhandled exception",
        )

    if isinstance(raw, WorkflowResteerRequest):
        # A raw resteer is normalized into an error summary so Prime never
        # has to inspect a third return shape from the dispatch helper.
        if raw.original_work_order_id != work_order.work_order_id:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "resteer request references a different work order",
            )
        return _make_error(
            work_order,
            WorkflowFailureKind.RESTEER_REQUESTED,
            "handler requested resteer",
            resteer_request=raw,
        )

    if isinstance(raw, WorkflowErrorSummary):
        if raw.work_order_id != work_order.work_order_id:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "error.work_order_id does not match the order",
            )
        if raw.harness != work_order.harness:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "error.harness does not match the order",
            )
        try:
            _validate_error_payloads(raw)
        except WorkflowValidationError as exc:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                f"error payload prompt-drag guard: {exc}",
            )
        return raw

    if isinstance(raw, WorkflowResultSummary):
        if raw.work_order_id != work_order.work_order_id:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "result.work_order_id does not match the order",
            )
        if raw.harness != work_order.harness:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "result.harness does not match the order",
            )
        if raw.result_shape != work_order.expected_result_shape:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "result_shape does not match expected_result_shape",
            )
        try:
            _validate_result_payloads(raw)
        except WorkflowValidationError as exc:
            return _make_error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                f"result payload prompt-drag guard: {exc}",
            )
        if work_order.risk_tier >= 2 and not raw.proof_trail:
            return _make_error(
                work_order,
                WorkflowFailureKind.PROOF_UNAVAILABLE,
                "tier-2+ result missing proof_trail",
            )
        if work_order.input.is_summarize_only:
            # In summarize-only mode the handler must not have surfaced
            # any tool-derived structured outputs that imply a tool call
            # — outputs may only restate or distill the packet inputs.
            # The dispatch layer cannot prove every handler honored this,
            # but it does reject the obvious leak shape: a non-empty
            # tuple of outputs paired with the empty allowed_tools cap.
            # Handlers signal summarize-only safety by returning a tuple
            # of distilled strings or the empty tuple. Structured payload
            # validation above already rejected unsafe shapes.
            pass
        return raw

    return _make_error(
        work_order,
        WorkflowFailureKind.INPUT_INVALID,
        "handler returned an unsupported shape",
    )


# ---------------------------------------------------------------------------
# Promotion / acceptance helper
# ---------------------------------------------------------------------------

def promote_workflow_result(
    work_order: WorkflowWorkOrder,
    result: Union[WorkflowResultSummary, WorkflowErrorSummary],
    *,
    review_console_pass: bool = False,
    human_approval: bool = False,
) -> WorkflowPromotionDecision:
    """Decide whether ``result`` may promote into durable state.

    Tier rules (per contract §"Review and Proof Expectations"):

    - **Tier 1**: accept the summary; no extra gate.
    - **Tier 2**: ``proof_trail`` must be non-empty (already enforced
      by dispatch) AND ``work_order.input.gate_context`` must be
      present with ``policy_decision == "ALLOW"``.
    - **Tier 3**: tier-2 conditions, plus the caller must explicitly
      supply ``review_console_pass=True`` (the Review Console lane
      recorded ``pass`` / ``no actionable findings``).
    - **Tier 4**: tier-3 conditions, plus the caller must explicitly
      supply ``human_approval=True`` AND the result itself must carry
      ``requires_human_gate=True``.

    Errors never promote — ``WorkflowErrorSummary`` always returns
    ``accepted=False``.

    Defaulting ``review_console_pass`` and ``human_approval`` to False
    blocks tier-3 / tier-4 durable promotion by construction; callers
    that have actually gathered those signals must pass them in
    explicitly.
    """
    if not isinstance(work_order, WorkflowWorkOrder):
        raise WorkflowValidationError(
            "promote_workflow_result requires a WorkflowWorkOrder"
        )
    if not isinstance(review_console_pass, bool):
        raise WorkflowValidationError(
            "review_console_pass must be a bool"
        )
    if not isinstance(human_approval, bool):
        raise WorkflowValidationError(
            "human_approval must be a bool"
        )

    tier = work_order.risk_tier
    policy_decision_required = tier >= 2
    requires_review_console = tier >= 3
    requires_human_gate = tier >= 4

    def _block(reason: str) -> WorkflowPromotionDecision:
        return WorkflowPromotionDecision(
            accepted=False,
            reason=reason,
            policy_decision_required=policy_decision_required,
            requires_review_console=requires_review_console,
            requires_human_gate=requires_human_gate,
        )

    if isinstance(result, WorkflowErrorSummary):
        return _block("errors never promote to durable state")
    if not isinstance(result, WorkflowResultSummary):
        raise WorkflowValidationError(
            "promote_workflow_result requires a result or error summary"
        )
    if result.work_order_id != work_order.work_order_id:
        return _block("result work_order_id does not match the order")
    if result.harness != work_order.harness:
        return _block("result harness does not match the order")

    if tier >= 2:
        if not result.proof_trail:
            return _block(
                "tier-2+ promotion requires a non-empty proof_trail"
            )
        gate_context = work_order.input.gate_context
        if gate_context is None:
            return _block(
                "tier-2+ promotion requires gate_context on the work order"
            )
        if gate_context.policy_decision != "ALLOW":
            return _block(
                "tier-2+ promotion requires gate_context.policy_decision "
                "== 'ALLOW'"
            )
    if tier >= 3 and not review_console_pass:
        return _block(
            "tier-3+ promotion requires caller-supplied review_console_pass=True"
        )
    if tier >= 4:
        if not result.requires_human_gate:
            return _block(
                "tier-4 promotion requires requires_human_gate=True on the result"
            )
        if not human_approval:
            return _block(
                "tier-4 promotion requires caller-supplied human_approval=True"
            )

    return WorkflowPromotionDecision(
        accepted=True,
        reason="result accepted for promotion",
        policy_decision_required=policy_decision_required,
        requires_review_console=requires_review_console,
        requires_human_gate=requires_human_gate,
    )


# ---------------------------------------------------------------------------
# Resteer application
# ---------------------------------------------------------------------------

def apply_resteer(
    original: WorkflowWorkOrder,
    changes: WorkflowResteerChanges,
    *,
    new_work_order_id: str,
    created_at: str,
) -> Union[WorkflowWorkOrder, WorkflowErrorSummary]:
    """Apply a structured resteer delta to ``original`` and return the new
    work order, or a typed ``INPUT_INVALID`` error if the result would be
    invalid (e.g. nesting cap exceeded).

    Pure / local — never mutates ``original``. Tuple-override fields
    (``allowed_paths``, ``forbidden_paths``, ``allowed_tools``) use the
    tri-state semantics documented on :class:`WorkflowResteerChanges`:
    ``None`` passes the original packet's value through; a tuple
    (including the empty tuple) replaces the original value. Tier may
    only decrease or stay the same.
    """
    if not isinstance(original, WorkflowWorkOrder):
        raise WorkflowValidationError(
            "apply_resteer requires a WorkflowWorkOrder"
        )
    if not isinstance(changes, WorkflowResteerChanges):
        raise WorkflowValidationError(
            "apply_resteer requires WorkflowResteerChanges"
        )

    new_tier = changes.risk_tier if changes.risk_tier else original.risk_tier
    if new_tier > original.risk_tier:
        return _make_error(
            original,
            WorkflowFailureKind.INPUT_INVALID,
            "resteer must not raise risk tier",
        )

    new_depth = original.depth + 1
    if new_depth > WORKFLOW_NESTING_CAP:
        return _make_error(
            original,
            WorkflowFailureKind.INPUT_INVALID,
            "resteer would exceed nesting cap",
        )

    base_packet = original.input
    new_allowed_paths = (
        base_packet.allowed_paths
        if changes.allowed_paths is None
        else changes.allowed_paths
    )
    new_forbidden_paths = (
        base_packet.forbidden_paths
        if changes.forbidden_paths is None
        else changes.forbidden_paths
    )
    new_allowed_tools = (
        base_packet.allowed_tools
        if changes.allowed_tools is None
        else changes.allowed_tools
    )
    new_inputs = base_packet.inputs + tuple(changes.additional_inputs)

    try:
        new_packet = WorkflowInputPacket(
            project=base_packet.project,
            goal_summary=base_packet.goal_summary,
            inputs=new_inputs,
            allowed_tools=new_allowed_tools,
            allowed_paths=new_allowed_paths,
            forbidden_paths=new_forbidden_paths,
            prompt_budget=base_packet.prompt_budget,
            gate_context=base_packet.gate_context,
        )
    except WorkflowValidationError as exc:
        return _make_error(
            original,
            WorkflowFailureKind.INPUT_INVALID,
            f"resteer produced an invalid packet: {exc}",
        )

    new_time_budget = (
        changes.time_budget_seconds if changes.time_budget_seconds
        else original.time_budget_seconds
    )
    new_hard_timeout = (
        changes.hard_timeout_seconds if changes.hard_timeout_seconds
        else original.hard_timeout_seconds
    )

    try:
        return WorkflowWorkOrder(
            work_order_id=new_work_order_id,
            harness=original.harness,
            action=changes.action or original.action,
            intent=changes.intent or original.intent,
            risk_tier=new_tier,
            input=new_packet,
            expected_result_shape=(
                changes.expected_result_shape or original.expected_result_shape
            ),
            time_budget_seconds=new_time_budget,
            hard_timeout_seconds=new_hard_timeout,
            created_at=created_at,
            parent_work_order_id=original.work_order_id,
            depth=new_depth,
        )
    except WorkflowValidationError as exc:
        return _make_error(
            original,
            WorkflowFailureKind.INPUT_INVALID,
            f"resteer produced an invalid order: {exc}",
        )


__all__ = (
    "WORKFLOW_NESTING_CAP",
    "MIN_RISK_TIER",
    "MAX_RISK_TIER",
    "WorkflowHarness",
    "WorkflowPhase",
    "WorkflowFailureKind",
    "WorkflowValidationError",
    "WorkflowInputRecord",
    "WorkflowPromptBudget",
    "WorkflowGateContext",
    "WorkflowInputPacket",
    "WorkflowWorkOrder",
    "WorkflowHeartbeat",
    "WorkflowResultSummary",
    "WorkflowErrorSummary",
    "WorkflowResteerChanges",
    "WorkflowResteerRequest",
    "WorkflowPromotionDecision",
    "WorkflowHandler",
    "HandlerReturn",
    "dispatch_work_order",
    "promote_workflow_result",
    "apply_resteer",
    "is_path_in_scope",
)
