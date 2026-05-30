# Relay Executor — Package API Policy Note

**Status:** Provisional — `relay_executor.py` not yet landed (Build 1 in progress)
**Decision owner:** Build 2
**Reference:** `docs/package-api-surface-note.md`, `docs/relay-package-api-policy-note.md`

---

## Summary

This note establishes the policy for how Relay execution helpers should reach the `meridian_core` package root once Build 1 lands `relay_executor.py`. It does not preemptively export anything — root exports require a real module to audit against.

---

## What Belongs at `from meridian_core import ...`

A name belongs at the package root when all three conditions hold:

1. **External caller need** — Prime or another top-level surface (Compass, a reporting harness) directly constructs or inspects the object. If callers only see results produced by Relay, the name stays internal.
2. **Stable domain shape** — The field set and semantics have survived at least one review cycle without breaking changes.
3. **No undocumented internal dependencies** — The name must not couple unexported helpers that would force those helpers to be exported alongside it.

Relay execution candidates that could satisfy these conditions once Build 1 stabilizes:

- A top-level execution result type (e.g. `RelayExecutionResult` or equivalent) — callers need to inspect outcomes.
- A primary execution entry point (e.g. `execute_relay` or equivalent) — callers need to invoke execution.

---

## What Should Remain Module-Local

Names that are internal Relay plumbing and do not need to be directly constructed or inspected by Prime or Compass:

- Internal step runners, retry logic, lane coordinators.
- Vendor/account adapter implementations. Adapters implement a protocol; callers depend on the protocol, not on the concrete adapter. Concrete adapters never belong in the core executor API surface — they belong in the account layer or an adapter registry outside `meridian_core`.
- Execution context builders and intermediate state objects (equivalent to `RelayDispatchLane` / `RelayDispatchPlan` — see `docs/relay-package-api-policy-note.md`).
- Any helper that takes `count_tokens`, `RelayRoute`, or other non-exported names as parameters.

---

## When Docs-Only Policy Should Wait for Implementation

This note was written before `relay_executor.py` exists. The provisional export list below is a planning artifact only. Build 2 must not add names to `meridian_core.__all__` based on this note alone. The correct sequence:

1. Build 1 lands `relay_executor.py` and its tests pass on `main`.
2. Build 2 reads the actual module, audits the public surface against the three conditions above.
3. Build 2 proposes root exports in a concrete task (updating `meridian_core/__init__.py` and `docs/package-api-surface-note.md`).
4. Codex reviews the export task before it merges.

---

## How Build 2 Should React When Build 1 Lands `relay_executor.py`

When `relay_executor.py` appears on `main`:

1. Read the module in full.
2. Check for any type that Prime/Compass would construct directly or inspect for decisions.
3. Apply the three conditions above to each candidate name.
4. Update this note with the concrete export decision.
5. Open an export task if names qualify; close this note as "resolved" if none do.

Do not batch executor exports with unrelated changes. One export decision per task.

---

## How Package Exports Interact with FileMap and Docs Discovery

Per `docs/package-api-surface-note.md`, root exports are for stable domain objects and primary builder/loader functions. When a name is added to `__all__`:

- Add it to the "Current Export Direction" table in `docs/package-api-surface-note.md`.
- Do not add it to `FileMap` unless it has its own module entry; `FileMap` tracks files, not individual names.
- If the name is a primary entry point (e.g. a top-level `execute_relay` function), a cross-reference in `docs/relay-package-api-policy-note.md` is appropriate.

---

## Why Vendor/Account Adapters Do Not Belong in the Core Executor API

`meridian_core` is the domain layer. Vendor and account adapters bind to external systems (API keys, account IDs, rate limits, provider-specific payload shapes). Mixing adapters into the core executor API:

- Creates coupling between the stable domain model and volatile external contracts.
- Forces `meridian_core` to carry provider-specific dependencies.
- Prevents the adapter layer from being swapped, mocked, or extended without touching core.

Adapters belong in a separate account or adapter layer that depends on `meridian_core`, not the reverse. The executor should accept an abstract adapter protocol; concrete adapters are injected or resolved outside the core package.

---

## Provisional Export List (not active — awaiting Build 1)

The following names are plausible candidates once `relay_executor.py` lands. They are listed here for orientation only and carry no implementation commitment:

```python
# Provisional — do NOT add to __all__ until relay_executor.py is reviewed
# from meridian_core import RelayExecutionResult   # if an execution result type exists
# from meridian_core import execute_relay           # if a top-level executor entry point exists
```

These names will be confirmed, renamed, or dropped after Build 1's module is audited. No export task should be opened from this note alone.
