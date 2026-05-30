# V0 Build Readiness Map

**Status:** Strategic/architectural — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Audience:** Prime, Codex, Scott, future contributors
**Purpose:** Name the minimum Meridian capabilities needed before Scott can meaningfully "wake Prime" and let it coordinate work — and be honest about what is missing from each.

**What V0 means:** Prime can be woken, read its mission and portfolio state, produce a progress intention, dispatch a single worker session via Relay, receive the worker's output in the Review Console, and present Scott with a gate item if needed. V0 is not a full orchestration system. It is the smallest end-to-end loop where Prime is the coordinator rather than Scott.

This is a coordinator map, not a roadmap. It does not promise dates or assign owners. It names the gaps.

---

## Reading Key

Each capability section uses this shape:

- **Maturity** — current state tag
- **What exists today** — concrete code or artifacts already in the repo
- **Missing for V0** — what must exist before V0 is reachable
- **Next smallest build slice** — the single commit-sized action that moves this capability forward

---

## 1. Mission Boot

**Maturity:** `domain slice` (partial integration)

**What exists today:**
- `MISSION.md` — exists and readable
- `meridian_core/mission.py` — loads MISSION.md into a structured `Mission` object (`PrimeDirective`, mission name, purpose, directives); raises `MissionLoadError` on bad input; tests passing
- `meridian_core/wake.py` — `WakeBrief`, `WakeLine`, `WakeStatus`; `build_wake_brief()` reads portfolio and heartbeat state and produces a structured Go/Degraded/Blocked/Offline status per harness

**Missing for V0:**
- `build_wake_brief()` is computed but never placed anywhere. Its output does not reach the Review Console as Go-call cards.
- No CLI or harness entrypoint runs the wake sequence when Prime starts. Nothing calls `build_wake_brief()` at startup.
- No MISSION.md version guard — Prime can be woken even if MISSION.md is missing or corrupt. The `MissionLoadError` path needs to actually surface to Scott, not silently fail.

**Next smallest slice:** Add a `prime_wake()` command to `meridian_core/cli.py` that runs `build_wake_brief()`, converts each `WakeLine` to a `SYSTEM_FINDING` ReviewConsoleItem, and prints them to stdout. This is the first moment Prime says "I am awake" to a human-readable surface.

---

## 2. Compass / Progress Intention

**Maturity:** `domain slice`

**What exists today:**
- `meridian_core/intention.py` — `ProgressIntention`, `build_progress_intention()`, `ObjectiveStage`, integrates `CouncilPlan` at the routing layer
- `meridian_core/objectives.py` — `get_mission_objectives()` callable API (designed for Compass UI or CLI)
- `meridian_core/decisions.py` — `DecisionResult` (what Prime decided and why)
- `meridian_core/models.py` — complete typed portfolio model: `Portfolio`, `Initiative`, `Heartbeat`, `NextMove`, `Objective`, `Task`, `Project`, `Venture`

**Missing for V0:**
- No persisted portfolio state. Portfolio is built from sample/synthetic data, not from a real file or durable store.
- Prime has no runtime call path that reads the current portfolio, produces a `ProgressIntention`, and says what moves next. The domain model exists but nothing drives it.
- No CLI output that prints the current intention. There is no way for Scott to ask "Prime, what are you working on?" and get an answer.

**Next smallest slice:** A `prime_intention` CLI command that reads a `portfolio.json` (sample or real) and prints the current `ProgressIntention` to stdout — initiative, next moves, stage, risk tier, council composition. This is the text substitute for the Compass UI until Bifrost exists.

---

## 3. Relay Route + Prompt Packet + Dispatch Plan

**Maturity:** `domain slice` (most complete; dispatch plan ready, executor not built)

**What exists today:**
- `meridian_core/relay.py` — `RelayRoute` carrying `prompt_budget`, context strategy, `CouncilPlan`, `ModelRole`, `SteeringCapability`
- `meridian_core/prompt_budget.py` — `PromptBudgetPlan`, tier-locked rules, token ceilings per tier
- `meridian_core/prompt_packet.py` — immutable validated `PromptPacket` with `__post_init__` validation and `model_payload()` dispatch boundary; tests passing
- `meridian_core/prompt_metrics.py` — `PromptMetricSample`, `PromptMetricSummary` domain types
- `meridian_core/relay_packet.py` — `assemble_relay_packet()` builds a validated packet from a route
- `meridian_core/relay_dispatch.py` — `RelayDispatchPlan`, `RelayDispatchLane`, `build_relay_dispatch_plan()` maps route + packet to per-lane work specs; tests passing (Build 1, `0282b3a`)

**Missing for V0:**
- Nothing executes the dispatch. `build_relay_dispatch_plan()` returns a plan object; no code calls a model API with it.
- Budget enforcement at dispatch time: the token ceiling exists in `PromptBudgetPlan` but Relay does not enforce it when making actual calls.
- Metrics are not emitted or persisted during dispatch.

**Next smallest slice:** `meridian_core/relay_executor.py` — takes a `RelayDispatchPlan` and makes a real Claude API call for each lane (single-lane first), returning raw text. This is the first moment Prime dispatches to a model through Meridian's own harness stack rather than a flat-file queue.

---

## 4. Review Console

**Maturity:** `domain slice` (has Aegis bridge; no persistence or UI)

**What exists today:**
- `meridian_core/review_console.py` — `ReviewConsoleItemType` enum (`CROSS_CHECK`, `PLAN_REVIEW`, `PROOF`, `SYSTEM_FINDING`, `ARTIFACT`, `APPROVAL_GATE`, `COMPARISON`), `ReviewConsoleStatus` enum (`PENDING`, `RESPONDED`, `ACKNOWLEDGED`, `DISMISSED`), item queue, disposition actions (`APPROVE`, `REJECT`, `MODIFY`, `INSPECT`, `ACKNOWLEDGE`)
- `meridian_core/aegis.py` — `AegisEvidence.to_console_item()` already bridges Aegis proof results to `ReviewConsoleItem`; `apply_console_response()` takes Scott's disposition back to Aegis
- `docs/review-console-surface-contract.md` — surface contract fully defined

**Missing for V0:**
- No persistence. Console items are in-memory only and lost on process exit.
- No Scott-facing output. No CLI view, no Bifrost panel. Scott cannot see what Prime placed in the console.
- Prime has no `route_to_console()` call path that routes events (wake Go-calls, worker completions, cross-check findings) to the console at runtime.
- Gate enforcement: gate cards do not block Prime. `APPROVAL_GATE` items exist in the model but no wire stops dispatch until Scott approves.

**Next smallest slice:** A `prime_console` CLI command that reads and prints current in-memory Review Console items with status. A `route_to_console(item_type, summary, provenance)` function that Prime calls to place items. Gate enforcement and persistence can wait for V1.

---

## 5. Beacon / Queue Liveness

**Maturity:** `planned` (model types exist in models.py; no Beacon harness)

**What exists today:**
- `meridian_core/models.py` — `Heartbeat`, `HeartbeatStatus` (`ONLINE`, `DEGRADED`, `BLOCKED`, `FAILED`, `UNKNOWN`), `SteeringCapability`
- `meridian_core/wake.py` — `WakeLine` consumes `Heartbeat` to produce Go/Degraded status per harness
- `meridian_core/intention.py` — `build_progress_intention()` reads heartbeat list to detect blocked harnesses

**Missing for V0:**
- No Beacon harness module. Nothing emits heartbeats. All heartbeats in the system today are constructed from sample state for tests only.
- No liveness poll loop. No degradation detection. No Beacon → Review Console bridge for runtime degradation findings.
- The live-queue flat files are the only liveness signal today — and only a human reading them counts as "alive."

**Next smallest slice:** `meridian_core/beacon.py` — a `check_harness_liveness()` function that checks known harnesses by sentinel (e.g., flat-file queue timestamp, process name, or a sentinel file). Returns a `Heartbeat` per harness. For V0, reading a queue file's last-modified timestamp is sufficient. Full process management can come later.

---

## 6. Bifrost Cockpit

**Maturity:** `planned` (design briefs exist; no code)

**What exists today:**
- `docs/bifrost-cockpit-queue-status-brief.md` — design brief for queue-driven worker activity display
- `docs/bifrost-session-queue-activation-brief.md` — design brief for Prime-owned queue activation from UI
- `docs/review-console-surface-contract.md` — content model fully defined

**Missing for V0:** All of it. No UI code exists.

**V0 substitution strategy:**
Bifrost is not a V0 blocker if two CLI substitutes exist in `cli.py`:
1. `prime_status` — prints mission boot status, current intention, and open Review Console items
2. `prime_approve <item-id>` — lets Scott dispose of gate items from terminal

Full Bifrost cockpit is V1+ scope. V0 is CLI-only.

**Next smallest slice:** The `prime_status` command (covers mission boot + intention + console in one view). `prime_approve` follows immediately after. Both can be thin wrappers over existing domain functions once the CLI entry exists.

---

## 7. Aegis Proof Gates

**Maturity:** `domain slice` (Aegis → Review Console bridge exists; gate wire to Relay not built)

**What exists today:**
- `meridian_core/aegis.py` — `AegisEvidence` with `EvidenceType` (`TEST`, `BROWSER_CHECK`, `SCREENSHOT`, `LOG`, `MANUAL_WAIVER`), `EvidenceStatus`, `EvidenceSeverity`; `ProofTrail`; `is_proof_blocking()`; `to_console_item()` bridge; `apply_console_response()` for disposition feedback
- `meridian_core/models.py` — `Proof`, `ProofType`, `ArtifactKind`
- `meridian_core/risk.py` — `RiskTier`
- Tests for Aegis

**Missing for V0:**
- No live proof execution. `AegisEvidence` is constructed manually. No harness runs tests, takes screenshots, or captures logs into evidence automatically.
- Gate enforcement: `is_proof_blocking()` exists but `relay_executor.py` (not yet built) does not consult it. A tier-3/4 action can today be "dispatched" without Aegis OK, because dispatch itself doesn't exist yet.
- Waiver audit trail: the waiver path is in the domain model but waiver records are not logged to any durable store.

**Next smallest slice:** Wire `is_proof_blocking()` into `relay_executor.py` — before dispatching a tier-3/4 lane, check the `ProofTrail` and raise if any evidence is blocking. Live proof execution (running actual tests into evidence) can follow. The gate wire is the V0 critical path item.

---

## 8. FileMap / Memory Injection

**Maturity:** FileMap `integrated`; Echo/Atlas `planned`; injection factory `domain slice`

**What exists today:**
- `meridian_core/filemap.py` — FileMap domain model, actively maintained by Build 3, indexed by content type; all key docs and domain modules registered
- `meridian_core/injections.py` — `make_injection()`, `SessionInjection` — factory for session injection objects; domain model complete
- `meridian_core/tokens.py` — token counting utilities used by `relay_packet.py`

**Missing for V0:**
- No live memory store (Echo). `SessionInjection` objects are built but never injected into anything.
- No Atlas (RAG retrieval). The FileMap is indexed but nothing queries it and returns ranked injections.
- No injection→packet wiring. `assemble_relay_packet()` does not accept a list of injections and cap them to the budget token ceiling. The budget ceiling exists but the selection algorithm does not.

**Next smallest slice:** Wire `make_injection()` output into `assemble_relay_packet()` — accept a list of `SessionInjection` objects, rank by priority, truncate to the budget ceiling, prepend to `serialized_prompt`. No Echo, no RAG needed — just budget-capped injection. This makes FileMap knowledge usable at dispatch time without waiting for memory infrastructure.

---

## 9. Build Queues / Worker Session Harness

**Maturity:** `integrated` (flat-file queues); `planned` (runtime dispatch and session lifecycle)

**What exists today:**
- Live queue system — `docs/live-build-1.md` through `docs/live-build-5.md` actively used; read/poll/commit/report loop running in this build session
- `meridian_core/relay_dispatch.py` — `RelayDispatchPlan` complete; `build_relay_dispatch_plan()` ready
- `meridian_core/relay_packet.py` — `assemble_relay_packet()` ready
- `meridian_core/injections.py` — `SessionInjection` factory ready

**Missing for V0:**
- No `relay_executor.py`. The dispatch plan has no executor. The flat-file queue is the only live coordination mechanism and it is human-in-the-loop.
- No session lifecycle management — no spawn, steer, wait, or terminate.
- No queue-to-session automation: Prime cannot read a queue file, identify the next task, build a dispatch plan, and launch a session without Scott's manual intervention.
- No structured session output capture. Worker results today are commits to flat files; no output flows into Review Console automatically.

**Next smallest slice:** `relay_executor.py` (shared dependency with items 3 and 7 above). Once a single Claude API call can be dispatched through `RelayDispatchPlan`, the flat-file queue can route to it instead of waiting for a human to paste instructions. Session lifecycle and output routing to Review Console follow after.

---

## V0 Gate Summary

V0 is reachable when these six items exist, in rough dependency order:

| # | Item | Blocker for |
|---|---|---|
| 1 | `prime_wake()` in `cli.py` — reads mission, builds WakeBrief, emits Go-call console items | Mission boot, Beacon visibility |
| 2 | `route_to_console()` + `prime_console` / `prime_status` CLI — Prime places items, Scott reads them | Review Console, all gate items |
| 3 | `relay_executor.py` — takes a `RelayDispatchPlan`, makes a real model API call, returns output | Relay dispatch, session harness, Aegis gate wire |
| 4 | `beacon.py` — `check_harness_liveness()` from flat-file or sentinel | Beacon, `build_wake_brief()` using real data |
| 5 | `prime_approve <item-id>` CLI — Scott disposes of gate items from terminal | Gate enforcement (V0 substitute for Bifrost) |
| 6 | Relay gate wire in `relay_executor.py` — tier-3/4 dispatch blocked if ProofTrail has blocking evidence | Aegis proof gate, gated cognition |

**Dependency chain:**
- Items 1 + 2 → Prime wakes and is visible to Scott
- Items 1 + 2 + 3 → Prime wakes, states intention, dispatches a worker, worker returns output
- Items 1 + 2 + 3 + 5 → Prime wakes, dispatches, shows Scott results, Scott can approve/reject
- Adding 4 + 6 → system is observable and gated

That is V0. Everything else (Bifrost UI, Compass UI, Echo, Atlas, multi-lane Council deliberation, federation) is V1+.

---

## What This Map Does Not Include

- Timeline or owner assignments — this is a capability map, not a sprint plan.
- Implementation details — those belong in per-capability design briefs.
- FileMap entries — Build 3 owns `docs/FileMap.md`.
- Test plans — each build slice owns its own test requirements.
- Cross-references to Polaris lessons — see `docs/polaris-lessons-for-meridian.md`.

---

## Cross-References

- Full capability maturity map: `docs/meridian-capabilities-architecture-map.md`
- Review Console surface contract: `docs/review-console-surface-contract.md`
- Bifrost cockpit queue status: `docs/bifrost-cockpit-queue-status-brief.md`
- Bifrost session queue activation: `docs/bifrost-session-queue-activation-brief.md`
- Relay + Prompt Budget integration: `docs/relay-prompt-budget-integration-brief.md`
- Prompt Packet design: `docs/prompt-packet-design-brief.md`
- Load-bearing principles: `docs/meridian-pillars.md`
- Working vocabulary: `context.md`
