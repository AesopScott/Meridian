# Prompt Packet — Package API Export Decision Note

**Status:** Pre-export planning — PromptPacket not yet in package root  
**Decision owner:** Build 2  
**Reference:** `docs/package-api-surface-note.md`, `docs/prompt-packet-design-brief.md`, `docs/prompt-packet-implementation-checklist.md`

---

## Summary

`PromptPacket` should not be exported from `meridian_core.__init__` until Build 1's validation hardening lands and a full test suite for the domain model is in place. This note records which names belong in the public surface, which stay internal, and what proof is required before the export decision is made.

---

## Names That Should Be Exported (when ready)

```python
from meridian_core import PromptPacket
from meridian_core import PromptPacketError
```

- **`PromptPacket`** — the primary public artifact: validated, immutable prompt bundle. Callers building Relay dispatch flows need to construct and inspect it.
- **`PromptPacketError`** — base validation exception. Callers catching errors from packet construction need this for clean `except` clauses.

`BudgetExceededError` is optional — export it only if callers need to distinguish budget violations from other packet errors. Defer that decision until the exception hierarchy is stable.

---

## Names That Should Stay Internal

```python
# Never in __all__
_validate_budget
_validate_sources
_validate_serialization
_validate_construction_time
_validate_lineage
```

Any `_`-prefixed validation helper lives inside `prompt_packet.py` and is not part of the public contract. Callers interact through `is_valid` and `validation_errors` on the packet, not through validation functions directly.

`BudgetExceededError` and any sub-exception types should stay module-level imports only (`from meridian_core.prompt_packet import BudgetExceededError`) until the hierarchy is proven stable across at least one review cycle.

---

## Tests Required Before Export

The following test categories must exist and pass before any `PromptPacket` name enters `__all__`:

1. **Creation and immutability** — packet constructs correctly; mutation raises under `frozen=True`
2. **Budget compliance** — tokens ≤ max passes; tokens > max sets `is_valid=False` with clear error message
3. **Source compliance** — all lineage sources in allowed list passes; unlisted source sets `is_valid=False`
4. **Serialization integrity** — empty `serialized_prompt` sets `is_valid=False`
5. **Construction time sanity** — negative time rejected; time ≥ 30,000ms rejected
6. **Lineage integrity** — lineage sum ≤ prompt_tokens passes; sum > prompt_tokens sets `is_valid=False`
7. **Input isolation** — mutating the caller's source dict after construction does not affect the packet
8. **Error message quality** — all validation error strings are human-readable and contain the relevant field name

The implementation checklist (`docs/prompt-packet-implementation-checklist.md`) has concrete test skeletons for all of these. All groups must pass before the export gate opens.

---

## Why Export Must Wait for Build 1 Validation Hardening

Build 1 owns the PromptPacket implementation slice. Until that slice lands:

- `meridian_core/prompt_packet.py` may not exist or may be incomplete.
- The validation logic may still have open questions (exception-vs-flag design, `source_lineage` dict vs frozenset, where `__post_init__` runs its checks).
- Exporting a partially-validated or structurally unstable class from the package root creates a public contract that is painful to break later.

The rule from `docs/package-api-surface-note.md` applies: root exports are for **stable** domain objects. `PromptPacket` is not stable until its validation hardening is reviewed and its test suite is complete. Premature export is a one-way door.

Build 2's role here is to prepare the export decision, not execute it.

---

## Relationship to `docs/package-api-surface-note.md`

That note establishes the general principle: root exports are reserved for stable domain objects, primary builder functions, and small enums that are part of public decision contracts. It lists existing exports and candidates for deliberate future export.

`PromptPacket` fits the "stable domain object" category once validation hardening lands. It is not yet on the candidate list in that note because the class does not yet exist. When Build 1 completes the implementation slice and it passes review, the next step is:

1. Add `PromptPacket` and `PromptPacketError` to the candidate list in `package-api-surface-note.md`.
2. Confirm the test gate above is satisfied.
3. Add to `meridian_core/__init__.py` imports and `__all__` in a dedicated export slice (Build 2 scope).

---

## What Build 2 Owns Here

- This planning note only (`docs/prompt-packet-package-api-note.md`).
- When Build 1 validation hardening lands: the `__init__.py` export slice and its smoke test in `tests/test_package_api.py`.
- No implementation edits to `prompt_packet.py` or `tests/test_prompt_packet.py` — those are Build 1 files.
