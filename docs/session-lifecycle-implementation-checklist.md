# Session Lifecycle Implementation Checklist

Converts `docs/session-lifecycle-v2-contract.md` into a bounded, code-ready implementation plan for `meridian_core/session_lifecycle.py`. This checklist is a planning artifact only. Do not implement the runtime module until the contract is reviewed and this checklist is approved.

## 1. Module Scaffold

- [ ] Create `meridian_core/session_lifecycle.py`.
  - Module docstring: ownership, purity boundary, no-live-effects posture.
  - Imports: `dataclasses`, `enum`, `typing` (`Optional`, `Tuple`, `FrozenSet`), `datetime` (timezone-aware only).
  - No subprocess, no filesystem mutation, no network, no branch movement, no UI automation.

### Out of runtime scope (do not implement yet)
- Live Polaris/Electron integration
- Actual session spawning or process management
- Branch switching or worktree creation
- Vendor-account automation
- Shared mutable project state
- Federation networking

## 2. Enums

### `SessionHarnessRole` (Enum)
Values:
- `BUILD = "build"` — worker lane that produces code/docs
- `REVIEW = "review"` — Codex review lane
- `UI = "ui"` — Bifrost UI lane
- `ARCHITECTURE = "architecture"` — architecture/docs lane
- `COORDINATOR = "coordinator"` — Prime-orchestrated override lane
- `SPECIALIST = "specialist"` — ad hoc specialist lane

### `SessionStatus` (Enum)
Values:
- `STARTING = "starting"` — session is booting
- `POLLING = "polling"` — actively polling assigned queue, idle
- `RUNNING = "running"` — executing an active task
- `WAITING = "waiting"` — paused for human input or external signal
- `BLOCKED = "blocked"` — blocked by Aegis, quota, or environmental issue
- `REVIEW_GATED = "review_gated"` — cadence review pending before next task
- `CAPACITY_LIMITED = "capacity_limited"` — provider/model quota or rate limit
- `STALE = "stale"` — no active task and no heartbeat beyond threshold
- `STOPPED = "stopped"` — explicitly stopped by Prime or Scott
- `ARCHIVED = "archived"` — completed and archived

### `SessionCommandIntent` (Enum)
Values:
- `SPAWN = "spawn"` — create a new worker/review session
- `WATCH = "watch"` — observe a session without intervening
- `POLL_QUEUE = "poll_queue"` — force a queue read cycle
- `STEER = "steer"` — change session direction (task, model, project)
- `STOP_REQUEST = "stop_request"` — request graceful stop
- `TRANSFER = "transfer"` — reassign session to different lane/queue
- `ARCHIVE = "archive"` — archive session state
- `RESTART = "restart"` — restart a session that exited or stalled
- `RESTEER = "resteer"` — recover a session that is polling wrong queue, stale, or degraded
- `RECOVER_FROM_LIMIT = "recover_from_limit"` — recover from provider quota/rate limit
- `REQUEST_HUMAN_GATE = "request_human_gate"` — request human approval before next action

## 3. Dataclasses

### `SessionLifecycleState` (frozen=True)
The authoritative snapshot of a session. Immutable.

| Field | Type | Required | Notes |
|---|---|---|---|
| `session_id` | `str` | Yes | Unique session identifier |
| `session_name` | `str` | Yes | Human-readable name |
| `project_name` | `str` | Yes | Project the session belongs to |
| `project_path` | `Optional[str]` | No | Filesystem path to project |
| `harness_role` | `SessionHarnessRole` | Yes | Session role |
| `assigned_queue_file` | `str` | Yes | Path to the queue file this session owns |
| `model_provider` | `str` | Yes | e.g. "deepseek", "anthropic" |
| `model_name` | `str` | Yes | e.g. "deepseek-chat", "claude-sonnet-4-5" |
| `status` | `SessionStatus` | Yes | Current session status |
| `worktree_path` | `str` | Yes | Unique worktree path for this session |
| `branch_name` | `str` | Yes | Git branch the session operates on |
| `current_task_id` | `Optional[str]` | No | Task heading or id currently executing |
| `last_queue_read_at` | `Optional[datetime]` | No | Timestamp of last queue read (timezone-aware) |
| `last_queue_write_at` | `Optional[datetime]` | No | Timestamp of last queue write (timezone-aware) |
| `last_prompt_sent_at` | `Optional[datetime]` | No | Timestamp of last prompt dispatch |
| `last_prompt_payload_size` | `Optional[int]` | No | Size of last prompt payload in tokens or chars |
| `review_cadence_state` | `str` | Yes | Cadence state: "clear", "pending_1_of_3", "pending_2_of_3", "pending_3_of_3", "blocked" |
| `proof_state` | `str` | Yes | Proof state: "none", "pending", "passed", "failed", "blocked" |
| `health_state` | `str` | Yes | Health: "healthy", "degraded", "unhealthy", "unknown" |
| `blocker_summary` | `FrozenSet[str]` | Yes | Set of blocking condition descriptions (empty if none) |
| `permission_context` | `str` | Yes | Permission level: "full", "restricted", "read_only", "none" |

Legality helpers:
- `def is_idle(self) -> bool`: True when status is POLLING and no active task.
- `def is_healthy(self) -> bool`: True when health_state is "healthy".
- `def is_blocked(self) -> bool`: True when blockers present or status is BLOCKED.
- `def is_gated(self) -> bool`: True when status is REVIEW_GATED or CAPACITY_LIMITED.
- `def is_terminal(self) -> bool`: True when status is STOPPED or ARCHIVED.
- `def age_since_last_read(self, now: datetime) -> Optional[float]`: Seconds since last queue read, or None.
- `def age_since_last_write(self, now: datetime) -> Optional[float]`: Seconds since last queue write, or None.
- `def is_stale(self, now: datetime, threshold_seconds: float = 600.0) -> bool`: True when last read exceeds threshold.

### `SessionCommandPlan` (frozen=True)
Prime's proposed action for a session. Immutable and auditable.

| Field | Type | Required | Notes |
|---|---|---|---|
| `target_session_id` | `str` | Yes | Which session this command targets |
| `command_intent` | `SessionCommandIntent` | Yes | What to do |
| `reason` | `str` | Yes | Why this command is being issued |
| `expected_state_transition` | `str` | Yes | Human-readable description of expected state change |
| `evidence_refs` | `FrozenSet[str]` | Yes | References to proof/audit log entries |
| `queue_file_affected` | `str` | Yes | Queue file that will be read or written |
| `worktree_affected` | `Optional[str]` | No | Worktree path affected by this command |
| `branch_affected` | `Optional[str]` | No | Branch affected by this command |
| `aegis_gate_result` | `str` | Yes | Aegis gate verdict: "approved", "denied", "conditional", "not_applicable" |
| `cadence_review_gate_status` | `str` | Yes | Cadence gate: "clear", "pending", "blocked" |
| `is_executable_now` | `bool` | Yes | Can this command execute immediately? |
| `human_approval_required` | `bool` | Yes | Must a human approve before execution? |
| `rollback_note` | `Optional[str]` | No | How to roll back if the command fails |

Executability helpers:
- `def is_executable(self) -> bool`: True only when `is_executable_now` is True, `human_approval_required` is False, and `aegis_gate_result` is not "denied".
- `def requires_attention(self) -> bool`: True when human approval required or aegis denied.
- `def safe_to_display(self) -> bool`: Always True — command plans are designed for Bifrost display.

## 4. Invariant Validators (pure functions)

These are standalone functions, not methods on state objects, so they can be tested independently and reused across the harness.

### `validate_unique_worktree(sessions: FrozenSet[SessionLifecycleState]) -> List[str]`
Return a list of violation descriptions if any two sessions share a worktree path. Empty list means clean.

### `validate_queue_routing(session: SessionLifecycleState) -> List[str]`
Return violations if:
- Build role session's queue file does not contain "build" in its path.
- Review role session's queue file does not contain "review" in its path.

### `validate_no_branch_movement(command: SessionCommandPlan) -> List[str]`
Return violations if the command would change a branch without explicit permission. In V2, all branch changes are violations unless the permission context is "full".

### `validate_no_read_check_spam(history: Tuple[SessionLifecycleState, ...]) -> bool`
Return True if the recent history shows read-check-only activity without task execution, indicating a session is stuck in a read-check loop.

## 5. Proof Expectations

Every function and dataclass must include proof readiness:

- **Serialization proof**: `SessionLifecycleState` and `SessionCommandPlan` must be JSON-serializable (via `dataclasses.asdict()` or custom encoder). Write tests that round-trip through JSON.
- **Determinism proof**: All helpers are pure functions of their inputs. Write tests that call each helper twice with identical inputs and assert identical outputs.
- **No side effects proof**: The module imports must not include `subprocess`, `os`, `shutil`, `requests`, or any filesystem-mutating library. A static import check test enforces this.
- **Failure-soft proof**: All validation functions return lists of violations rather than raising exceptions. Callers decide severity.
- **Time-safety proof**: All datetime fields must be timezone-aware. The `__post_init__` for any dataclass holding a datetime field must reject naive datetimes.

## 6. Tests To Write

File: `tests/test_session_lifecycle.py`

### Enum tests
- [ ] `test_session_harness_role_values` — verify all six roles exist and are distinct.
- [ ] `test_session_status_values` — verify all ten statuses exist and are distinct.
- [ ] `test_session_command_intent_values` — verify all eleven intents exist and are distinct.

### `SessionLifecycleState` tests
- [ ] `test_state_construction_minimal` — construct with required fields only, verify defaults.
- [ ] `test_state_construction_full` — construct with all fields, verify all values.
- [ ] `test_state_immutability` — verify FrozenInstanceError on field mutation attempt.
- [ ] `test_is_idle` — verify True only for POLLING with no current_task_id.
- [ ] `test_is_healthy` — verify True only for "healthy" health_state.
- [ ] `test_is_blocked` — verify True when blockers non-empty or status BLOCKED.
- [ ] `test_is_gated` — verify True for REVIEW_GATED and CAPACITY_LIMITED statuses.
- [ ] `test_is_terminal` — verify True for STOPPED and ARCHIVED.
- [ ] `test_age_since_last_read` — compute age from known datetime, verify accuracy.
- [ ] `test_age_since_last_read_none` — return None when last_queue_read_at is None.
- [ ] `test_age_since_last_write` — compute age from known datetime, verify accuracy.
- [ ] `test_is_stale` — return True when age exceeds threshold, False otherwise.
- [ ] `test_is_stale_no_read` — return True when last_queue_read_at is None (never read).
- [ ] `test_state_json_roundtrip` — serialize to JSON and back, verify equality.

### `SessionCommandPlan` tests
- [ ] `test_plan_construction` — construct with all fields, verify values.
- [ ] `test_plan_immutability` — verify FrozenInstanceError on field mutation attempt.
- [ ] `test_is_executable` — True only when all three conditions met.
- [ ] `test_is_executable_human_gate_blocks` — False when human_approval_required is True.
- [ ] `test_is_executable_aegis_denied_blocks` — False when aegis_gate_result is "denied".
- [ ] `test_is_executable_not_executable_now` — False when is_executable_now is False.
- [ ] `test_requires_attention` — True when human approval required or aegis denied.
- [ ] `test_safe_to_display` — always True.
- [ ] `test_plan_json_roundtrip` — serialize to JSON and back, verify equality.

### Invariant validator tests
- [ ] `test_unique_worktree_no_violations` — distinct worktrees produce empty list.
- [ ] `test_unique_worktree_violation` — shared worktree produces violation description.
- [ ] `test_queue_routing_build_valid` — build queue path containing "build" produces empty list.
- [ ] `test_queue_routing_build_invalid` — build role with non-build path produces violation.
- [ ] `test_queue_routing_review_valid` — review queue path containing "review" produces empty list.
- [ ] `test_queue_routing_review_invalid` — review role with non-review path produces violation.
- [ ] `test_no_branch_movement_allowed` — branch-affected command without full permission produces violation.
- [ ] `test_no_branch_movement_full_permission` — branch-affected command with full permission produces empty list.
- [ ] `test_read_check_spam_detected` — history of repeated read-checks without writes returns True.
- [ ] `test_read_check_normal_activity` — history with writes interspersed returns False.

### Integration/import tests
- [ ] `test_module_imports_are_pure` — verify no banned imports (subprocess, os, shutil, requests, socket).
- [ ] `test_datetime_fields_must_be_timezone_aware` — constructing state with naive datetime raises ValueError.

### Proof commands (all expected to pass before Ready for Codex Review)
```bash
python -m pytest tests/test_session_lifecycle.py -q
```

## 7. FileMap Registration

After implementation, register in FileMap:
- `meridian_core/session_lifecycle.py` (area: `session_lifecycle`, purpose: "Session Lifecycle domain objects")
- `tests/test_session_lifecycle.py` (area: `session_lifecycle_tests`, purpose: "Session Lifecycle tests")

## 8. What Stays Out Of Runtime Until Later

| Item | Reason |
|---|---|
| `meridian_core/session_lifecycle.py` | Awaiting contract review and checklist approval |
| Live session spawn/watch/steer execution | Requires Polaris/Electron harness integration |
| Worktree creation or branch switching | Requires Scott/Prime permission model |
| Bifrost render bindings | Separate UI slice after domain objects are stable |
| Aegis gate execution inside session lifecycle | Aegis is a separate harness; session lifecycle only reads its verdict |
| Federation handoff | V3 horizon, not V2 |
| Read-check commit suppression | Runtime concern; contract defines the rule, implementation is later |

## References

- Contract: `docs/session-lifecycle-v2-contract.md`
- Pattern reference: `meridian_core/prime_autonomy.py` (frozen dataclass + enums + legality helpers)
- Pattern reference: `meridian_core/restart_resteer.py` (pure evaluator + invariant validators)
- Pattern reference: `meridian_core/echo.py` (frozen dataclass + __post_init__ validation)
