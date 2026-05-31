# Session Lifecycle V2 Contract

## Purpose

The Session Lifecycle Harness lets Prime spawn, watch, steer, recover, transfer, and archive worker/review sessions through typed state instead of ad hoc UI supervision. It is the runtime expression of the rule Scott has been enforcing manually: every lane must know its queue, role, worktree, model, cadence, proof state, and blocker state.

## Owner

- Harness owner: Session Lifecycle Harness
- Supervising intelligence: Prime
- UI surface: Bifrost renders summaries and command previews only
- Safety gate: Aegis must approve high-risk or destructive command plans before execution

## SessionLifecycleState

`SessionLifecycleState` is the authoritative snapshot of a session.

Required responsibilities:

- `session_id` and `session_name`
- `project_name` and optional `project_path`
- `harness_role`: build, review, UI, architecture, coordinator, or specialist
- `assigned_queue_file`
- `model_provider` and `model_name`
- `status`: starting, polling, running, waiting, blocked, review_gated, capacity_limited, stale, stopped, archived
- `worktree_path`
- `branch_name`
- `current_task_id` or task heading
- `last_queue_read_at`
- `last_queue_write_at`
- `last_prompt_sent_at`
- `last_prompt_payload_size`
- `review_cadence_state`
- `proof_state`
- `health_state`
- `blocker_summary`
- `permission_context`

The state must be serializable, deterministic, and safe to display in Bifrost without exposing raw worker chat.

## SessionCommandPlan

`SessionCommandPlan` is Prime's proposed action for a session. It must be typed and auditable before execution.

Supported command intents:

- `spawn`
- `watch`
- `poll_queue`
- `steer`
- `stop_request`
- `transfer`
- `archive`
- `restart`
- `resteer`
- `recover_from_limit`
- `request_human_gate`

Each plan must include:

- target session identity
- command intent
- reason
- expected state transition
- evidence references
- queue file affected
- worktree/branch affected
- Aegis gate result
- cadence/review gate status
- whether the command is executable now
- whether human approval is required

## Invariants

- Every worker and review session must run in its own unique worktree.
- Build sessions read only their assigned build queue.
- Review sessions read only their assigned review queue.
- A session may inspect other queues only as evidence, never as executable work.
- Branch movement requires Scott or Prime permission.
- No hidden account automation, destructive filesystem action, or branch switching is allowed without explicit command-plan proof.
- Read-check-only commits are not a substitute for work; heartbeat/read state belongs in Session Lifecycle state and Bifrost status surfaces.

## Workflow/Sub-Agent Principle

Harness work should run in bounded workflow or sub-agent contexts when available. Prime keeps only typed summaries and durable state:

- Echo returns memory hits and memory-write summaries.
- Atlas returns retrieval hits and source summaries.
- Aegis returns gate verdicts and proof requirements.
- Relay returns dispatch envelopes and payload metrics.
- Bifrost returns render snapshots and UI proof.
- Session Lifecycle returns state transitions and command outcomes.

Prime should not absorb raw workflow transcripts unless a human-gated debug review explicitly asks for them.

## Proof And Safety

Every executable command plan must carry proof:

- current state evidence
- queue evidence
- worktree evidence
- review/cadence evidence
- Aegis gate evidence
- expected result
- rollback or recovery note when relevant

Human-gated commands must be clearly non-executable until approval is recorded.

## Out Of Scope For V2

- live Polaris or Electron automation
- destructive commands
- automatic branch switching
- vendor-account automation
- shared mutable project state
- federation networking

V2 defines the state and command contract. Later slices implement domain objects and Bifrost display surfaces.
