# Public Exports Readiness Checklist

**Status**: V2 decision framework for when harness objects become package-root exports.

**Purpose**: Provide Build 2 (and the Codex Reviews lane) with a consistent checklist to determine when a V2 harness domain object or builder function is mature enough to add to `meridian_core.__all__` and root-level imports.

---

## Overview

Adding an object to `meridian_core.__all__` (making it a root export) is a **stability commitment**. Callers will import it directly:

```python
from meridian_core import MyDomainClass, build_my_thing
```

Once exported, breaking changes (renaming, removing fields, changing constructor signature) become breaking changes to the library itself. This checklist ensures we only export objects that are:

1. **Proven in runtime**: The implementation is complete and tested.
2. **Documented**: Callers understand the object's purpose and use.
3. **Registered**: The object is listed in `meridian_core.registries` or equivalent catalogs.
4. **Properly named**: The name is unambiguous and won't conflict with future features.
5. **Safe**: No known backward-compatibility risks, and related objects either ship together or are deferred together.

---

## Readiness Checklist

### Section 1: Runtime Stability

Before exporting, the harness object must be proven in runtime.

- [ ] **Implementation is complete** — The class or function is fully implemented in `meridian_core/harness.py`.
- [ ] **No TODOs or FIXMEs** — The code has no lingering comments about incomplete features.
- [ ] **Immutable pattern** — Objects are immutable or use copy-on-write; no hidden state mutations.
- [ ] **Constructor validation** — If the object is a dataclass/pydantic model, `__post_init__` or validation runs and rejects invalid inputs before the object exists.
- [ ] **Error handling** — All error paths are explicit; no silent failures or generic exceptions.
- [ ] **Bound by contract** — The object matches its corresponding `docs/*.md` contract; no deviations.

**Decision**: If any box is unchecked, the object is **not runtime-ready**. Defer export.

### Section 2: Tests

Exported objects must have comprehensive test coverage.

- [ ] **Unit tests pass** — `python -m pytest tests/test_harness.py -v` runs cleanly with no failures.
- [ ] **Coverage ≥80%** — The harness module has at least 80% line coverage.
- [ ] **Integration tests pass** — Cross-harness tests (e.g., Echo output fed to Atlas) pass.
- [ ] **Happy path tested** — Standard usage patterns are covered.
- [ ] **Error cases tested** — Invalid inputs, edge cases, and known failure modes are tested.
- [ ] **No skipped tests** — No `@pytest.mark.skip` or `xfail` in the test suite without documentation.

**Decision**: If any box is unchecked, the object is **not proven**. Defer export and add test coverage first.

### Section 3: Documentation

Callers must know what the object does and how to use it.

- [ ] **Docstring is complete** — The class/function has a docstring explaining purpose, parameters, return value, and common use cases.
- [ ] **Contract doc is stable** — The object is documented in `docs/harness-contract.md` and that contract is marked "approved" or "stable".
- [ ] **No internal references** — The docstring and contract don't reference internal implementation details.
- [ ] **Example code is provided** — A usage example exists in the contract doc or in a tutorial.
- [ ] **Failure modes are documented** — Expected exceptions and what triggers them are listed.

**Decision**: If any box is unchecked, update docs before export.

### Section 4: FileMap & Registry Registration

Exported objects should be registered in the project's metadata system.

- [ ] **FileMap entry exists** — If the object is a harness domain type, it has a `FileArea` in `docs/file-map.md` or is registered via Build 3's FileMap harness.
- [ ] **registry/*.md entry exists** — The object is listed in `docs/registries/` with its full module path, type, and stability status.
- [ ] **No name collisions** — The exported name doesn't conflict with any other root export or future reserved name.
- [ ] **Cross-harness callers recorded** — Any harnesses that import this object are noted in the registry as consumers.

**Decision**: If any box is unchecked, work with Build 3 (FileMap) and Build 2 (registries) to register before export.

### Section 5: Naming & Backward-Compatibility

The exported name must be forward-compatible and unambiguous.

- [ ] **Name is unambiguous** — The name doesn't suggest the wrong thing or conflict with similar names in other modules.
- [ ] **Prefix/suffix follows convention** — Domain classes use PascalCase; helper functions use snake_case; builders use `build_*`.
- [ ] **No generic names** — Avoid single-word names like `Query` or `Result` without a harness prefix (e.g., `AtlasQuery`, `RelayRoute`).
- [ ] **No `Internal` or `Private` suffix** — If the object is internal, it should not be exported (add to allowed files list instead).
- [ ] **Public API is stable** — Fields, constructor arguments, and method signatures are unlikely to change in the next 2 releases.
- [ ] **Related objects ship together** — If exporting `AtlasHit`, also export `AtlasQuery` and `AtlasResult` in the same commit; don't leave gaps.

**Decision**: If any box is unchecked, rename the object or defer its related siblings until all are ready.

### Section 6: Safety & Risk Mitigation

Exporting an object creates a stability obligation; minimize future breaking changes.

- [ ] **No speculative generality** — The object is designed for **current** use cases, not hypothetical future ones.
- [ ] **No mutable collections** — If the object contains a list or dict, it's copied to a read-only view on construction (e.g., `MappingProxyType`).
- [ ] **Enum values are frozen** — If the object contains an enum, the enum is complete; adding values later will not surprise callers.
- [ ] **Inheritance is clear** — If the object is a subclass, the parent class is also exported (or is already part of a standard library).
- [ ] **No hidden dependencies** — All required imports are explicit in the module; no circular import hazards.
- [ ] **Version checked** — The object works with the minimum Python version Meridian targets (e.g., 3.10+).

**Decision**: If any box is unchecked, redesign the object to be simpler and more stable, or defer export.

---

## Export Decision Framework

Once all six sections are reviewed:

| Outcome | Action |
|---------|--------|
| **All sections cleared** | Export the object to `meridian_core.__all__`. Update `meridian_core/__init__.py` to import and re-export it. |
| **1–2 boxes unchecked** | **Defer and address**: Identify which boxes are blocking; fix them; re-check. |
| **3+ boxes unchecked** | **Not ready for export**: The object needs significant work. Focus on the highest-priority gaps (usually tests, docs, or design). Defer to a later cadence. |
| **Design concerns flagged** | **Consult Codex**: If the checklist reveals a deeper design issue (name collision, unsafe mutability, speculative generality), submit to Codex Reviews for guidance before re-exporting. |

---

## Per-Harness Export Status

Track which objects from each harness are exported, pending, or deferred:

### Echo (Durable Memory)

- **Exported**: `MemoryRecord`, `MemoryQuery`, `MemoryHit` (pending Build 1 runtime completion + Codex clearance)
- **Pending**: `MemoryKind` enum, `MemorySource` enum
- **Deferred**: Private repository methods, internal validators

### Atlas (Retrieval)

- **Exported**: `AtlasQuery`, `AtlasHit`, `AtlasResult` (pending Build 1 runtime completion + Codex clearance)
- **Pending**: `AtlasSource` enum
- **Deferred**: Optional Echo integration internals; custom scoring functions

### Prime Autonomy

- **Exported**: `PrimeNextAction` (pending Build 1 implementation + Codex clearance)
- **Pending**: Helper types for action decomposition
- **Deferred**: Internal policy selection logic

### Session Lifecycle

- **Exported**: `SessionLifecycleState`, `SessionCommandPlan` (pending Build 1 implementation + Codex clearance)
- **Pending**: Heartbeat and recovery enums
- **Deferred**: Internal state machine logic

### Workflow Dispatch

- **Exported**: `WorkflowWorkOrder`, `WorkflowHeartbeat`, `WorkflowResultSummary`, plus enums (pending Build 1 implementation + Codex clearance)
- **Pending**: Error summary types
- **Deferred**: Internal dispatch routing logic

---

## Process: Using This Checklist

1. **Harness author (Build 1)** completes the runtime implementation and writes tests.
2. **Build 2** reviews the checklist for each object planned as an export.
3. **For each object**: Ask "are all six sections ready?" If not, note the gaps.
4. **Codex Reviews** reviews the export decision and the checklist; flags any design concerns.
5. **Build 2** updates `meridian_core/__init__.py` to add cleared objects to `__all__` and imports.
6. **Build 2** updates this checklist document with the export status for the next review cycle.

---

## Maintenance

This checklist is a living document. As each harness ships and new use cases emerge:

- Update the **per-harness export status** table to reflect new exports.
- If a section is repeatedly unchecked for similar reasons (e.g., "naming is unclear"), add guidance to that section.
- If a newly exported object causes issues downstream, review this checklist to identify what we missed.

---

## Success Criteria

This checklist is successful when:

1. **Export decisions are consistent** — Two objects in similar readiness states receive the same decision (both exported or both deferred).
2. **No surprises** — Newly exported objects don't require breaking changes within a year.
3. **Clear ownership** — Build 2 and Codex Reviews have a shared vocabulary for "export-ready."
4. **Guides Build 1 and Build 5** — Other build lanes reference this checklist when planning their implementations to ensure export-readiness from the start.
