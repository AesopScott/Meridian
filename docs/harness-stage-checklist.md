# Harness Stage Checklist

**Purpose:** Track each Meridian harness by build stage so Scott can ask for a harness by name and stage later.

**Rule:** A harness is not complete because its button exists. Completion means backend capability, Prime integration, visible Runtime Logic UI, and proof/review are all aligned.

**Ownership correction:** Prime/Orchestrator coordinates intent, priority, risk tier, proof/human-gate needs, and final decisions. Relay + Model Harness own model-call mechanics: provider/model identity, adapter metadata, prompt payload construction, context-window fit, dispatch/fallback behavior, provider balance, transport gates, and telemetry. Bifrost renders backend-owned state and must not convert taxonomy labels into backend authority.

**HTML view:** `docs/harness-stage-checklist.html`

**Update rule:** When this checklist changes, update the HTML view in the same checkpoint.

## Stage Definitions

| Stage | Meaning | Done When |
|---|---|---|
| Contract / Baseline | The harness has a written contract, checklist, or architecture boundary. | Scope, owner, non-owner boundaries, and acceptance criteria are documented. |
| V2 Backend | The backend requirement is represented in the V2 build plan/tracker. | `docs/v2-progress-tracker.md` has the build item and dependency status. |
| Core Implementation | The harness has typed runtime/domain code. | Runtime module exists with unit tests and no UI-only logic. |
| Prime Integration | Prime can consume the harness state or decision. | Prime packet/source refs/proof path include the harness without hidden interpretation. |
| Runtime Logic UI | Clicking the harness shows `[Harness] Runtime Logic`. | Right-panel UI renders complete backend-sourced logic through a bridge/snapshot path; a titled shell or partial snapshot is not complete. |
| Proofs / Review | The harness has proof gates, tests, and review status. | Tests pass; review state is explicit as cleared, awaiting review, or not started. |
| Operations | The harness can safely execute or mutate live state. | Live actions are gated, auditable, and recoverable. |

## Current Harness Matrix

| Harness | Contract / Baseline | V2 Backend | Core Implementation | Prime Integration | Runtime Logic UI | Proofs / Review | Operations | Next Build |
|---|---|---|---|---|---|---|---|---|
| Prime | built | review-cleared | review-cleared | review-cleared | review-cleared | review-cleared | not live execution | Post-V2 live source refs and operations gating; do not absorb model-call mechanics. |
| Relay / Model | built | review-cleared | review-cleared | partial via Prime source refs | wired | review-cleared | Auto disabled | Post-V2 live provider telemetry and operations gating; keep model-call mechanics Relay/Model-owned. |
| Compass | baseline | review-cleared | review-cleared | partial via Prime source refs | wired | review-cleared | no writes | Post-V2 Prime/live orchestration integration or operations gating. |
| Vulcan / Session Lifecycle | baseline | review-cleared | review-cleared | partial via Prime/Beacon advisory refs | wired | review-cleared | no live command execution | Post-V2 live session operation gating and recovery UX. |
| Aegis | built | built | built | wired into Prime risk input | partial | review-cleared core; Prime binding awaiting review | proof gates only | Runtime Logic UI for Aegis and live proof packet surfaces. |
| Bifrost | built | review-cleared | review-cleared | renders backend snapshots | review-cleared | review-cleared | UI only | Post-V2 operations-gated UI integration. |
| Echo | built | review-cleared | review-cleared | not wired into Prime runtime | not wired | review-cleared core | query only | Post-V2 live memory feed into Prime runtime packet. |
| Atlas | built | review-cleared | review-cleared | not wired into Prime runtime | not wired | review-cleared core + adapter | retrieval only | Post-V2 live retrieval feed into Prime runtime packet. |
| Beacon | baseline/partial | not queued here | partial | not wired into Prime runtime | not wired | partial | observes only | Define heartbeat/liveness Runtime Logic UI and Prime heartbeat input boundary. |
| Charon / FileMap | built | review-cleared | review-cleared | indirect via docs/context | partial | review-cleared | lookup only | Post-V2 Runtime Logic UI reading FileMap state. |
| Arbiter / Reviews | partial | partial | partial | not wired into Prime runtime | not wired | partial | review queue only | Runtime Logic UI for review state and Prime acceptance gates. |
| Workflow | built | review-cleared | review-cleared | bounded work orders only | partial status surface | review-cleared dispatch + Atlas adapter | no live workflow execution | Post-V2 Prime binding and live workflow execution gates. |
| Federation | horizon | horizon | planning only | not wired | not wired | review-cleared planning | no runtime | Keep out of V2 runtime until Prime core is stable. |
| Security / Guardrails | reserved | not queued | not implemented | not wired | not wired | none | none | Define Security harness scope separate from Aegis proof gates. |
| Ratchet / Tool | planned | not queued | not implemented | not wired | not wired | none | none | Define tool execution contract and permission boundaries. |
| Source / Git | planned | not queued | not implemented | not wired | not wired | none | none | Define branch/worktree mutation gates before any UI action. |
| Vision / Browser | planned | not queued | not implemented | not wired | not wired | none | none | Define browser/vision harness contract and proof surface. |
| Autonomy / Release | planned | not queued | not implemented | not wired | not wired | none | none | Define release/autonomy gates after Prime/Vulcan/Aegis mature. |

## Missing Stage Checks

These are the extra stages beyond the initial list that matter for no drift:

| Stage | Why It Matters |
|---|---|
| Contract / Baseline | Prevents building UI or runtime code before ownership is clear. |
| Operations | Separates visible logic from live state mutation. A harness can be visible before it can execute. |
| FileMap / Discoverability | Prime and future sessions must be able to find the harness files without rediscovery. |
| Obsidian / Build Log | Keeps Scott-facing continuity outside Git diffs and short chat memory. |
| Review State | Separates built from accepted. Built-but-awaiting-review is not done. |

## Ask-For-It Format

Use:

```text
Show me <Harness> by stage.
Build <Harness> <Stage>.
What is blocking <Harness> from <Stage>?
Update the Harness Stage Checklist.
```

## Current Priority

1. Keep V2 trackers synchronized with reviewed backend and FileMap landings.
2. Audit post-V2 Prime/live wiring candidates before queueing any operations-capable work.
3. Keep Relay / Model ownership boundaries intact for model-call mechanics.
4. Route Echo/Atlas live-input wiring as post-V2 Prime integration only after backend source refs are explicitly scoped.
