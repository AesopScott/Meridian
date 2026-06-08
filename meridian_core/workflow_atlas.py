"""Atlas Workflow Adapter — first per-harness workflow consumer slice.

This module is the deterministic, dependency-free adapter that bridges the
promoted Atlas retrieval surface (``meridian_core.atlas``) and the promoted
Workflow Sub-Agent Harness dispatch contract
(``meridian_core.workflow_dispatch``). It provides:

- a work-order builder that encodes an :class:`AtlasQuery` as bounded
  :class:`WorkflowInputRecord` entries inside a :class:`WorkflowInputPacket`,
  using ``kind="file_path"`` for required paths so the promoted packet's
  ``allowed_paths``/``forbidden_paths`` scope is enforced on required paths
  by construction;
- a pure decoder that reconstructs an :class:`AtlasQuery` from a
  :class:`WorkflowWorkOrder`'s typed inputs;
- a handler factory that returns a workflow handler suitable for
  :func:`dispatch_work_order`. The handler does **not** close over an
  :class:`AtlasQuery` — it decodes the query from the order each call, so
  the handler reflects the work order's typed inputs and cannot diverge
  from them. The handler also filters FileMap candidates and fails closed
  on FileMap / DOC output paths against the work order's
  ``allowed_paths`` / ``forbidden_paths`` scope.

Adapter rules cleared in this slice:

- ``required_paths`` cannot bypass the promoted Workflow Dispatch scope
  rules: required paths are surfaced as ``kind="file_path"`` records that
  :class:`WorkflowInputPacket` validates against ``allowed_paths`` and
  ``forbidden_paths`` at construction.
- Display-safety rejection is end-to-end through
  :func:`dispatch_work_order`: the adapter never silently blanks unsafe
  ``title``/``reason``/``excerpt`` fields nor drops unsafe hits. Unsafe
  payload content surfaces as a dispatcher ``INPUT_INVALID`` failure on
  the work order.
- The handler reconstructs the :class:`AtlasQuery` from the order's typed
  inputs each invocation; it does not carry a sidecar query.
- Empty Atlas queries return a successful empty :class:`AtlasResult` (no
  hits, no missing paths), not a :class:`WorkflowResteerRequest`.
- The module imports only public symbols from ``workflow_dispatch``. It
  does not import or rely on private dispatch helpers.
- Result-shape compatibility with the promoted Atlas contract:
  ``hits``, ``missing_paths``, and ``truncated`` are preserved verbatim in
  :class:`AtlasResultRecord`; source attribution and ranking order are
  preserved by faithful conversion of each :class:`AtlasHit`.
- Echo compatibility: when an ``echo_store`` is injected into the handler
  factory, the adapter forwards it to ``meridian_core.atlas.query``;
  ``AtlasSource.ECHO`` hits with conceptual ``echo://`` paths flow through
  the result unchanged.

This slice is pure / local: no live workflow execution, no process or
session control, no model calls, no network, no filesystem writes, no
branch / worktree movement, no Echo durable writes, no FileMap durable
writes, no UI / Electron / Bifrost behavior, no generated artifacts, no
provider / account calls, and no FileMap registration. The default
Atlas query may read allowlisted docs when they are explicitly scoped as
required paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple, Union

from meridian_core.atlas import (
    AtlasHit,
    AtlasQuery,
    AtlasResult,
    AtlasSource,
    query as atlas_query,
)
from meridian_core.workflow_dispatch import (
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowGateContext,
    WorkflowHarness,
    WorkflowHeartbeat,
    WorkflowInputPacket,
    WorkflowInputRecord,
    WorkflowPromptBudget,
    WorkflowResultSummary,
    WorkflowValidationError,
    WorkflowWorkOrder,
    is_path_in_scope,
)


# ---------------------------------------------------------------------------
# Constants — vocabulary the adapter publishes
# ---------------------------------------------------------------------------

ATLAS_ACTION_QUERY = "atlas.query"
ATLAS_RESULT_SHAPE = "atlas.query.v1"
ATLAS_INPUT_SOURCE = "atlas"

ATLAS_KIND_TERM = "atlas_term"
ATLAS_KIND_AREA = "atlas_area"
# Required paths use the promoted ``file_path`` kind so the packet's
# ``allowed_paths`` / ``forbidden_paths`` scope is enforced on them by
# WorkflowInputPacket construction. This is the fix for the Review A
# finding that required paths bypassed packet path scope when they were
# carried as a custom input kind.
ATLAS_KIND_REQUIRED_PATH = "file_path"
ATLAS_KIND_INCLUDE_ECHO = "atlas_include_echo"
ATLAS_KIND_LIMIT = "atlas_limit"

_VALID_ATLAS_KINDS = frozenset((
    ATLAS_KIND_TERM,
    ATLAS_KIND_AREA,
    ATLAS_KIND_REQUIRED_PATH,
    ATLAS_KIND_INCLUDE_ECHO,
    ATLAS_KIND_LIMIT,
))

ATLAS_PROOF_REF = "atlas.query"


# ---------------------------------------------------------------------------
# Adapter output records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AtlasOutputRecord:
    """One :class:`AtlasHit` in workflow-adapter form.

    Mirrors the promoted :class:`AtlasHit` field-for-field; ``source`` is
    flattened to the enum value string so the record is plain structured
    data that the dispatcher's prompt-drag guard can walk.
    """

    path: str
    title: str
    reason: str
    excerpt: Optional[str]
    source: str
    score: float


@dataclass(frozen=True)
class AtlasResultRecord:
    """The full Atlas adapter response, preserving the promoted
    :class:`AtlasResult` shape (``hits``, ``missing_paths``,
    ``truncated``) so callers receive a one-to-one mapping of the
    promoted Atlas contract through ``WorkflowResultSummary.outputs``.
    """

    hits: Tuple[AtlasOutputRecord, ...]
    missing_paths: Tuple[str, ...]
    truncated: bool


# ---------------------------------------------------------------------------
# Builder — encode an AtlasQuery as a WorkflowWorkOrder
# ---------------------------------------------------------------------------

def _atlas_inputs_from_query(
    query: AtlasQuery,
) -> Tuple[WorkflowInputRecord, ...]:
    """Encode the typed :class:`AtlasQuery` fields as bounded
    :class:`WorkflowInputRecord` entries.

    Required paths are encoded with ``kind="file_path"`` so the packet's
    ``allowed_paths`` / ``forbidden_paths`` scope is enforced on them at
    construction time. Terms, areas, ``include_echo``, and ``limit`` are
    encoded with explicit atlas kinds.
    """
    records: list[WorkflowInputRecord] = []
    for term in query.terms:
        records.append(WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_TERM,
            ref=term,
        ))
    for area in query.areas:
        records.append(WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_AREA,
            ref=area,
        ))
    for path in query.required_paths:
        records.append(WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_REQUIRED_PATH,
            ref=path,
        ))
    records.append(WorkflowInputRecord(
        source=ATLAS_INPUT_SOURCE,
        kind=ATLAS_KIND_INCLUDE_ECHO,
        ref="true" if query.include_echo else "false",
    ))
    records.append(WorkflowInputRecord(
        source=ATLAS_INPUT_SOURCE,
        kind=ATLAS_KIND_LIMIT,
        ref=str(query.limit),
    ))
    return tuple(records)


def build_atlas_work_order(
    *,
    work_order_id: str,
    project: str,
    query: AtlasQuery,
    intent: str,
    risk_tier: int,
    allowed_paths: Tuple[str, ...],
    prompt_budget: WorkflowPromptBudget,
    time_budget_seconds: int,
    hard_timeout_seconds: int,
    created_at: str,
    goal_summary: str = "atlas retrieval query",
    allowed_tools: Tuple[str, ...] = (),
    forbidden_paths: Tuple[str, ...] = (),
    gate_context: Optional[WorkflowGateContext] = None,
    parent_work_order_id: str = "",
    depth: int = 0,
    additional_inputs: Tuple[WorkflowInputRecord, ...] = (),
) -> WorkflowWorkOrder:
    """Construct a :class:`WorkflowWorkOrder` for an Atlas query.

    The query is encoded as typed :class:`WorkflowInputRecord` entries on
    the packet. Required paths are placed under ``kind="file_path"`` so
    :class:`WorkflowInputPacket` validates them against ``allowed_paths``
    and ``forbidden_paths``; required paths outside the packet scope are
    rejected by the promoted dispatch contract (not silently included).

    Pure / local. Does not call Atlas; does not invoke a handler.
    """
    if not isinstance(query, AtlasQuery):
        raise WorkflowValidationError(
            "build_atlas_work_order requires an AtlasQuery"
        )
    if not isinstance(additional_inputs, tuple):
        raise WorkflowValidationError(
            "additional_inputs must be a tuple"
        )
    for extra in additional_inputs:
        if not isinstance(extra, WorkflowInputRecord):
            raise WorkflowValidationError(
                "additional_inputs entries must be WorkflowInputRecord"
            )
    inputs = _atlas_inputs_from_query(query) + tuple(additional_inputs)
    packet = WorkflowInputPacket(
        project=project,
        goal_summary=goal_summary,
        inputs=inputs,
        allowed_tools=allowed_tools,
        allowed_paths=allowed_paths,
        forbidden_paths=forbidden_paths,
        prompt_budget=prompt_budget,
        gate_context=gate_context,
    )
    return WorkflowWorkOrder(
        work_order_id=work_order_id,
        harness=WorkflowHarness.ATLAS,
        action=ATLAS_ACTION_QUERY,
        intent=intent,
        risk_tier=risk_tier,
        input=packet,
        expected_result_shape=ATLAS_RESULT_SHAPE,
        time_budget_seconds=time_budget_seconds,
        hard_timeout_seconds=hard_timeout_seconds,
        created_at=created_at,
        parent_work_order_id=parent_work_order_id,
        depth=depth,
    )


# ---------------------------------------------------------------------------
# Decoder — reconstruct an AtlasQuery from a work order's typed inputs
# ---------------------------------------------------------------------------

def query_from_work_order(work_order: WorkflowWorkOrder) -> AtlasQuery:
    """Reconstruct the :class:`AtlasQuery` declared by ``work_order``.

    Pure / local. The handler calls this each invocation so the handler
    cannot diverge from the work order's typed inputs (no closed-over
    sidecar query). Unknown atlas-sourced input kinds raise
    :class:`WorkflowValidationError`. Non-atlas-sourced inputs are
    ignored gracefully — the adapter only consumes ``atlas``-sourced
    records.
    """
    if not isinstance(work_order, WorkflowWorkOrder):
        raise WorkflowValidationError(
            "query_from_work_order requires a WorkflowWorkOrder"
        )
    if work_order.harness != WorkflowHarness.ATLAS:
        raise WorkflowValidationError(
            "query_from_work_order requires harness=ATLAS"
        )

    terms: list[str] = []
    areas: list[str] = []
    required_paths: list[str] = []
    include_echo = False
    limit = 25  # mirrors AtlasQuery default

    for record in work_order.input.inputs:
        if record.source != ATLAS_INPUT_SOURCE:
            # Other-source records (e.g. ``source="echo"`` hints) are
            # not consumed by this adapter; they are preserved for other
            # readers without affecting the Atlas query reconstruction.
            continue
        if record.kind not in _VALID_ATLAS_KINDS:
            raise WorkflowValidationError(
                f"unknown atlas input kind: {record.kind}"
            )
        if record.kind == ATLAS_KIND_TERM:
            terms.append(record.ref)
        elif record.kind == ATLAS_KIND_AREA:
            areas.append(record.ref)
        elif record.kind == ATLAS_KIND_REQUIRED_PATH:
            required_paths.append(record.ref)
        elif record.kind == ATLAS_KIND_INCLUDE_ECHO:
            if record.ref == "true":
                include_echo = True
            elif record.ref == "false":
                include_echo = False
            else:
                raise WorkflowValidationError(
                    "atlas_include_echo ref must be 'true' or 'false'"
                )
        elif record.kind == ATLAS_KIND_LIMIT:
            try:
                limit = int(record.ref)
            except ValueError as exc:
                raise WorkflowValidationError(
                    "atlas_limit ref must be a base-10 integer"
                ) from exc
            if limit < 0:
                raise WorkflowValidationError(
                    "atlas_limit must be non-negative"
                )

    return AtlasQuery(
        terms=tuple(terms),
        areas=tuple(areas),
        required_paths=tuple(required_paths),
        include_echo=include_echo,
        project=work_order.input.project,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Result conversion
# ---------------------------------------------------------------------------

def _atlas_hit_to_output_record(hit: AtlasHit) -> AtlasOutputRecord:
    return AtlasOutputRecord(
        path=hit.path,
        title=hit.title,
        reason=hit.reason,
        excerpt=hit.excerpt,
        source=hit.source.value,
        score=hit.score,
    )


def _atlas_result_to_record(result: AtlasResult) -> AtlasResultRecord:
    return AtlasResultRecord(
        hits=tuple(_atlas_hit_to_output_record(h) for h in result.hits),
        missing_paths=tuple(result.missing_paths),
        truncated=bool(result.truncated),
    )


def _path_allowed_for_order(
    work_order: WorkflowWorkOrder,
    path: object,
) -> bool:
    if not isinstance(path, str):
        return False
    return is_path_in_scope(
        path,
        allowed_paths=work_order.input.allowed_paths,
        forbidden_paths=work_order.input.forbidden_paths,
    )


def _scoped_filemap_entries(
    work_order: WorkflowWorkOrder,
    entries: Tuple,
) -> Tuple:
    return tuple(
        entry for entry in entries
        if _path_allowed_for_order(work_order, getattr(entry, "path", None))
    )


def _result_paths_are_scoped(
    work_order: WorkflowWorkOrder,
    result: AtlasResult,
) -> bool:
    for hit in result.hits:
        if hit.source in (AtlasSource.FILEMAP, AtlasSource.DOC):
            if not _path_allowed_for_order(work_order, hit.path):
                return False
    for missing_path in result.missing_paths:
        if not _path_allowed_for_order(work_order, missing_path):
            return False
    return True


def _result_summary_text(result: AtlasResult) -> str:
    pieces = [f"atlas query returned {len(result.hits)} hit(s)"]
    if result.missing_paths:
        pieces.append(
            f"{len(result.missing_paths)} required path(s) missing"
        )
    if result.truncated:
        pieces.append("results truncated")
    return "; ".join(pieces)


def _error(
    work_order: WorkflowWorkOrder,
    failure_kind: WorkflowFailureKind,
    summary: str,
) -> WorkflowErrorSummary:
    return WorkflowErrorSummary(
        work_order_id=work_order.work_order_id,
        harness=work_order.harness,
        failure_kind=failure_kind,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------

AtlasHandler = Callable[
    [WorkflowWorkOrder, Callable[[WorkflowHeartbeat], None]],
    Union[WorkflowResultSummary, WorkflowErrorSummary],
]


def make_atlas_handler(
    *,
    filemap_entries: Tuple = (),
    echo_store: object = None,
    query_fn: Optional[Callable[..., AtlasResult]] = None,
) -> AtlasHandler:
    """Build a workflow handler for Atlas work orders.

    The handler does **not** close over an :class:`AtlasQuery`; instead it
    reconstructs the query from ``work_order.input.inputs`` each call.
    Two work orders with different declared inputs handled by the same
    handler instance produce different :class:`AtlasResult` outcomes —
    handler state cannot diverge from the work order's typed inputs.

    Dependencies are dependency-injected so this slice stays pure /
    local:

    - ``filemap_entries`` — tuple of FileMap entry records passed through
      to :func:`meridian_core.atlas.query`.
    - ``echo_store`` — optional Echo repository used when the decoded
      query has ``include_echo=True``. When omitted, Echo hits are
      skipped by the promoted Atlas surface.
    - ``query_fn`` — optional override for
      :func:`meridian_core.atlas.query`, used by tests to inject a
      deterministic fake. Defaults to the promoted ``atlas.query``.

    Pure / local: no live workflow execution, no process / session
    control, no model calls, no network, no filesystem writes. The
    default Atlas query may read allowlisted docs when they are
    explicitly scoped as required paths.
    """
    if query_fn is None:
        query_fn = atlas_query
    if not callable(query_fn):
        raise WorkflowValidationError("query_fn must be callable")

    def handler(
        work_order: WorkflowWorkOrder,
        emit: Callable[[WorkflowHeartbeat], None],
    ) -> Union[WorkflowResultSummary, WorkflowErrorSummary]:
        if work_order.harness != WorkflowHarness.ATLAS:
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "work order harness is not ATLAS",
            )
        if work_order.action != ATLAS_ACTION_QUERY:
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "unsupported atlas action on work order",
            )
        if work_order.expected_result_shape != ATLAS_RESULT_SHAPE:
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "expected_result_shape does not match atlas.query.v1",
            )
        try:
            decoded_query = query_from_work_order(work_order)
        except WorkflowValidationError:
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "atlas work order inputs failed to decode",
            )
        try:
            scoped_filemap_entries = _scoped_filemap_entries(
                work_order,
                filemap_entries,
            )
            atlas_result = query_fn(
                decoded_query,
                filemap_entries=scoped_filemap_entries,
                echo_store=echo_store,
            )
        except Exception:
            return _error(
                work_order,
                WorkflowFailureKind.INTERNAL_ERROR,
                "atlas query raised an unhandled exception",
            )
        if not isinstance(atlas_result, AtlasResult):
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "atlas query returned an unsupported shape",
            )
        if not _result_paths_are_scoped(work_order, atlas_result):
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "atlas result included a path outside work order scope",
            )

        record = _atlas_result_to_record(atlas_result)
        summary_text = _result_summary_text(atlas_result)
        proof_trail: Tuple[str, ...] = (
            (ATLAS_PROOF_REF,) if work_order.risk_tier >= 2 else ()
        )
        try:
            return WorkflowResultSummary(
                work_order_id=work_order.work_order_id,
                harness=WorkflowHarness.ATLAS,
                result_shape=ATLAS_RESULT_SHAPE,
                summary=summary_text,
                outputs=(record,),
                proof_trail=proof_trail,
            )
        except WorkflowValidationError:
            # If WorkflowResultSummary construction fails (e.g. the
            # ``summary`` text or ``proof_trail`` violate the promoted
            # bounds), surface a typed INPUT_INVALID error rather than
            # silently blanking fields. Unsafe payload content in
            # ``outputs`` is caught downstream by
            # ``dispatch_work_order``'s prompt-drag guard.
            return _error(
                work_order,
                WorkflowFailureKind.INPUT_INVALID,
                "atlas result summary construction failed",
            )

    return handler


# Sentinel referenced by the no-private-helper test. The adapter does
# not import or use private dispatch helpers; this constant exists only
# to make that contract self-evident in code review without having to
# search the file for an absence.
ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER = False


__all__ = (
    "ATLAS_ACTION_QUERY",
    "ATLAS_RESULT_SHAPE",
    "ATLAS_INPUT_SOURCE",
    "ATLAS_KIND_TERM",
    "ATLAS_KIND_AREA",
    "ATLAS_KIND_REQUIRED_PATH",
    "ATLAS_KIND_INCLUDE_ECHO",
    "ATLAS_KIND_LIMIT",
    "ATLAS_PROOF_REF",
    "AtlasOutputRecord",
    "AtlasResultRecord",
    "AtlasHandler",
    "build_atlas_work_order",
    "query_from_work_order",
    "make_atlas_handler",
    "ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER",
)
