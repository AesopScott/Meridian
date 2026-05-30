# Meridian V1 Capability Plan

**Status:** Architecture plan — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Source:** `docs/v0-v1-progress-tracker.md`, `docs/v0-build-readiness-map.md`
**Revision note:** Rewritten after Scott's V1 clarification — V1 is the cockpit UI release, not a memory/federation release.

---

## V1 Definition

V1 turns V0's CLI-and-domain capabilities into something Scott can see, steer, and operate.

**V1 = Bifrost cockpit live, wired to everything V0 built.**

Scott opens the cockpit and can see: Prime's current intention, all harness liveness states, pending Review Console items and approval gates, active Relay sessions, Aegis proof status, and build progress — without running a CLI command.

### V1 Success Test

Scott opens the Bifrost cockpit. Without typing `prime_status` or `prime_console`:

- He sees Prime's current mission, intention, and next moves.
- He sees all harness statuses (Go / Degraded / Blocked / Offline).
- He sees pending Review Console gate items and can approve them from the UI.
- He sees active Relay session state (dispatched, running, complete, failed).
- He sees Aegis proof findings relevant to current work.
- He sees build progress across lanes.

That is V1. Nothing more.

### Explicitly Out of V1 Scope

- **Echo Harness** — persistent memory engine
- **Atlas Harness** — retrieval/RAG over FileMap and history
- **Multi-user / Federation Harness** — connecting Meridian instances
- **Public/account adapter strategy** — model harness compartmentalization

These are V2 horizon items. See `docs/v2-horizon-plan.md`.

---

## What Must Wait for V0 to Complete

The cockpit panels display live data from V0 harnesses. No panel can be live-wired until its source data exists:

| Panel | V0 dependency |
|---|---|
| Harness status panel | `prime_wake()` + `WakeBrief` emitting per-harness status |
| Review Console panel | `route_to_console()` + `prime_console` CLI producing `ReviewConsoleItem` records |
| Gate approval UI | `prime_approve` CLI + `ReviewConsoleQueue.respond()` |
| Relay session panel | `relay_executor.py` dispatch running and producing session state |
| Aegis proof panel | Relay gate wire + `ProofTrail.is_proof_blocking()` enforced end-to-end |
| Beacon liveness | `beacon.py` `check_harness_liveness()` producing liveness signals |

**Gate:** Do not begin live-data binding for any panel until its V0 source is complete and passing review. Scaffold and layout work can happen in parallel.

---

## What Can Be Designed and Built in Parallel Now

| Work | Parallel opportunity |
|---|---|
| Bifrost app scaffold | Framework, window layout, panel slots — no live data needed |
| Prime conversation surface | Display static or mock orchestrator thread messages |
| Panel component library | Generic status cards, gate item renderers, severity color coding |
| `prime_approve` UI action prototype | Mock approval flow before backend wires up |

**Rule:** Scaffold commits are low-risk and unblock integration. Start them immediately. Do not wait for all V0 gates to clear before touching UI code.

---

## Cockpit Capability Dependency Order

```
V0 gate cleared: prime_wake() → WakeBrief
  └── Harness status panel live                       [Build 5]

V0 gate cleared: route_to_console() + prime_console
  └── Review Console panel live                       [Build 5]
        └── Gate approval UI action live               [Build 5]

V0 gate cleared: relay_executor.py dispatch
  └── Relay session state panel live                  [Build 5]

V0 gate cleared: Relay gate wire + Aegis ProofTrail
  └── Aegis proof/gate panel live                     [Build 5]

V0 gate cleared: beacon.py liveness
  └── Beacon status wired into harness panel          [Build 5]

All panels live
  └── Progress/proof surface (Build 5 configurable)  [Build 5]
        └── End-to-end smoke test                     [Build 5]
```

Build 5 owns all Bifrost implementation slices. Build 4 owns design specs and integration contracts. Build 1 owns any Prime-side event emission needed to feed the cockpit.

---

## Recommended Builder Lane Ownership

| Capability | Primary lane | Notes |
|---|---|---|
| Bifrost app scaffold | Build 5 | Framework decision + window/panel layout |
| Prime conversation surface | Build 5 | Display of orchestrator thread |
| Harness status panel | Build 5 | Reads `WakeBrief`; depends on `prime_wake()` V0 |
| Review Console panel | Build 5 | Reads `ReviewConsoleQueue`; depends on `route_to_console()` V0 |
| Gate approval UI | Build 5 | Calls `ReviewConsoleQueue.respond()`; depends on `prime_approve` V0 |
| Relay session panel | Build 5 | Reads Relay session state; depends on `relay_executor.py` V0 |
| Aegis proof panel | Build 5 | Reads `ProofTrail`; depends on gate wire V0 |
| Progress/proof surface | Build 5 | Configurable per `a412e90` design |
| UI integration design contracts | Build 4 | What each panel binds to and how |
| Prime event emission for cockpit | Build 1 | Any new Prime-side signals needed |

---

## Risk Areas

### 1. UI Sprawl

Every harness will want its own panel. Without a strict layout contract, the cockpit becomes a dashboard maze. The V0 surface rule holds in V1: orchestrator thread (decisions/intentions) vs. review console (evidence/status). A third surface — archive/log view — catches everything else. Three surfaces maximum.

Mitigation: Build 4 writes the UI integration design contract before Build 5 implements panels beyond the scaffold. Each new panel must map to one of the three surfaces.

### 2. Stale Status

Harness status displayed in Bifrost is only as fresh as the last pull from the source. If Bifrost reads a flat file that Prime updates infrequently, status goes stale. Users lose trust in the panel.

Mitigation: V0 harness file writes should be timestamped. Bifrost shows the age of each status reading. Stale = warn after 60s, error after 5min. Do not display status without a timestamp.

### 3. Noisy Progress Surfaces

Build progress from five lanes in parallel produces a lot of noise: idle read checks, staging contamination, read-check commits every 30s. If every commit scrolls through the progress surface, Scott cannot find meaningful events.

Mitigation: The progress surface filters by event type. Read-check commits are folded into a "heartbeat" row, not shown individually. Only task-completing commits and review findings get full rows.

### 4. Prompt Drag Through the UI

If Bifrost sends large context blobs to Prime to display (full queue file content, full FileMap, full proof trail), prompt sizes bloat before Prime can reason. The cockpit must be a display surface, not a context-injection vector.

Mitigation: Bifrost reads domain objects (`ReviewConsoleItem`, `WakeLine`, `RelayRoute`) and renders them. It does not dump raw file content into any Prime prompt. Prime pulls only what it asks for, not what the UI decides to surface.

### 5. Confusing Human Gates

A gate item in the Review Console requires Scott's response. In V0, Scott runs `prime_approve 001`. In V1, the cockpit must make it clear which items require action vs. which are informational. If the panel shows 12 items with no visual distinction between gates and findings, Scott will miss approvals.

Mitigation: Gates get a distinct visual treatment (warning/error severity chip, "Action required" label, approve/reject/modify actions inline). Informational items are collapsed by default. Gate count appears in the cockpit header as a badge.

---

## First 10 Commit-Sized V1 Slices

These are ordered by dependency. Slices 1–3 can start immediately (scaffold only). Slices 4–10 require the named V0 gate to clear first.

| # | Slice | V0 gate required | Lane | File(s) |
|---|---|---|---|---|
| 1 | Bifrost app scaffold — framework, window, panel slots, no live data | None | Build 5 | `bifrost/` |
| 2 | Panel component library — status cards, severity chips, gate renderers | None | Build 5 | `bifrost/components/` |
| 3 | Prime conversation surface — mock orchestrator thread display | None | Build 5 | `bifrost/prime_panel.py` |
| 4 | Harness status panel live — reads `WakeBrief` per harness | `prime_wake()` V0 | Build 5 | `bifrost/harness_panel.py` |
| 5 | Review Console panel live — reads `ReviewConsoleQueue.pending()` | `route_to_console()` V0 | Build 5 | `bifrost/console_panel.py` |
| 6 | Gate approval UI — inline approve/reject/modify for `APPROVAL_GATE` items | `prime_approve` V0 | Build 5 | `bifrost/gate_action.py` |
| 7 | Relay session panel live — reads Relay session state | `relay_executor.py` V0 | Build 5 | `bifrost/relay_panel.py` |
| 8 | Aegis proof panel live — reads `ProofTrail`, shows blocking findings | Relay gate wire V0 | Build 5 | `bifrost/aegis_panel.py` |
| 9 | Progress/proof surface — filtered build progress, folded read checks | All panels live | Build 5 | `bifrost/progress_panel.py` |
| 10 | End-to-end integration smoke test — all panels live with V0 running | All V0 gates | Build 5 | `tests/test_bifrost_integration.py` |

---

## V1 Readiness Gate

V1 ships when:

1. Bifrost cockpit opens and all six panels render without errors.
2. Harness status shows live data from `WakeBrief` (not mocked).
3. A Review Console gate item appears in the cockpit and Scott approves it from the UI (not CLI).
4. Relay session state reflects an active dispatch.
5. Aegis blocking findings surface in the proof panel before Relay clears them.
6. Build progress shows task-completing commits across all lanes, folded heartbeat, with timestamps.

---

## Cross-References

- V0/V1 tracker: `docs/v0-v1-progress-tracker.md`
- V0 capability gaps: `docs/v0-build-readiness-map.md`
- V2 horizon: `docs/v2-horizon-plan.md`
- Prime status console: `docs/prime-status-console-cli-brief.md`
- Review Console surface contract: `docs/review-console-surface-contract.md`
- Bifrost cockpit brief: `docs/bifrost-cockpit-queue-status-brief.md`
- Prime orchestration state model: `docs/prime-orchestration-state-model.md`
