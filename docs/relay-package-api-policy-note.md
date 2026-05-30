# Relay Internals — Package API Policy Note

**Status:** Internal — no Relay dispatch names in package root as of this note
**Decision owner:** Build 2
**Reference:** `docs/package-api-surface-note.md`, `meridian_core/relay_packet.py`, `meridian_core/relay_dispatch.py`

---

## Summary

The following Relay-owned names exist in the codebase and are intentionally **not** exported from `meridian_core.__init__`. They are module-level imports only. This note records the reasoning and the proof required before any future root export.

---

## Names That Stay Internal

```python
# Module-level only — never in __all__ without a further review
from meridian_core.relay_packet import assemble_relay_packet
from meridian_core.relay_dispatch import RelayDispatchLane, RelayDispatchPlan, build_relay_dispatch_plan
```

### `assemble_relay_packet()` (`relay_packet.py`)

Runtime glue that builds a `PromptPacket` from a `RelayRoute`. Reads `route.prompt_budget`, calls `count_tokens()` (internal), and defaults `source_lineage` when not supplied. This is Relay dispatch plumbing — it couples internal helpers (`count_tokens`, `RelayRoute`) that are not themselves package-root exports. Callers who need to construct a packet directly should use `build_prompt_packet()`, which IS exported. `assemble_relay_packet()` is not a stable public builder; it is an internal convenience for Relay's own orchestration.

### `RelayDispatchLane` and `RelayDispatchPlan` (`relay_dispatch.py`)

Structural artifacts of Relay's internal execution model. `RelayDispatchPlan` maps a `RelayRoute` + `PromptPacket` to per-lane model work; `RelayDispatchLane` records one lane's payload and role assignment. These objects are produced inside Relay's dispatch flow and are not intended for direct construction or inspection by callers outside Relay. Callers interact with Relay through higher-level interfaces (Prime, Compass); they do not need to build or decompose dispatch plans.

### `build_relay_dispatch_plan()` (`relay_dispatch.py`)

Builder for `RelayDispatchPlan`. Same reasoning: internal Relay orchestration. The payload in every lane is `packet.model_payload()` — no metadata, no tokens, no lineage crosses into lane payloads. This invariant is safe but the builder itself is not a public contract callers should depend on.

---

## Why These Are Not Ready for Root Export

Three conditions must all hold before any of these names move to `__all__`:

1. **External caller need** — A caller outside Relay (Prime, a test harness, a reporting surface) must need to construct or inspect the object directly, not just receive it from a higher-level call.
2. **Stable domain shape** — The field set and semantics must have survived at least one review cycle without breaking changes.
3. **No undocumented internal dependencies** — `assemble_relay_packet` specifically cannot be exported while `count_tokens` remains module-level; both or neither.

Until those conditions are met, keep these as module-level imports and document any new callers in a cross-check note.

---

## Relationship to `docs/package-api-surface-note.md`

That note establishes the general principle: root exports are for stable domain objects, primary builder functions, and small enums that are part of public decision contracts. Relay dispatch helpers are currently runtime glue and structural intermediates, not stable domain objects intended for direct external use. See `docs/package-api-surface-note.md` for the full export policy and current `__all__` surface.
