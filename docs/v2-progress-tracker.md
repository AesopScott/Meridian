# Meridian V2 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view for V2 capability builds. This is the canonical tracker for V2 progress reports: totals first, details second.

**Tracker rule:** Every item is owned by Prime or a harness. No loose feature names without owner assignment.

**Source:** `docs/v2-detailed-build-plan.md`

## V2 Progress Summary

| Owner | Built | In Progress | Needs Build | Total | Percent Complete |
|---|---:|---:|---:|---:|---:|
| Prime Autonomy | 0 | 0 | 2 | 2 | 0% |
| Echo Harness | 0 | 0 | 3 | 3 | 0% |
| Atlas Harness | 0 | 0 | 3 | 3 | 0% |
| Relay/Model Harness | 0 | 0 | 4 | 4 | 0% |
| Aegis Harness | 1 | 0 | 1 | 2 | 50% |
| Session Lifecycle Harness | 0 | 0 | 3 | 3 | 0% |
| Bifrost Harness | 0 | 0 | 3 | 3 | 0% |
| Federation Harness | 0 | 0 | 1 | 1 | 0% |
| **Total V2** | **1** | **0** | **20** | **21** | **4.8%** |

## Built V2 Capabilities

### Aegis Harness

- [x] **Aegis + Prime:** `CognitionPolicy` domain model with action-type/lane/decision enums and policy tier mapping - built in `e08e598`; exposes `CognitionPolicy`, `CognitionPolicyResult`, `cognition_policy_for_tier()`, `evaluate_cognition_policy()` through package root for Relay binding.

## In Progress / Stabilizing

- None currently. V2 domain slices enter full build queue after Codex cadence review completes.

## Needs Build: First Wave

### Prime Autonomy

- [ ] **Prime + Autonomy Contract:** `PrimeNextAction` domain object with action type, confidence, blockers, human-gate requirements - module: `meridian_core/prime_autonomy.py`; tests: `tests/test_prime_autonomy.py`; contract: `docs/prime-autonomy-v2-contract.md`.
- [ ] **Prime + Project State:** deterministic next-action selector taking project/backlog/lane/tier/review gate state - integrates Echo memory query and Atlas retrieval hits as input placeholders.

### Echo Harness

- [ ] **Echo + Memory Contract:** `MemoryRecord`, `MemoryQuery`, `MemoryHit` domain objects - module: `meridian_core/echo.py`; tests: `tests/test_echo.py`; contract: `docs/echo-memory-contract.md`; ranked by project/recency/importance/pinning.
- [ ] **Echo + Repository:** simple local storage abstraction for memory records - deterministic query function for Prime.
- [ ] **Echo + FileMap Integration:** FileMap registration of memory storage location by Build 3.

### Atlas Harness

- [ ] **Atlas + Retrieval Contract:** file/docs-first RAG over FileMap entries and Meridian docs - module: `meridian_core/atlas.py`; tests: `tests/test_atlas.py`; contract: `docs/atlas-retrieval-contract.md`; returns source-aware `AtlasHit` records.
- [ ] **Atlas + Ranking:** deterministic, cheap ranking by path/area/purpose/notes - no embeddings in first slice.
- [ ] **Atlas + FileMap Integration:** FileMap registration of Atlas query surface by Build 3.

### Relay / Model Harness

- [ ] **Model Harness + Metadata:** capability metadata and prompt-drag telemetry fields - module: `meridian_core/model_adapter.py`; contract: `docs/model-harness-v2-contract.md`.
- [ ] **Relay + Model Adapter:** route capability/tier/budget metadata binding - no vendor-specific presets in first slice.
- [ ] **Relay + Dispatch Hardening:** provider-neutral HTTP transport envelope updates for metadata pass-through.
- [ ] **Relay + PromptPacket:** proof metadata integration into dispatch (prompt_packet.py already v1 complete; v2 adds budget/proof bindings).

### Aegis Harness (Remaining)

- [ ] **Aegis + Runtime:** proof requirement enforcement at dispatch time using `CognitionPolicy` decisions - gates high-risk actions in runtime Relay invocation.

### Session Lifecycle Harness

- [ ] **Session Lifecycle + Contract:** `SessionLifecycleState` and `SessionCommandPlan` domain objects - module: `meridian_core/session_lifecycle.py`; tests: `tests/test_session_lifecycle.py`; contract: `docs/session-lifecycle-v2-contract.md`; models spawn/watch/steer/stop/transfer/archive/stale/recover actions.
- [ ] **Session Lifecycle + Workflow:** workflow/sub-agent dispatch contract for bounded harness work - contract: `docs/workflow-subagent-harness-contract.md`; Prime issues typed work orders, receives heartbeats/proof/results.
- [ ] **Session Lifecycle + Permissions:** branch/worktree movement requires Scott or Prime permission object; stale recovery recommendation logic.

### Bifrost Harness

- [ ] **Bifrost + V2 Extensions:** view-model placeholders for Prime next action, Echo memory hits, Atlas retrieval hits, session lifecycle preview, Aegis policy result - module: `bifrost/cockpit.py` (extends v1 snapshot); tests: `tests/test_bifrost_cockpit.py`; contract: `docs/bifrost-v2-extensions-contract.md`.
- [ ] **Bifrost + Cockpit Render:** static render tests and HTML escaping tests for new V2 view-model fields.
- [ ] **Bifrost + FileMap Integration:** FileMap registration of Bifrost cockpit extension surface by Build 3.

### Federation Harness

- [ ] **Federation Harness + Planning:** multi-Meridian/multi-user collaboration architecture (planning phase only) - document: `docs/federation-harness-horizon.md`; no network protocol or permission model implementation in V2 first wave.

## Review Gates for V2

- Every V2 domain slice must include unit tests and pass before marked built.
- Every new module/doc must be routed to FileMap by Build 3.
- Every three task-changing commits per lane must trigger Codex Reviews.
- Any track introducing model calls must prove Aegis policy tests first.
- Any track introducing session actions must prove unique worktree and branch-permission rules.

## Out of V2 Scope (Horizon Only)

- Public product packaging and account-based distribution strategy.
- Multi-user federation runtime and shared mutable project state.
- Vector database or large-scale retrieval infrastructure.
- Full autonomous branch movement and direct destructive session controls.

## V2 First-Wave Recommended Build Order

1. **Aegis:** `CognitionPolicy` domain model (DONE: commit e08e598)
2. **Echo Harness:** deterministic memory records and query
3. **Atlas Harness:** FileMap/docs-first retrieval
4. **Prime Autonomy:** `PrimeNextAction` selector using Echo/Atlas placeholders
5. **Session Lifecycle Harness:** typed lifecycle state and command plan
6. **Bifrost Harness:** static V2 extensions rendering the above
7. **Relay/Model Harness:** metadata binding and prompt-drag hardening
8. **Federation Harness:** planning and horizon architecture

## Reporting Format

Every V2 progress report should begin with:

```text
V2: <built>/<total> built (<percent>), <in_progress> in progress/review, <remaining> left.
```

Then list by harness:

- **Prime Autonomy** — Next-action selection, project state integration
- **Echo Harness** — Durable memory records, ranked query
- **Atlas Harness** — File/docs-first retrieval, source-aware ranking
- **Relay/Model Harness** — Dispatch safety, capability metadata, prompt-drag telemetry
- **Aegis Harness** — Gated cognition, policy-driven proof enforcement
- **Session Lifecycle Harness** — Typed lifecycle state, workflow/sub-agent dispatch
- **Bifrost Harness** — Cockpit V2 extensions, view-model rendering
- **Federation Harness** — Multi-Meridian collaboration (horizon)
