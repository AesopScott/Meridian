# Prompt Packet — Package API Export Note

**Status:** Exported — public contract open as of Build 2 commit `f2f69ff`
**Decision owner:** Build 2
**Reference:** `docs/package-api-surface-note.md`, `docs/prompt-packet-design-brief.md`, `docs/prompt-packet-implementation-checklist.md`

---

## Summary

`PromptPacket`, `PromptPacketValidationError`, and `build_prompt_packet` are exported from `meridian_core.__init__` as of commit `f2f69ff`. The export gate opened after Build 1 completed validation hardening in commit `0ce0cf9`, which moved all validation into `PromptPacket.__post_init__`.

---

## Names Exported

```python
from meridian_core import PromptPacket
from meridian_core import PromptPacketValidationError
from meridian_core import build_prompt_packet
```

These are the three stable public names. All appear in `meridian_core.__all__` and are covered by import smoke tests in `tests/test_package_api.py`.

---

## Names That Stay Internal

```python
# Never in __all__
_validate_budget
_validate_sources
_validate_serialization
_validate_construction_time
_validate_lineage
```

Any `_`-prefixed validation helper lives inside `meridian_core/prompt_packet.py` and is not part of the public contract. Callers interact through `is_valid` and `validation_errors` on the packet, not through validation functions directly.

Sub-exception types (e.g. `BudgetExceededError`) remain module-level imports only until the exception hierarchy is stable across a further review cycle.

---

## Why These Exports Are Safe

Three properties justified opening the export gate:

1. **Validated on construction** — all validation runs in `PromptPacket.__post_init__` (Build 1 commit `0ce0cf9`). A successfully constructed object is always in a valid state. Invalid inputs raise `PromptPacketValidationError` before the object exists.
2. **Immutable lineage** — `source_lineage` is copied to a `MappingProxyType` on construction; callers cannot mutate internal state through the original dict.
3. **Clean payload boundary** — `model_payload()` exposes only `serialized_prompt`. Packet metadata (tokens, lineage, construction time, tier) never leaks into the text sent to a model.

---

## Relationship to `docs/package-api-surface-note.md`

`PromptPacket` satisfies the general principle from that note: root exports are reserved for stable domain objects, primary builder functions, and small enums that are part of public decision contracts.

The export decision followed this sequence:
1. Build 1 completed the implementation slice and validation hardening (`0ce0cf9`).
2. Build 2 confirmed the test gate was satisfied (creation, immutability, all 5 validation rules, input isolation, error message quality).
3. Build 2 added to `meridian_core/__init__.py` imports and `__all__` (`f2f69ff`).
4. Build 2 updated `package-api-surface-note.md` to reflect the new surface (`e73b840`).

---

## What Build 2 Owns Here

- This note (`docs/prompt-packet-package-api-note.md`)
- The `__init__.py` export slice and smoke test in `tests/test_package_api.py` (committed `f2f69ff`)

Build 1 owns `meridian_core/prompt_packet.py` and `tests/test_prompt_packet.py`.
