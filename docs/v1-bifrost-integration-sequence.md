# V1 Bifrost Cockpit Integration Sequence

**Owner:** Build 4 (architecture)
**Status:** Draft — V1 scaffold in progress
**Date:** 2026-05-31
**Depends on:** `docs/v1-bifrost-live-data-contract.md`, `f56af55` (cockpit-state domain)

---

## Purpose

This document tells each harness owner exactly which steps to execute, in what order, to wire the Bifrost cockpit from static scaffold to live V0 data. Steps are grouped by harness. Parallelism windows are explicit. Review gates are named.

---

## Bifrost Harness

### Step B1 — Static Scaffold (in progress)
- **Input:** Tailwind + component layout spec from Build 5
- **Output:** `bifrost/cockpit/` — static HTML/CSS panel layout with placeholder slots
- **Proof expectation:** `pnpm dev` renders cockpit without errors; all surface panels visible
- **Parallel with:** nothing; all other harness steps wait for B1
- **Review gate:** FileMap registration of `bifrost/cockpit/` before any harness wires into it

### Step B2 — Render Model
- **Input:** `CockpitSnapshot` shape from Build 1 (`f56af55`)
- **Output:** `bifrost/cockpit/render_model.ts` — typed mapping from `CockpitSnapshot` fields to panel props
- **Proof expectation:** TypeScript compiles; render model unit test with stub snapshot passes
- **Parallel with:** P1 (Prime snapshot provider)
- **Review gate:** none; proceed after B1

### Step B3 — Local Preview Command
- **Input:** B2 render model + stub `CockpitSnapshot`
- **Output:** `bifrost/scripts/preview_cockpit.ts` — one-command local preview with mock data
- **Proof expectation:** `pnpm preview:cockpit` renders all panels with mock values; no blank slots
- **Parallel with:** P1, RC1
- **Review gate:** none

### Step B4 — Browser Verification
- **Input:** B3 preview command
- **Output:** screenshot or Playwright smoke test confirming panels render
- **Proof expectation:** all six surface panels visible and non-empty
- **Parallel with:** nothing; gates final V1 cockpit PR
- **Review gate:** Codex review of `bifrost/cockpit/` before merge

---

## Prime Harness

### Step P1 — Cockpit Snapshot Provider
- **Input:** `CockpitSnapshot` domain type (Build 1 `f56af55`), `PromptPacket` dispatch hook
- **Output:** `prime/cockpit_snapshot_provider.py` — emits `CockpitSnapshot` on each turn dispatch
- **Proof expectation:** unit test: dispatch a mock `PromptPacket`, assert snapshot emitted with correct `prime_intention` fields
- **Parallel with:** B2, B3
- **Review gate:** FileMap registration; Codex cadence review if this is the 3rd Build 1 commit

### Step P2 — Current Intention Wire
- **Input:** P1 snapshot provider + B2 render model
- **Output:** `prime_intention` panel slot in Bifrost populated from live snapshot
- **Proof expectation:** integration smoke test: send a turn, cockpit `prime_intention` panel updates
- **Parallel with:** nothing; requires P1 + B2
- **Review gate:** prompt-drag check — verify no snapshot content appears in subsequent `PromptPacket.context`

---

## Review Console Harness

### Step RC1 — Gate List Provider
- **Input:** `ReviewCard` list from `review_console.py`, `CockpitSnapshot.review_gates` field
- **Output:** `review_console/cockpit_gate_provider.py` — emits gate summaries on `ReviewCard` state change
- **Proof expectation:** unit test: mutate a `ReviewCard`, assert `review_gates` summary updates
- **Parallel with:** B2, B3, P1
- **Review gate:** FileMap registration

### Step RC2 — Gate Wire
- **Input:** RC1 gate provider + B2 render model
- **Output:** `review_gates` panel populated in Bifrost
- **Proof expectation:** integration smoke: clear a gate, panel reflects updated status
- **Parallel with:** nothing; requires RC1 + B2
- **Review gate:** none beyond RC1

---

## Beacon Harness

### Step BN1 — Liveness / Age / Stale Signals
- **Input:** existing Beacon heartbeat events
- **Output:** `beacon/cockpit_liveness_provider.py` — emits `{last_seen_at, age_seconds, is_stale}` on tick
- **Proof expectation:** unit test: advance clock past stale threshold, assert `is_stale = True`
- **Parallel with:** RC1, P1
- **Review gate:** FileMap registration

### Step BN2 — Stale Badge Wire
- **Input:** BN1 liveness provider + B2 render model
- **Output:** staleness badge on each cockpit panel driven by `is_stale`
- **Proof expectation:** integration smoke: suppress heartbeat, badges appear after timeout
- **Parallel with:** nothing; requires BN1 + B2
- **Review gate:** none

---

## Relay Harness

### Step RL1 — Lane / Session Dispatch Status
- **Input:** `RelayRoute` dispatch events, `CockpitSnapshot.lane_strip` field
- **Output:** `relay/cockpit_lane_provider.py` — emits lane strip on each dispatch
- **Proof expectation:** unit test: dispatch a route, assert lane strip entry created with correct status
- **Parallel with:** BN1, RC1, P1
- **Review gate:** FileMap registration

### Step RL2 — Lane Strip Wire
- **Input:** RL1 lane provider + B2 render model
- **Output:** lane strip panel populated in Bifrost
- **Proof expectation:** integration smoke: dispatch a route, lane strip updates
- **Parallel with:** nothing; requires RL1 + B2
- **Review gate:** none

---

## Aegis Harness

### Step AG1 — Proof / Gate Status
- **Input:** Aegis proof log, `CockpitSnapshot.instrumentation.review_pending_count`
- **Output:** `aegis/cockpit_proof_provider.py` — emits proof pass/fail counts on each Aegis tick
- **Proof expectation:** unit test: log a proof failure, assert pending count increments
- **Parallel with:** RL1, BN1, RC1, P1
- **Review gate:** FileMap registration; Aegis findings must pass before this step merges

### Step AG2 — Proof Badge Wire
- **Input:** AG1 proof provider + B2 render model
- **Output:** proof/gate badge in bottom instrumentation band
- **Proof expectation:** integration smoke: fail a proof gate, badge goes red
- **Parallel with:** nothing; requires AG1 + B2
- **Review gate:** none

---

## Build / Queue Harness

### Step BQ1 — Lane Strip and Progress-Event Source
- **Input:** `docs/live-build-*.md` active task sections, harness commit hooks
- **Output:** `harness/cockpit_progress_provider.py` — polls queue files and emits `ProgressEvent` list
- **Proof expectation:** unit test: write a mock queue file, assert progress events parsed correctly
- **Parallel with:** AG1, RL1, BN1, RC1, P1
- **Review gate:** FileMap registration; scope must not inject queue file text into Prime

### Step BQ2 — Progress Events Wire
- **Input:** BQ1 progress provider + B2 render model
- **Output:** progress events panel in Bifrost populated
- **Proof expectation:** integration smoke: complete a mock task, progress panel shows new event
- **Parallel with:** nothing; requires BQ1 + B2
- **Review gate:** none

---

## Integration Order Summary

```
B1 (scaffold) ─────────────────────────────────────────────────────┐
                                                                     ▼
B2 (render model) ◄── P1, RC1, BN1, RL1, AG1, BQ1 (all parallel) ──┤
                                                                     ▼
B3 (local preview) ────────────────────────────────────────────────┤
                                                                     ▼
P2, RC2, BN2, RL2, AG2, BQ2 (wire each surface, can parallelize) ──┤
                                                                     ▼
B4 (browser verification / final smoke) ───────────────────────────┘
```

Each "wire" step (P2, RC2, etc.) is independently shippable. A partial cockpit with some panels live and others showing degraded/unknown state is acceptable and preferable to blocking on all wires completing.

---

## Stop Conditions

Prime should pause UI integration work and flag for review when any of the following occur:

| Condition | Action |
|---|---|
| Any cockpit snapshot field appears in a subsequent `PromptPacket.context` | **Hard stop** — prompt-drag detected; audit provider boundary before continuing |
| A wire step produces a blank panel with no degraded fallback | **Pause** — add stale/unknown fallback before merging |
| A proof gate fails (AG2) | **Pause** — do not merge until Aegis clears the failure |
| Bifrost render model TypeScript errors | **Stop** — fix before wiring any surface |
| Queue file text surfaces in any rendered panel | **Hard stop** — Bifrost must only render typed summaries, never raw file content |
| Session count or budget labels appear in Prime prompt context | **Hard stop** — instrumentation band data must not cross the Bifrost/Prime boundary |

---

## Out of Scope for V1

- Echo, Atlas, federation, or multi-tenant provider strategy
- Public-facing or customer-visible cockpit surfaces
- Persistent cockpit state across Prime restarts
- Cockpit write-back or action dispatch (V1 is read-only)
