# Prime Continuous Restart/Resteer Logic

**Status:** Architecture plan — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Source:** Live queue experiment observations; Scott's direction on restart/resteer necessity
**Related:** `docs/prime-orchestration-state-model.md`, `docs/v1-capability-plan.md`, `docs/v2-horizon-plan.md`

---

## Prime Directive: Continuous Restart/Resteer

> **Prime never assumes the system is in a known good state. It detects drift, restores operating frame, and adjusts next moves — continuously, not on request.**

This is the Pillar:

1. **Detect** — Prime actively reads live queue files, Beacon signals, Aegis proof trails, and Review Console state to know what every lane is actually doing, not what it was told to do.
2. **Restart** — When a lane's operating frame is broken (idle session, stale task, uncommitted drift, wrong queue), Prime rewrites the frame: new Active Task, cleared stale state, re-anchored Obsidian memory.
3. **Resteer** — When the frame is intact but the next move is wrong (outdated priority, review capacity mismatch, failing proof), Prime changes direction: repair routing, lane pause/resume, new task injection.

Restart restores **what the session believes it is doing**. Resteer changes **what Prime wants it to do next**.

---

## What Prime Must Detect

### Lane State Signals

| Signal | Indicator | Source |
|---|---|---|
| Idle lane | No read check commit in >5 minutes | `live-build-N.md` Read Checks |
| Stale Active Task | Active Task section references a task already completed (commit hash exists) | `live-build-N.md` Active Task + git log |
| Wrong queue routing | Lane is polling a queue file not assigned to it | `live-build-N.md` header, `live-codex-reviews*.md` header |
| Cadence pause overrun | Lane has been paused for >15 minutes without a review result landing | `live-build-N.md` Codex Review Cadence |
| Uncommitted drift | Lane shows local edits in its queue file but no commit | git status per worktree |
| Session polling but not executing | Read checks land but no task-completion commits in >10 minutes when a task is present | `live-build-N.md` timestamps vs. git log |
| Session executing but not committing | Write/Completion Log entries exist but no matching commit hash | `live-build-N.md` Write/Completion Log vs. git log |
| Missing proof | Relay dispatch completed but Aegis blocking finding has not been cleared | `ProofTrail.is_proof_blocking()` result |
| Review capacity mismatch | Codex review slices queued but review lanes are idle or misrouted | `live-codex-reviews*.md` pending slice count |
| Cross-lane contamination | A commit picks up files owned by another lane | git diff for each commit — files outside the lane's allowed set |

### Failure Modes Prime Watches

- **Ghost session** — A session that was once live but is now idle. Its last read check is stale but its Active Task is still marked as running. Other sessions may conflict with or depend on its output.
- **Duplicate task execution** — Two lanes pick up the same Active Task because the stale marker was not cleared after completion.
- **Repair loop** — A Codex review finding routes a repair back to a lane, but the lane never executes it, so the review lane re-finds the same issue on the next sweep.
- **Obsidian memory divergence** — The code repo moves forward but Obsidian build notes are not updated. Prime loses its persistent context anchor.
- **Queue file drift** — Multiple sessions edit the same queue file in the same commit window, producing merge conflicts or contaminated commits.

---

## What Prime Must Do

### Restart Actions

| Trigger | Restart Action |
|---|---|
| Idle lane detected (>5 min, no read check) | Prime rewrites Active Task with a fresh directive and timestamp. Injected via queue file push to origin/main. |
| Stale Active Task (task already committed) | Prime replaces Active Task section with "No active task. Polling." and queues the next logical task if any. |
| Ghost session (session was lost mid-task) | Prime marks the task abandoned, stashes any local-only notes in Obsidian, and re-issues the task to an available lane. |
| Uncommitted drift | Prime injects a repair task: "commit or discard local changes before proceeding." No new work until drift is cleared. |
| Wrong queue routing | Prime corrects the queue assignment in the lane's header and injects a read-check task so the session picks up the correction. |

### Resteer Actions

| Trigger | Resteer Action |
|---|---|
| Cadence pause completed | Prime injects the next task into the queue after verifying the review result. |
| Review capacity mismatch | Prime reassigns a review lane or pauses a build lane to balance throughput. |
| Repair task routed from Codex Reviews | Prime injects the repair as an Active Task in the affected lane's queue before any new work. |
| Proof missing before Relay clears | Prime blocks the Relay dispatch and injects an Aegis proof-clear task for the owning lane. |
| Session executing but not committing | Prime injects a "commit your current slice" task — if the session continues to not commit, Prime escalates to Scott via Review Console. |

---

## Restart vs. Resteer — Decision Matrix

| Situation | Restart? | Resteer? | Both? |
|---|---|---|---|
| Session went idle, no task queued | — | Yes (inject new task) | — |
| Session went idle, task was active | Yes (restore frame) | — | — |
| Session has stale task, is polling | Yes (clear stale task) | Yes (inject new task) | Both |
| Session executing, not committing | — | Yes (prompt commit) | — |
| Proof missing, Relay blocked | — | Yes (inject proof-clear task) | — |
| Wrong queue file | Yes (correct queue assignment) | — | — |
| Review overloaded, build stalled | — | Yes (rebalance) | — |
| Obsidian memory diverged | Yes (re-anchor notes) | — | — |

---

## Harness Mapping

| Component | Role in Restart/Resteer |
|---|---|
| **Beacon** | Liveness signals per lane — Prime's first-line detection for idle or degraded sessions |
| **Relay** | Dispatch executor — Prime blocks or re-routes dispatches when proof is missing or a lane is in restart |
| **Aegis** | Proof trail — Prime reads `ProofTrail.is_proof_blocking()` before Relay clears; resteer target when proof is missing |
| **Review Console** | Escalation surface — when Prime cannot auto-repair (e.g., session never commits), it routes a human gate item here |
| **Bifrost** | Visibility surface — V1 cockpit shows restart/resteer activity as Prime decisions, not just raw queue state |
| **FileMap** | Source of truth for file ownership — Prime uses FileMap to validate that cross-lane contamination has not occurred |
| **Live queue files** | Coordination substrate — restart and resteer actions are injected here; V0 prototype; replaced by domain objects in V2+ |
| **Obsidian memory** | Long-horizon context anchor — Prime re-anchors session notes after any restart to preserve context across session boundaries |

---

## Implementation Phases

### V0 — Markdown Prototype

- Prime manually detects idle lanes by reading `live-build-N.md` Read Checks and comparing timestamps.
- Prime rewrites Active Task sections by direct file edit and push.
- No automation. Detection is Scott-assisted or prime-session-initiated. Repair is a manual commit.
- **This is where we are now.** The live queue experiment is the V0 prototype.

### V1 — Cockpit Visibility

- Bifrost cockpit surfaces lane liveness from Beacon with staleness warnings (>60s = warn, >5min = error).
- Review Console shows repair tasks routed by Prime.
- Gate items appear in the cockpit when escalation is needed (session not committing, proof missing).
- Prime still rewrites queue files manually; Bifrost makes the state readable without a CLI.

### V2+ — Native Runtime

- `prime_wake()` emits `WakeBrief` per lane with staleness state, last-task status, and proof flags.
- Beacon drives a continuous liveness feed; Prime subscribes, not polls.
- Prime can inject Active Tasks via `ReviewConsoleQueue` rather than raw file edit.
- Restart/resteer becomes a first-class Prime capability with domain objects: `LaneState`, `RestartEvent`, `ResteerDirective`.
- Session lifecycle managed by the Session Lifecycle Harness; Prime issues start/stop/reassign through it.
- Uncommitted drift detected by a git status hook on the worktree, surfaced to Prime before any new task injection.

---

## Guardrails

1. **Do not restart a session mid-commit.** If a lane's Read Checks show activity in the last 60 seconds, treat it as potentially in-flight. Wait one more cycle before issuing a restart directive.
2. **Do not inject two Active Tasks.** A queue file may only have one Active Task at a time. Prime must clear the stale task before injecting the new one.
3. **Escalate before force-closing.** If a lane has been unresponsive for >15 minutes and holds an uncommitted slice, do not abandon the work. Route a human gate to Scott: "Session appears lost — confirm abandon or wait."
4. **No resteer during proof gap.** If Aegis has a blocking proof finding, do not inject new tasks to the affected lane. Repair the proof first.
5. **Preserve Obsidian anchor before restart.** Before marking a session abandoned, write what is known about its last state to Obsidian. Do not restart with no memory of what was interrupted.
6. **FileMap ownership before repair.** Before injecting a repair task, confirm the target file is in the allowed set for that lane. Cross-lane repairs route to the owning lane, not the detecting lane.

---

## Cross-References

- Prime orchestration state model: `docs/prime-orchestration-state-model.md`
- V0 build readiness map: `docs/v0-build-readiness-map.md`
- V1 capability plan (cockpit): `docs/v1-capability-plan.md`
- V2 horizon plan: `docs/v2-horizon-plan.md`
- Prime status console CLI brief: `docs/prime-status-console-cli-brief.md`
- Review Console surface contract: `docs/review-console-surface-contract.md`
