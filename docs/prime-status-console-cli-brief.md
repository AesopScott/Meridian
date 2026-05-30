# Prime Status Console and Review Console CLI Bridge

**Status:** Architecture note — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Source:** `docs/v0-build-readiness-map.md` (capability gaps 1, 2, 4, 5), `meridian_core/review_console.py`, `meridian_core/wake.py`, `meridian_core/aegis.py`
**Purpose:** Define the CLI surface that bridges Prime's orchestration state to two distinct conversation surfaces — the orchestrator thread and the review/system prompt window — and name the routing contract between them.

---

## The Problem This Solves

Prime's domain models exist but nothing surfaces them. `build_wake_brief()` produces a `WakeBrief` and nobody reads it. `ProofTrail.is_proof_blocking()` knows whether a dispatch is gated and nobody checks it. `ReviewConsoleQueue.pending_gates()` can tell Prime what Scott needs to decide and nothing calls it.

The CLI bridge is the V0 connection layer. It is not the permanent architecture — it is the first wire between the domain model and a human-readable surface. Three commands replace two absent patterns in V0:

1. What is Prime's state right now? → `prime_status`
2. What does Prime need from Scott? → `prime_console` + `prime_approve`

---

## The Two Surfaces

### Orchestrator Conversation

The conversation Prime has with Scott directly. This is where:
- Scott says "continue working" or "change direction"
- Prime reports strategic progress — what is being built, what objective is being served, what gate was hit
- Prime asks for judgment calls: "Should we proceed with this approach?"
- Prime acknowledges completed review cycles

This surface should be **clean**. No raw proof logs. No liveness heartbeat dumps. No BuildN read-check lists. Those belong in the review window.

### Review Console (Non-Orchestrator / Review Prompt Window)

A separate prompt window — in V0 this is a terminal; in V1 it is a Bifrost panel. This is where:
- Prime places `ReviewConsoleItem` records that Scott can inspect, acknowledge, or approve
- Beacon posts liveness warnings for dead or degraded lanes
- Aegis posts proof-blocking findings that gate Relay dispatch
- Wake Brief lines appear at startup
- Worker session completion signals arrive
- Codex review findings land before Prime clears a lane

The rule: **anything that would be a status entry in a NASA mission control log goes here, not to the orchestrator thread.** The orchestrator thread carries decisions and intentions; the review window carries evidence and status.

---

## CLI Commands (V0)

### `prime_status`

Prints Prime's current orientation in one screen. Scott uses this to orient before giving Prime direction.

Output sections:
1. **Mission** — name, prime directive, load status
2. **Intention** — current `ProgressIntention`: initiative, next moves, stage, risk tier
3. **Harness liveness** — each harness from `WakeBrief`: Go / Degraded / Blocked / Offline
4. **Pending gates** — count of `APPROVAL_GATE` items in the Review Console requiring Scott's response

```
$ prime_status

MERIDIAN PRIME — Build 4 Session
Mission: Meridian Local AI Command System
Prime Directive: Build Prime-first. Human in the loop for judgment only.

INTENTION
  Initiative:  Core Orchestration Layer
  Next moves:  relay_executor.py → prime_wake() CLI → route_to_console() wire
  Stage:       FOUNDATION
  Risk tier:   MEDIUM

HARNESS STATUS
  Bifrost        OFFLINE     (V0 bypassed — CLI substitute active)
  Beacon         STANDING_BY (liveness emitter not built; flat-file sentinel ready)
  Relay          DEGRADED    (dispatch plan ready; executor not built)
  Aegis          STABLE      (domain slice; proof gates not wired to dispatch)
  Loom           OFFLINE     (not yet built)
  Review Console STABLE      (domain slice; not persisted yet)

PENDING GATES
  2 items require Scott's response  →  run prime_console
```

**Implementation:** Reads `MISSION.md` via `mission.py`, calls `build_wake_brief()`, reads `portfolio.json` via `build_progress_intention()`, counts pending gates in `~/.meridian/console.json`.

---

### `prime_console`

Prints all pending `ReviewConsoleItem` records — findings, proof, gates, system messages — that Prime has placed for Scott's attention. This is the V0 Review Console surface.

```
$ prime_console

REVIEW CONSOLE  [4 pending]
─────────────────────────────────────────────────────────────────

[001] APPROVAL_GATE  ⚠ WARNING
      Title:    Relay dispatch: tier-3 gate — proof required
      Content:  Build 1 (d2820d2) marked complete. Aegis reports 1 open
                ERROR-severity finding: test_prompt_budget.py coverage
                below 80%. Dispatch to next session is blocked until
                resolved or waived.
      Actions:  approve · reject · modify
      → prime_approve 001

[002] SYSTEM_FINDING  ℹ INFO
      Title:    Build 4 wake check — Beacon offline
      Content:  Beacon liveness harness not built. Flat-file sentinel active.
                Queue files polled at origin/main for idle/running signal.
      Actions:  acknowledge
      → prime_approve 002 --action acknowledge

[003] CROSS_CHECK  ℹ INFO
      Title:    Build 3 FileMap refresh — 1378bda awaiting Codex Round B2
      Content:  Build 3 completed FileMap refresh (1378bda) and marked
                Ready for Codex Review. Review lane has not yet declared
                Round B2 scope.
      Actions:  inspect · acknowledge

[004] PROOF  ℹ INFO
      Title:    Build 2 export gate — PromptPacket API (f2f69ff) — CLEAR
      Content:  Aegis review: PromptPacket export from relay_packet.py
                matches declared API surface. No blocking findings.
      Actions:  acknowledge
```

**Implementation:** Reads `~/.meridian/console.json`, formats and renders pending items sorted by severity then sequence.

---

### `prime_approve <item-id>`

Respond to a specific gate item. Accepts optional `--action` flag (default: `approve`).

```bash
prime_approve 001                                           # approve gate 001
prime_approve 002 --action acknowledge                      # acknowledge informational item
prime_approve 001 --action reject                           # reject — Prime must not proceed
prime_approve 001 --action modify --note "Waive coverage for integration test only"
```

**Implementation:** Loads `~/.meridian/console.json`, calls `ReviewConsoleQueue.respond()`, writes back. If the item was a blocking gate, Relay's next dispatch will re-check `pending_gates()` and find none, allowing the dispatch to proceed.

---

## `route_to_console(item_type, summary, provenance, severity?, requires_response?)`

The programmatic call that Prime and harnesses use to place items into the Review Console. This is the integration seam — not a user-facing command, but the function that every other piece of the harness calls.

**Signature (V0):**
```python
def route_to_console(
    item_type: ReviewConsoleItemType,
    summary: str,
    provenance: str,
    severity: ReviewConsoleSeverity = ReviewConsoleSeverity.INFO,
    requires_response: bool = False,
    item_id: str | None = None,
) -> ReviewConsoleItem
```

**Who calls it:**

| Caller | When | Item type | Severity |
|--------|------|-----------|----------|
| `wake.py` → `build_wake_brief()` | Prime wakes up | `SYSTEM_FINDING` | per `WakeStatus` |
| `aegis.py` → `is_proof_blocking()` | Blocking evidence found | `APPROVAL_GATE` | `WARNING` or `ERROR` |
| `relay_executor.py` | Dispatch completes | `SYSTEM_FINDING` | `INFO` |
| `beacon.py` | Lane liveness fails | `SYSTEM_FINDING` | `WARNING` |
| Review lane / Codex Reviews | Finding posted | `CROSS_CHECK` | per finding severity |
| Prime / orchestrator | Gate decision needed | `APPROVAL_GATE` | `WARNING` |

**V0 implementation:** Reads `~/.meridian/console.json`, creates a `ReviewConsoleItem` via the appropriate factory (`make_system_finding`, `make_approval_gate`, `make_cross_check_item`), calls `ReviewConsoleQueue.enqueue()`, writes back. Assigns a UUID `item_id` if none provided.

**V1 implementation:** Loom manages the queue in memory. Bifrost subscribes to queue events and renders items in real time. Prime's orchestrator loop checks `pending_gates()` before every Relay dispatch.

---

## Connection Map

```
Mission Boot
  └── mission.py:load_mission()
  └── wake.py:build_wake_brief()
        └── route_to_console(SYSTEM_FINDING, per WakeLine)
              └── prime_console shows each line
              └── prime_status shows harness summary

Progress Intention
  └── intention.py:build_progress_intention()
        └── prime_status shows current initiative + next moves
        └── (no Review Console items — intention is orchestrator-layer info)

Beacon (V0 stub)
  └── beacon.py:check_harness_liveness()
        └── if stale queue file → route_to_console(SYSTEM_FINDING, WARNING)
        └── prime_console shows liveness alert

Aegis Proof Gates
  └── aegis.py:ProofTrail.is_proof_blocking()
        └── if blocking → route_to_console(APPROVAL_GATE)
        └── prime_console shows gate
        └── prime_approve unblocks
  └── relay_executor.py checks pending_gates() before dispatch
        └── if gates present → dispatch blocked until cleared

Review Console
  └── ReviewConsoleQueue.pending() → prime_console renders
  └── ReviewConsoleQueue.pending_gates() → prime_status shows count
  └── prime_approve → ReviewConsoleQueue.respond()
```

---

## Example Transcript

### Orchestrator Thread (Prime's conversation with Scott)

```
Scott: Continue working.

Prime: Build 1's relay_executor.py slice just completed (d2820d2). Aegis
       flagged a coverage gap — I've routed it to the Review Console as
       gate item 001. Relay dispatch to the next session is blocked until
       you resolve it.

       Build 4 is writing the CLI bridge brief.
       Build 3 FileMap refresh is pending Codex Round B2 review.

       Current intention: get relay_executor.py dispatching real model calls.
       Next gate: coverage waiver or fix for test_prompt_budget.py.

       Run prime_console to see all pending items.
```

### Review Console (Separate Terminal / Bifrost Panel)

```
[001] APPROVAL_GATE  ⚠
      Relay dispatch blocked — Aegis: test_prompt_budget.py coverage 78%
      (threshold 80%). Tier-3 dispatch requires proof-clean evidence.
      Actions: approve · reject · modify
      → prime_approve 001

[002] SYSTEM_FINDING  ℹ
      Build 4 wake — Beacon offline, flat-file sentinel active (04d9779)

[003] CROSS_CHECK  ℹ
      Build 3 FileMap refresh 1378bda — awaiting Codex Round B2 scope
      declaration before review can begin.

[004] SYSTEM_FINDING  ℹ
      Codex Reviews B Round B1 closed: Build 5 slice 7c34566 CLEAR.
      MEDIUM finding (FileMap gap) routed to Build 3.
```

The orchestrator thread says what is happening and what Scott needs to decide. The review console shows why and shows the evidence. Scott approves in the review console; Prime continues in the orchestrator thread.

---

## V0 vs V1 Summary

| Piece | V0 (this brief) | V1 (future) |
|-------|----------------|-------------|
| `prime_status` | CLI printing to stdout | Bifrost cockpit panel |
| `prime_console` | CLI reading `console.json` | Bifrost review panel, live-updating |
| `prime_approve` | CLI writing `console.json` | Inline UI action in Bifrost |
| `route_to_console()` | Appends to `console.json` | Loom queue event; Bifrost subscribes |
| Queue persistence | Flat JSON file | Loom-managed in-memory + durable store |
| Gate enforcement | `pending_gates()` checked in `relay_executor.py` before dispatch | Loom state machine blocks all dispatch until gate cleared |
| Proof routing | Aegis calls `route_to_console()` directly | Aegis emits `ProofEvent`; Loom routes to console |

The V0 design is intentionally minimal. The same domain objects — `ReviewConsoleQueue`, `ReviewConsoleItem`, `ReviewConsoleAction` — survive into V1. The CLI is replaced by Bifrost surfaces; `route_to_console()` is replaced by event emission; `prime_approve` becomes a UI action. The schema does not change.

---

## What This Brief Is Not

- A Bifrost UI design — that is `docs/bifrost-cockpit-queue-status-brief.md`
- A `relay_executor.py` implementation spec — that is Build 1's next slice
- A Prime conversation protocol — that belongs in Prime's prompt/directive layer
- A complete Aegis proof gate spec — that belongs in a future `docs/aegis-proof-gate-contract.md`

---

## Cross-References

- V0 capability gaps: `docs/v0-build-readiness-map.md`
- Review Console domain model: `meridian_core/review_console.py`
- Aegis proof model: `meridian_core/aegis.py`
- Wake sequence: `meridian_core/wake.py`
- Bifrost cockpit: `docs/bifrost-cockpit-queue-status-brief.md`
- Prime orchestration state model: `docs/prime-orchestration-state-model.md`
- Review Console surface contract: `docs/review-console-surface-contract.md`
