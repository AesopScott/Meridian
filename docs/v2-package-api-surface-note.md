# V2 Package API Surface Note

\\\Status:\\\ V2 first-wave package API policy — defines which domain objects should eventually be public \meridian_core\ root exports once their runtime slices are built and review-cleared.

\\\Purpose:\\\ Guide Build 1 (runtime) and Build 2 (package API decisions) on what becomes root-exported public surface vs. module-level imports for V2 harnesses.

---

## Principle

V2 harnesses introduce new domain objects. These objects should be root-exportable only after:

1. The runtime implementation is built and unit-tested.
2. The contract is complete and review-cleared.
3. Cross-harness integration has been proven (e.g., Echo hits flowing to Atlas, Atlas hits flowing to Relay/Aegis).

Until then, they live as module-level imports. This protects the public API from churn and ensures that callers of \meridian_core\ see only stable, proven surfaces.

---

## Echo Harness (Durable Memory)

\\\Contract:\\\ \docs/echo-memory-contract.md\ (complete; runtime implementation pending).

\\\Intended public surface (once built and cleared):\\\

- \MemoryRecord\ — immutable durable memory entry with summary, body, source, importance, pinning, supersession.
- \MemoryQuery\ — typed query with project, kinds, tags, since, limit, include_superseded.
- \MemoryHit\ — ranked result with record, score, reason.
- \MemoryKind\ enum — DECISION, FACT, PLAN, GATE_OUTCOME, STANDING_INSTRUCTION, NOTE.
- \MemorySource\ enum — PRIME, USER, REVIEW_CONSOLE, WORKER, IMPORT.

\\\Why public:\\\ Prime, Atlas, Bifrost, and Aegis all consume these objects. A stable, public typing is load-bearing for V2.

\\\Stability guarantee:\\\ Once Echo's runtime lands and cross-harness proof is complete, these names should be frozen. Changes to MemoryRecord fields or MemoryKind values are breaking changes.

\\\Current location:\\\ Will be in \meridian_core/echo.py\ with public exports via \meridian_core/__init__.py\ after Build 1 builds it and Build 2 routes the exports.

\\\Candidates for deferral:\\\ Private repository methods and internal validators stay in the module; only the domain classes and public query/result types become root exports.

---

## Atlas Harness (Retrieval / RAG)

\\\Contract:\\\ \docs/atlas-retrieval-contract.md\ (complete; runtime implementation pending).

\\\Intended public surface (once built and cleared):\\\

- \AtlasHit\ — single retrieval result with path, title, reason, excerpt, source, score.
- \AtlasQuery\ — typed query with terms, areas, required_paths, include_echo, project, limit.
- \AtlasResult\ — full response with hits, missing_paths, truncated.
- \AtlasSource\ enum — FILEMAP, DOC, ECHO.

\\\Why public:\\\ Prime calls Atlas directly. Bifrost renders hits. Aegis reviews hit excerpts. These objects form the public interface.

\\\Stability guarantee:\\\ Once Atlas's runtime lands and FileMap integration is proven, these names should be frozen. Changes to AtlasHit fields or AtlasSource values are breaking.

\\\Current location:\\\ Will be in \meridian_core/atlas.py\ with public exports via \meridian_core/__init__.py\ after Build 1 builds it and Build 2 routes the exports.

\\\Candidates for deferral:\\\ The optional Echo integration in Atlas lives as an internal implementation detail initially. The public surface assumes \include_echo=False\ in the first slice. When Echo folding is enabled, the return shape does not change — only the internals.

---

## Prime Autonomy (Next-Action Selection)

\\\Contract:\\\ \docs/prime-autonomy-v2-contract.md\ (not yet written; referenced in v2-detailed-build-plan.md).

\\\Intended public surface (once contract and implementation land):\\\

- \PrimeNextAction\ — domain object capturing proposed action, confidence, blockers, human-gate requirements, and reasoning summary.

\\\Why public:\\\ Prime's autonomy depends on a stable, typed representation of "what should I do next?" Callers should not have to parse prose or infer structure.

\\\Stability guarantee:\\\ Once Prime Autonomy's implementation is built and validated against real project state, the \PrimeNextAction\ shape should be frozen.

\\\Current location:\\\ Will be in \meridian_core/prime_autonomy.py\ with public exports via \meridian_core/__init__.py\ after Build 1 builds it and Build 2 routes the exports.

---

## Session Lifecycle Harness (Spawn, Watch, Steer, Recover)

\\\Contract:\\\ \docs/session-lifecycle-v2-contract.md\ (not yet written).

\\\Intended public surface (once contract and implementation land):\\\

- \SessionLifecycleState\ — immutable snapshot of current session state with timestamps, branch/worktree info, heartbeat history, and permission context.
- \SessionCommandPlan\ — typed command to a session (spawn, watch, steer, stop, transfer, archive, stale_recovery, restart_request).

\\\Why public:\\\ Prime coordinates session lifecycle. user views session state in Bifrost.

\\\Stability guarantee:\\\ Once Session Lifecycle is built, the command vocabulary and state enum should be frozen.

\\\Current location:\\\ Will be in \meridian_core/session_lifecycle.py\ with public exports via \meridian_core/__init__.py\ after Build 1 builds it and Build 2 routes the exports.

---

## Workflow Sub-Agent Harness (Dispatch, Heartbeat, Result)

\\\Contract:\\\ \docs/workflow-subagent-harness-contract.md\ (complete; runtime implementation pending).

\\\Intended public surface (once built and cleared):\\\

- \WorkflowWorkOrder\ — complete, self-contained instruction to a workflow sub-agent.
- \WorkflowInputPacket\ — context given to the sub-agent.
- \WorkflowHeartbeat\ — periodic status update.
- \WorkflowResultSummary\ — successful result.
- \WorkflowErrorSummary\ — error result.
- \WorkflowResteerRequest\ — suggestion to Prime for a modified work order.
- \WorkflowHarness\ enum — ECHO, ATLAS, AEGIS, RELAY, BIFROST, BEACON, SESSION_LIFECYCLE.
- \WorkflowPhase\ enum — STARTED, WORKING, WAITING_FOR_TOOL, WAITING_FOR_GATE, WARNING, FINALIZING.
- \WorkflowFailureKind\ enum — TIMEOUT, TOOL_DENIED, INPUT_INVALID, PROOF_UNAVAILABLE, GATE_REQUIRED, INTERNAL_ERROR, RESTEER_REQUESTED.

\\\Why public:\\\ Prime issues work orders directly. Every harness that does bounded work consumes the work-order shape.

\\\Stability guarantee:\\\ Workflow dispatch is the contract between Prime and sub-agent harnesses. Changes are breaking.

\\\Current location:\\\ Will be in \meridian_core/workflow_dispatch.py\ with public exports via \meridian_core/__init__.py\ after Build 1 builds the sub-agent spawn/watch infrastructure and Build 2 routes the exports.

---

## Integration with V0/V1

Echo, Atlas, Prime Autonomy, Session Lifecycle, and Workflow dispatch are additive. They do not change existing public exports (Mission, RiskTier, RelayRoute, PromptPacket, Aegis*, Bifrost*, etc.). Those remain stable.

---

## Review and Deferral Conditions

These exports are deferred until:

1. The runtime module is built (Build 1).
2. The module is tested (unit tests passing, ≥80% coverage).
3. The Build 2 + Build 1 integration is proven (cross-module imports succeed, package API tests pass).
4. Codex review is complete and no blocking findings remain.

---

## Next Steps

1. Build 1 implements Echo, Atlas, Prime Autonomy, Session Lifecycle.
2. Build 2 exports these to \meridian_core.__init__\ with comprehensive package API tests.
3. Build 1 ensures Workflow dispatch infrastructure is complete.
4. Build 2 exports Workflow types to \meridian_core.__init__\.

This note is living documentation. As each harness is built, update with actual field names, integration discoveries, and stability guarantees.
