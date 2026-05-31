# Meridian Harness Maturity & Build-Number Policy

**Status:** V2 contract defining Meridian's overall build number, per-harness versioning, maturity levels, and status tracking.

**Audience:** Build lanes, Codex Reviews, Orchestrator, Scott.

**Purpose:** Establish how Meridian tracks progress on each harness from contract baseline through production readiness, and how the overall system build number increments.

---

## Overall Build Number

The Meridian system has a single global **build number** that increments when a "round" of harness work completes the Codex review cadence. Each round is identified as **Build N** and represents a coordinated pass across one or more harness slices.

- **Build 1, 2, 3, 4, 5, ...** represent sequential rounds of work.
- A round is complete when all active tasks in that round pass Codex review and are merged to `main`.
- The build number is published in `docs/live-build-N.md` queue files and in progress trackers.

---

## Per-Harness Build Number

Each harness has its own **harness build number** that tracks the maturity of that harness independently of the overall system.

| Harness | Current Build | Status | Notes |
|---------|---------------|--------|-------|
| **Prime Autonomy** | V2 contract | contract-only | PrimeNextAction domain pending implementation |
| **Echo** | V2 contract + runtime (Build 1) | runtime-awaiting-review | Domain frozen; runtime implementation complete; Codex review pending |
| **Atlas** | V2 contract + runtime (Build 1) | runtime-awaiting-review | Domain frozen; runtime implementation complete; Codex review pending |
| **Relay/Model** | V1 executor + V2 CognitionPolicy | runtime-ready | V1 executor deployed; V2 CognitionPolicy domain complete (Build 1); Relay dispatch v2 API pending |
| **Aegis** | V1 policy + V2 CognitionPolicy | runtime-ready | V1 review harness operational; V2 CognitionPolicy adopted; full v2 surface pending |
| **Session Lifecycle** | V2 contract | contract-only | SessionLifecycleState domain pending implementation |
| **Bifrost** | V1 UI + V2 preview policy | runtime-ready | V1 cockpit UI operational; V2 Electron preview package surface defined; implementation pending (Build 5) |
| **Beacon** | V2 horizon | planning | Logging/telemetry infrastructure planned post-V2 first-wave |
| **FileMap** | V1 + V2 enhancements (Build 3) | runtime-ready | V1 FileArea/FileEntry structure stable; V2 cross-harness registration flow in progress |

---

## Maturity Levels

Maturity progresses through four stages per harness.

### 1. **Contract-Only**

- Domain shape is frozen in `docs/*.md` contracts.
- No runtime code exists or runtime code is incomplete.
- Safe for other harnesses to design against the contract.
- Example: Prime Autonomy `PrimeNextAction`, Session Lifecycle `SessionLifecycleState`.

**Inclusion criteria:**
- Contract document exists and is marked "V2 contract."
- Domain classes, enums, and fields are fully specified.
- Failure-soft behavior is defined.
- First runtime tests are listed.

### 2. **Runtime-Ready**

- Runtime implementation is complete and passes local tests.
- Code is merged to `main`.
- Codex review is requested or complete.
- Harness is safe for downstream to depend on; API is stable.
- Example: Echo runtime, Atlas runtime (pending Codex clearance), Relay executor.

**Inclusion criteria:**
- Implementation code is in the repository.
- Unit tests exist and pass.
- Integration tests exist and pass.
- Codex review has been completed (or is in-flight).
- No known blocking issues.

### 3. **UI-Visible** (for UI harnesses only)

- The harness is rendered in Bifrost and visible to Scott.
- All related contracts, runtime, and UI code are merged.
- Codex review has cleared the UI integration.
- Example: Bifrost cockpit UI (V1), Bifrost preview (V2, pending Build 5).

**Inclusion criteria:**
- Runtime code is runtime-ready.
- UI rendering code is complete.
- Bifrost integration is merged.
- Codex review cleared the UI harness.

### 4. **Production-Ready**

- The harness has been used in production Prime sessions.
- Performance, correctness, and failure modes have been validated under real load.
- No critical or high-priority issues remain.
- Example: Relay V1 executor, Aegis V1 policy engine, FileMap V1.

**Inclusion criteria:**
- UI-visible or runtime-ready (depending on harness type).
- Used in Scott's active sessions for at least one build cycle.
- Operational metrics show healthy behavior.
- No known issues that degrade the experience.

---

## Review & Approval Status

Independent of maturity, each harness slice has a review status that gates progression.

| Status | Meaning | Next Step |
|--------|---------|-----------|
| **contract** | Spec is written; no implementation. | Hand to Build lane for runtime. |
| **runtime-pending** | Code written; awaiting Codex review. | Codex Reviews lane runs round-trip review. |
| **review-cleared** | Codex review complete; no blocking findings. | Merge to `main`; advance to runtime-ready. |
| **review-repair** | Codex review found blocking findings; repair assigned. | Build lane executes repair; resubmit to Codex. |
| **production** | In use by Prime sessions; metrics healthy. | Maintain; monitor for degradation. |

---

## Harness-Specific Status

### Prime Autonomy

- **Maturity:** contract-only
- **V2 contract:** `docs/prime-autonomy-contract.md` (forthcoming)
- **Build number:** V2
- **Status:** PrimeNextAction domain shape to be finalized; runtime pending Build 1
- **Review status:** contract (awaiting finalization)

### Echo (Durable Memory)

- **Maturity:** runtime-ready (pending Codex clearance)
- **V2 contract:** `docs/echo-memory-contract.md` (approved)
- **V2 runtime:** `meridian_core/echo.py` (Build 1, implementation complete)
- **Build number:** V2
- **Status:** Domain frozen; runtime implementation merged; Codex review requested
- **Review status:** runtime-pending

### Atlas (Retrieval Harness)

- **Maturity:** runtime-ready (pending Codex clearance)
- **V2 contract:** `docs/atlas-retrieval-contract.md` (approved)
- **V2 runtime:** `meridian_core/atlas.py` (Build 1, implementation complete)
- **Build number:** V2
- **Status:** Domain frozen; runtime implementation merged; Codex review requested
- **Review status:** runtime-pending

### Relay (Executor & Dispatch)

- **Maturity:** runtime-ready
- **V1 executor:** `meridian_core/relay.py` (production, Build 1)
- **V2 CognitionPolicy integration:** `meridian_core/cognition_policy.py` (Build 1)
- **V2 package API:** Exported to root (Build 2)
- **Build number:** V1 operational; V2 CognitionPolicy integrated
- **Status:** Executor operational; V2 policy domain in use; Relay dispatch v2 architecture pending
- **Review status:** review-cleared (executor); review-cleared (cognition policy)

### Aegis (Policy & Review Harness)

- **Maturity:** runtime-ready
- **V1 policy engine:** `meridian_core/aegis.py` (production, Build 1)
- **V2 CognitionPolicy consumption:** Integrated (Build 1)
- **V2 CognitionPolicy exports:** Root-level public API (Build 2)
- **Build number:** V1 operational; V2 CognitionPolicy adopted
- **Status:** Review harness operational; policy engine mature; V2 surface pending
- **Review status:** review-cleared (v1); review-cleared (cognition policy integration)

### Session Lifecycle

- **Maturity:** contract-only
- **V2 contract:** `docs/session-lifecycle-contract.md` (forthcoming)
- **Build number:** V2
- **Status:** SessionLifecycleState domain shape to be defined; runtime pending Build 1
- **Review status:** contract (awaiting finalization)

### Bifrost (Rendering & Cockpit UI)

- **Maturity:** runtime-ready (V1) / UI-visible pending (V2 preview)
- **V1 cockpit UI:** `bifrost/cockpit.py`, `bifrost/renderer/` (production, Build 4)
- **V1 package exports:** `bifrost/__init__.py` (Build 2 policy)
- **V2 preview policy:** `docs/bifrost-preview-package-api-note.md` (Build 2)
- **V2 Electron app:** Implementation pending (Build 5)
- **Build number:** V1 UI operational; V2 preview package surface defined
- **Status:** Cockpit operational; preview generation architecture defined; Electron implementation pending
- **Review status:** review-cleared (v1); review-cleared (preview policy); awaiting implementation

### Beacon (Logging & Telemetry)

- **Maturity:** contract-only (planning phase)
- **V2 contract:** Horizon document (forthcoming, post-V2 first-wave)
- **Build number:** V2 horizon
- **Status:** Infrastructure for structured logging and metrics to be designed; Build 6+ timeline
- **Review status:** planning

### FileMap (Repository Inventory)

- **Maturity:** runtime-ready
- **V1 structure:** `meridian_core/filemap.py`, `FileArea`, `FileEntry` (production, Build 1)
- **V1 package exports:** Root-level public API (Build 2)
- **V2 cross-harness registration:** Enhancements in progress (Build 3)
- **Build number:** V1 operational; V2 registration flow pending
- **Status:** File registry operational; cross-harness registration pattern pending
- **Review status:** review-cleared (v1); runtime-pending (v2 registration)

---

## Progression Path

A typical harness progression:

1. **Contract written** (e.g., Build 4) → contract-only
2. **Runtime implementation** (Build 1) → runtime-pending review
3. **Codex review passes** → review-cleared, advance to runtime-ready
4. **First production session** (Build N) → production-ready
5. **Maturity maintained** (ongoing) → production-ready

Special cases:
- Some V0/V1 harnesses (Relay, Aegis, FileMap, Bifrost) are already production-ready and only receive V2 enhancements.
- Some V2 harnesses (Prime Autonomy, Session Lifecycle, Beacon) will remain contract-only until Build 1 implementation begins.

---

## How Build 2 Uses This Policy

Build 2 is responsible for **package/API surface** work and **build-number accounting**. When Build 2 completes a docs-only harness accounting task:

1. Update this file with the latest maturity/status for each harness.
2. Capture any Codex review results (cleared, repair, or pending).
3. Reflect completed implementations from prior builds.
4. Close any stale task references in the Active Task section.
5. Commit as a single "accounting slice" with this policy doc and queue entries.

---

## Out of Scope for V2 First-Wave

- Automated build-number generation or CI/CD integration.
- Per-commit maturity tracking or regression detection.
- Cross-harness dependency management (Bifrost only).
- Performance profiling or SLA enforcement.

These belong to V3 and later or to Beacon infrastructure (post-V2).
