# Prime Orchestration State Model

**Status:** Architecture note — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Source prototype:** `docs/prime-orchestration-harness-prototype.md`, live build queues, `docs/live-codex-reviews.md`
**Purpose:** Turn the current markdown-queue coordination process into a concrete Prime state model: named objects, defined transitions, and explicit harness ownership. This note is the design bridge between the prototype and the Python domain objects that should replace it.

---

## What the Prototype Proved

The live build queue system works. Builders pull tasks, execute, log completion, mark ready for review. A review lane declares scope, sweeps, posts findings or clears. Repair routes back to the original builder. Scott is not in the loop unless a gate fires.

This is Prime-style orchestration. It just lives in markdown files instead of in Prime's state. The next step is to name every piece of state precisely enough that a Python domain object can hold it — and a harness can act on it — without a human reading and interpreting text.

---

## State Objects

### 1. WorkerLane

Represents one executing lane — a builder, reviewer, or verifier.

**Current prototype:** one `docs/live-build-N.md` file per lane; one `docs/live-codex-reviews.md` for the review lane.

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `lane_id` | str | e.g. `"build-1"`, `"build-4"`, `"codex-reviews"` |
| `lane_type` | `LaneType` enum | `BUILDER`, `REVIEWER`, `VERIFIER` |
| `status` | `LaneStatus` enum | see transitions below |
| `current_task_id` | str \| None | ID of the active `WorkerTask`, if any |
| `cadence_commit_count` | int | task-changing commits since last cadence review |
| `cadence_paused` | bool | True if lane is waiting for a cadence review to clear |
| `last_heartbeat_at` | datetime | used by Beacon for liveness |

**LaneStatus transitions:**

```
IDLE → RUNNING           (Prime assigns a task)
RUNNING → READY_FOR_REVIEW  (builder marks slice complete)
READY_FOR_REVIEW → UNDER_REVIEW  (review lane picks it up)
UNDER_REVIEW → CLEARED   (review finds no actionable issues)
UNDER_REVIEW → REPAIR_ROUTED  (review routes findings back)
REPAIR_ROUTED → RUNNING  (builder accepts and starts repair)
RUNNING → CADENCE_PAUSED  (three task-changing commits; awaiting cadence review)
CADENCE_PAUSED → IDLE   (cadence review clears the lane)
```

**Owner harness:** Beacon (liveness, heartbeat), Relay (dispatch — transitions lane to RUNNING), Loom (workflow — manages the full state machine), Bifrost (displays current status).

---

### 2. WorkerTask

Represents one unit of assigned work — the "Active Task" in current queue files.

**Current prototype:** the `## Active Task` section of each build queue file.

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `task_id` | str | unique identifier |
| `goal` | str | one-sentence description of intent |
| `owner_lane_id` | str | which lane is executing |
| `allowed_files` | list[str] | explicit scope boundary |
| `tests_required` | bool | whether tests must pass before marking complete |
| `status` | `TaskStatus` enum | extended from `meridian_core/models.py` |
| `completion_commit` | str \| None | commit hash when builder marks complete |
| `completion_files` | list[str] | files actually changed in the slice |
| `ready_for_review` | bool | True when builder has marked the slice |

**TaskStatus** (extends current `models.TaskStatus`):

```
PENDING → IN_PROGRESS    (lane picks up the task)
IN_PROGRESS → COMPLETE   (builder marks slice done)
COMPLETE → READY_FOR_REVIEW  (builder posts completion signal)
READY_FOR_REVIEW → UNDER_REVIEW  (review lane accepts)
UNDER_REVIEW → ACCEPTED  (no findings, lane cleared)
UNDER_REVIEW → REPAIR_NEEDED  (findings routed back)
REPAIR_NEEDED → IN_PROGRESS  (builder starts repair)
IN_PROGRESS → COMPLETE   (cycle repeats)
```

**Owner harness:** Relay (creates task, assigns to lane), Loom (transitions status), Aegis (gates COMPLETE → READY_FOR_REVIEW with evidence), Review Console (surfaces REPAIR_NEEDED items as FINDING cards).

---

### 3. CompletionSignal

The structured "Ready for Codex Review" marker — the handoff from builder to Prime/review harness.

**Current prototype:** a text block in the Active Task section:
```
**Ready for Codex Review**
- Commit: `<hash>`
- Files: `<list>`
- Tests: <result>
```

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `signal_id` | str | unique |
| `task_id` | str | which task this closes |
| `lane_id` | str | which lane is signaling |
| `commit_hash` | str | the deliverable commit |
| `files_changed` | list[str] | scoped to allowed_files |
| `tests_result` | str | `"passing"`, `"not required"`, `"waived"` |
| `created_at` | datetime | timestamp |

**Owner harness:** Loom (receives signal, transitions task to READY_FOR_REVIEW), Aegis (validates evidence before accepting signal). Prime places a corresponding card in the Review Console (`SYSTEM_FINDING` or `SUMMARY` card) so Scott can see a build completed without needing to read the queue file.

---

### 4. ReviewRoundScope

Declares what the review lane will sweep before it begins. Prevents scope creep and gives Prime a traceable boundary for what has and has not been reviewed.

**Current prototype:** the "Review Round Scope" text block in `docs/live-codex-reviews.md`:
```
Commits in scope: <hash1>, <hash2>, ...
Lanes in scope: Build 1, Build 4
```

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `round_id` | str | e.g. `"round-1"`, `"round-2"` |
| `commit_hashes` | list[str] | commits being reviewed |
| `lane_ids` | list[str] | lanes whose slices are in scope |
| `declared_at` | datetime | when scope was declared |
| `status` | `RoundStatus` enum | `OPEN`, `IN_PROGRESS`, `COMPLETE` |
| `reviewer_lane_id` | str | which lane is doing the review |

**Why scope declaration matters:** Without declaring scope before reviewing, Prime cannot know whether a commit was reviewed and found clean vs. not yet reviewed. The checkpoint ledger only works if the scope is explicit and immutable once declared.

**Owner harness:** Loom (creates and closes rounds), Aegis (logs round result as proof record), Review Console (surfaces round completion as SUMMARY card).

---

### 5. ReviewCheckpoint

One entry in the review ledger — tracking whether a specific commit from a specific lane has been reviewed, found clean, or has open findings.

**Current prototype:** the `## Checkpoint Ledger` table in `docs/live-codex-reviews.md`.

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `checkpoint_id` | str | unique |
| `commit_hash` | str | the reviewed commit |
| `lane_id` | str | which builder's slice |
| `round_id` | str | which review round covered this |
| `status` | `CheckpointStatus` enum | `UNREVIEWED`, `REVIEWED_CLEAN`, `FINDINGS_OPEN`, `REPAIR_VERIFIED` |
| `finding_ids` | list[str] | findings against this commit, if any |
| `cleared_at` | datetime \| None | when status became REVIEWED_CLEAN or REPAIR_VERIFIED |

**CheckpointStatus transitions:**

```
UNREVIEWED → REVIEWED_CLEAN     (review finds no actionable issues)
UNREVIEWED → FINDINGS_OPEN      (review finds issues, routes repair)
FINDINGS_OPEN → REPAIR_VERIFIED  (builder repaired; re-review confirmed clean)
```

**Owner harness:** Aegis (checkpoint record is proof that review occurred), Loom (manages transitions), Relay (a lane with FINDINGS_OPEN checkpoints is blocked from new work until cleared).

---

### 6. FindingRecord

One review finding — a specific issue, its severity, and its disposition.

**Current prototype:** text entries in `## Checkpoint Ledger` and in build lane Codex Review Cadence sections.

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `finding_id` | str | unique |
| `checkpoint_id` | str | which checkpoint this finding belongs to |
| `severity` | `FindingSeverity` enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `description` | str | what the finding is |
| `suggested_repair` | str | what the review lane recommends |
| `status` | `FindingStatus` enum | `OPEN`, `REPAIR_ROUTED`, `WAIVED`, `VERIFIED` |
| `repair_task_id` | str \| None | the WorkerTask created to fix this |

**FindingSeverity** → `EvidenceSeverity` in `meridian_core/aegis.py` (already exists; reuse or alias).

**Owner harness:** Aegis (creates and owns finding records), Review Console (FINDING cards reference finding_id), Loom (CRITICAL/HIGH findings block lane from new work until VERIFIED).

---

### 7. RepairRoute

The act of Prime routing a finding back to its original builder.

**Current prototype:** the review lane writes a repair `## Active Task` directly into the offending build lane's queue file. This is the most fragile piece of the prototype — it requires a human-readable file edit to another lane's file.

**State fields:**

| Field | Type | Notes |
|---|---|---|
| `route_id` | str | unique |
| `finding_ids` | list[str] | which findings triggered this repair |
| `source_lane_id` | str | which lane produced the flawed work |
| `repair_task_id` | str | the new WorkerTask assigned to fix it |
| `routed_at` | datetime | |
| `resolved` | bool | True when repair is verified |

**Why this needs to be a first-class object:** The current prototype requires the review lane to edit another lane's queue file — a boundary violation that only works because a human is in the loop. When Prime owns this, it routes the finding by creating a WorkerTask and assigning it to the lane's state, without touching the lane's file directly. The file becomes a projection of state, not the state itself.

**Owner harness:** Loom (creates RepairRoute), Relay (assigns repair task to lane), Review Console (surfaces as a FINDING card with disposition options for the builder — or if CRITICAL, blocks Prime until acknowledged).

---

## Harness Ownership Map

| State object | Creates | Transitions | Reads | Surfaces |
|---|---|---|---|---|
| WorkerLane | Loom (at startup) | Relay, Loom, Beacon | All harnesses | Bifrost (status badge), Beacon (heartbeat) |
| WorkerTask | Relay (on assignment) | Loom, Aegis | Builder lane, Review lane | Bifrost (task card), Review Console (completion summary) |
| CompletionSignal | Builder lane (via Relay) | Aegis, Loom | Review lane, Prime | Review Console (SUMMARY card) |
| ReviewRoundScope | Review lane (via Loom) | Loom | Review lane, Prime | Review Console (SUMMARY card on close) |
| ReviewCheckpoint | Aegis (on review) | Aegis, Loom | Prime, Review lane | Review Console (FINDING or clean-pass card) |
| FindingRecord | Aegis (on review) | Aegis, Loom | Review lane, Builder lane | Review Console (FINDING card) |
| RepairRoute | Loom (on finding routing) | Relay, Loom | Builder lane | Review Console (FINDING card → REPAIR_NEEDED) |

---

## What Remains Markdown Prototype vs. What Should Become Python

### Keep as markdown (for now)

- **Queue poll loop rules** — the standing instructions at the top of each queue file are human-readable protocol that Prime will eventually internalize, but they are not state. They are behavior. They belong in Prime's prompt or directive layer until Prime's runtime exists.
- **Read Checks and Write/Completion Log** — these are audit trail entries, not state transitions. An event log (append-only, timestamped) is the right representation, but the format matters less than the content. Markdown works as long as queries are human-only.
- **Cross-Check Activity** — informational notes from one lane to another. These could eventually become `FindingRecord` objects with severity `LOW` or `INFORMATIONAL`, but the overhead of formalizing routine idle observations is not worth it until Prime's review loop is automated.

### Must become Python domain objects

| Current markdown artifact | Target Python object |
|---|---|
| Lane file + status text | `WorkerLane` (in `meridian_core/loom.py` or `meridian_core/orchestration.py`) |
| `## Active Task` section | `WorkerTask` (extends `Task` in `meridian_core/models.py`) |
| `Ready for Codex Review` marker | `CompletionSignal` |
| Checkpoint Ledger row | `ReviewCheckpoint` (in `meridian_core/aegis.py` or new `meridian_core/review.py`) |
| Review Round Scope declaration | `ReviewRoundScope` |
| Codex Review Cadence finding entry | `FindingRecord` (wraps/extends `AegisEvidence`) |
| Repair Active Task written to another lane's file | `RepairRoute` |
| Cadence commit count (`after 3 commits...`) | `WorkerLane.cadence_commit_count` field |
| Cadence pause state | `WorkerLane.cadence_paused` field |

### The ordering constraint

The Python objects should arrive in this order (each depends on the previous):

1. `WorkerTask` — simplest; extends existing `Task`; no harness dependencies
2. `CompletionSignal` — needs `WorkerTask`; gates Aegis acceptance
3. `WorkerLane` + `LaneStatus` — needs `WorkerTask` and `CompletionSignal`
4. `ReviewCheckpoint` + `FindingRecord` — needs `WorkerLane`; wraps `AegisEvidence`
5. `ReviewRoundScope` — needs `ReviewCheckpoint`
6. `RepairRoute` — needs `FindingRecord` and `WorkerTask`; replaces direct queue-file editing

Until step 6 exists, the review lane will continue to edit queue files directly. That is acceptable scaffolding. What is not acceptable is building step 6 before the objects it depends on are typed and tested.

---

## What This Is Not

- A Bifrost UI design — that is in `docs/bifrost-cockpit-queue-status-brief.md`.
- A FileMap — Build 3 owns `docs/FileMap.md`; new files here should be submitted to Build 3 for indexing.
- A runtime implementation — no Python code in this note. Build slices for the objects above belong to Build 1 (domain models) or Build 2 (package exports).
- A release timeline — this is a state model, not a schedule.

---

## Cross-References

- Source prototype: `docs/prime-orchestration-harness-prototype.md`
- V0 gap analysis: `docs/v0-build-readiness-map.md`
- Aegis evidence model: `meridian_core/aegis.py`
- Existing task/portfolio model: `meridian_core/models.py`
- Build and harness maturity: `meridian_core/builds.py`
- Review Console surface contract: `docs/review-console-surface-contract.md`
- Bifrost cockpit design: `docs/bifrost-cockpit-queue-status-brief.md`
- Load-bearing principles: `docs/meridian-pillars.md`
