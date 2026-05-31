# Harness Maturity and Build-Number Policy

**Status**: V2 build infrastructure policy — defines maturity tracking, build numbers, and readiness states for Meridian harnesses.

**Purpose**: Establish a consistent way to track the implementation state, review state, and readiness of each harness across V0 (operational), V1 (stabilization), and V2 (new harnesses). Enables progress reporting, capability statements, and dependency management.

---

## Overall Build Number

The **overall build number** advances by one when three conditions are met:

1. **All harnesses in the build lane have code changes (commits) that move them forward** — a commit must be made for each harness in scope, even if it's a docs-only or minor polish commit.
2. **Codex review has cleared all changes** — a Codex Reviews lane reviews the three commits and clears them with no blocking findings.
3. **Scott acknowledges the cadence** — when the Codex Reviews lane records its result, the orchestrator increments the overall build number and resets the per-harness cadence counters.

For example:
- **Build 1, Cadence 1**: Echo runtime implementation commit + Atlas query model commit + FileMap integration commit → Codex clears → Build 1 Cadence 1 recorded, counters reset to Cadence 2.
- **Build 2, Cadence 1**: Prime Autonomy schema commit + Relay policy commit + Bifrost preview commit → Codex clears → Build 2 Cadence 1 recorded.

---

## Per-Harness Build Number and Maturity Level

Each harness has a **per-harness build number** that reflects how many completed cadences it has shipped:

| Harness | Current Build | Cadence | Maturity | Review Status | Readiness State |
|---------|---------------|---------|----------|---------------|-----------------|
| **Prime Autonomy** | V2.0 | 1 of 3 | Contract baseline | Awaiting first implementation | Contract-only |
| **Echo (Durable Memory)** | V2.0 | 1 of 3 | Runtime implementation in progress | Runtime under development | Runtime-ready (pending review) |
| **Atlas (Retrieval/RAG)** | V2.0 | 1 of 3 | Runtime implementation in progress | Runtime under development | Runtime-ready (pending review) |
| **Relay (Model & Routing)** | V1.2 | 1 of 3 | Mature; V2 executor wrapper added | Review-cleared (V1.2 + V2 policy) | Production-ready |
| **Aegis (Proof & Evidence)** | V1.1 | 1 of 3 | Mature; V2 integration planned | Review-cleared | Production-ready |
| **Beacon (Observability)** | V1.0 | 1 of 3 | Mature; expansion planned | Review-cleared | Production-ready |
| **Session Lifecycle** | V2.0 | 1 of 3 | Contract baseline | Awaiting first implementation | Contract-only |
| **Bifrost (Cockpit UI)** | V1.1 | 1 of 3 | Mature; V2 Electron app planned | Review-cleared (V1.1 + preview policy) | UI-visible (V1); Electron in progress |
| **Workflow Sub-Agent Dispatch** | V2.0 | 1 of 3 | Contract baseline | Awaiting first implementation | Contract-only |

---

## Maturity Levels

Each harness operates at one of these maturity levels:

### Contract-Only
- **Definition**: Public contract is written and frozen; no runtime code exists yet.
- **When used**: Early phases of a new V2 harness (Echo, Atlas, Prime Autonomy, Session Lifecycle, Workflow).
- **Advancement**: Implement the first slice of runtime code → move to "Runtime implementation in progress".
- **Readiness state**: Contract-only.

### Runtime Implementation in Progress
- **Definition**: Runtime code is being built and tested; contract may receive minor clarifications but major changes require review.
- **When used**: While Build 1 or another lane is actively implementing the harness.
- **Advancement**: Complete first-wave implementation and pass Codex review → move to "Runtime-ready (pending review)".
- **Readiness state**: Runtime-ready (pending review).

### Mature
- **Definition**: The harness has shipped in a released version (V0 or V1); contract is stable; new features come as minor updates within the same build number or as a new build cadence.
- **When used**: Relay, Aegis, Beacon, Bifrost (V1 shell).
- **Advancement**: Add new V2 extensions, policy wrappers, or UI updates; ship within same build or next cadence → move to next V-number.
- **Readiness state**: Production-ready (and UI-visible if a cockpit harness).

---

## Review Status

Each harness is tracked in one of these review states:

- **Awaiting first implementation**: Contract is ready; implementation has not started.
- **Runtime under development**: Code is being written; Codex review has not yet cleared it.
- **Review-cleared**: Codex review has examined the code and found no blocking findings; the harness can advance or ship.
- **Awaiting clarification**: Codex review found questions or minor gaps; waiting for feedback.
- **Deferred**: Lower-priority work; scheduled for a later cadence.

---

## Readiness States

The readiness state reflects what consumers of the harness can expect:

### Contract-Only
- Harness has a public contract but no runtime.
- Callers can study the contract; no implementation to depend on yet.
- Example: Prime Autonomy V2.0.

### Runtime-Ready (Pending Review)
- Runtime code exists and passes unit tests.
- Codex review has not yet cleared it, or is in progress.
- Other harnesses should not yet depend on it for production.
- Example: Echo V2.0 (after first implementation is complete).

### Runtime-Ready (Cleared)
- Runtime code exists, is tested, and Codex review has cleared it.
- Other harnesses can depend on it.
- Still may be incomplete (first-wave implementation).

### Production-Ready
- The harness has shipped in a released version; all features are stable.
- Breaking changes require a major version bump.
- Other harnesses depend on it for critical paths.
- Example: Relay V1.2, Aegis V1.1.

### UI-Visible
- The cockpit (Bifrost) can render this harness's state and interactions.
- Applies to Bifrost itself and to harnesses that expose UI views.
- Example: Bifrost V1.1 (cockpit shell is UI-visible and production-ready).

---

## Build Cadence and Advancement Rules

### Cadence Rhythm
Each harness advances through cadences (1 of 3, 2 of 3, 3 of 3) in sync with its build lane:

1. **Cadence 1 of 3**: First commit in the three-commit cycle. Harness may ship a feature, polish, docs, or integration work.
2. **Cadence 2 of 3**: Second commit. Another harness or the same one makes progress.
3. **Cadence 3 of 3**: Third commit. The three-commit batch is complete.
4. **Codex Review**: Codex Reviews lane reviews all three commits and records pass/fail.
5. **Cadence Cleared**: Orchestrator increments the overall build number and resets cadences to 1 of 3.

### Advancement Rules

- A harness moves from **Contract-Only** to **Runtime in Progress** when the first implementation commit lands.
- A harness moves from **Runtime in Progress** to **Runtime-Ready (Cleared)** when Codex review clears the first-wave implementation.
- A harness moves from **Runtime-Ready (Cleared)** to **Mature** when it ships as part of a released version.
- A harness increments its build number (e.g., V2.0 → V2.1) when it ships a significant feature or reaches a stability milestone after review.

---

## Harness Ownership and Build Assignments

Each harness is owned by one primary build lane during implementation:

| Harness | Owner Lane | Other Lanes | Status |
|---------|------------|-------------|--------|
| Prime Autonomy | Build 1 | — | Contract baseline; awaiting Build 1 implementation start |
| Echo | Build 1 | — | Build 1 implementing runtime; contract baseline established |
| Atlas | Build 1 | — | Build 1 implementing runtime; contract baseline established |
| Relay/Model | Build 1 | Build 2 (policy) | Build 1 maintains runtime; Build 2 owns policy/wrapper docs |
| Aegis/Proof | Build 2 | Build 1 (runtime) | Build 1 maintains runtime; Build 2 owns package API surface decisions |
| Beacon | Build 4 | — | Build 4 owns implementation and any V2 extensions |
| Session Lifecycle | Build 1 | — | Contract baseline; awaiting Build 1 implementation start |
| Bifrost | Build 5 | Build 2 (policy) | Build 5 owns Electron app; Build 2 owns package API policy |
| Workflow Sub-Agent | Build 1 | — | Contract baseline; awaiting Build 1 implementation start |

---

## Policy: Build-Number vs. Feature Branch

- **Build numbers** track completed, review-cleared cadences.
- **Feature branches** track in-progress work across any number of commits before cadence completion.
- A feature branch may have 10+ commits; the build number increments only when all three cadence commits are cleared.
- This decouples rapid iteration from stable release tagging.

---

## Integration with V0/V1 Stability

V0 and V1 harnesses that were already shipped do not change build numbers during V2 unless they receive breaking changes:

- **Relay V1.2**: Receives V2 executor-policy wrapper → stays V1.2 (wrapper is V2 semantics, harness is still V1).
- **Aegis V1.1**: Receives V2 integration planning → stays V1.1 until an implementation lands.
- **Bifrost V1.1**: Receives V2 Electron app → Electron is V2, cockpit shell is still V1.1 until next major release.

---

## Living Document

As each harness advances through cadences and Codex clears them, update this table:

- When Build 1 ships a cadence-cleared Echo runtime → update Echo maturity to "Runtime-ready (Cleared)" and readiness to "Runtime-ready (Cleared)".
- When Build 1 ships Echo runtime integration with Atlas → increment Echo build number if it's a milestone, or leave at V2.0 if it's incremental.
- When V2 ships its first major milestone → all V2 harnesses may move from V2.0 to V2.1 if cadence is cleared.

---

## Success Criteria

This policy is successful when:

1. **Each harness has a clear maturity level** — Scott, reviewers, and other build lanes know what's available and what's coming.
2. **Build numbers track completed work** — the overall build number advances only when three commits are cleared.
3. **Readiness states guide integration** — callers know if a harness is safe to depend on.
4. **Cadences stay synchronized** — all harnesses in a build lane complete their work within the same three-commit rhythm.
