# Relay Executor — Package API Policy Note

**Status:** Resolved — `relay_executor.py` has landed; concrete export decision below
**Decision owner:** Build 2 (Codex cadence repair, 2026-05-31)
**Reference:** `docs/package-api-surface-note.md`, `docs/relay-package-api-policy-note.md`

---

## Summary

`meridian_core/relay_executor.py` has landed and defines the execution boundary for a `RelayDispatchPlan`. This note documents the concrete export decision for names in that module.

---

## What `relay_executor.py` Defines

The module defines five names:

| Name | Kind | Description |
|------|------|-------------|
| `ModelCallFn` | Protocol | Callable boundary: receives only a payload string, returns text |
| `RelayExecutionResult` | frozen dataclass | Successful per-lane output (role, preferred_model, output) |
| `RelayExecutionError` | frozen dataclass | Captured per-lane exception (role, preferred_model, error) |
| `RelayExecutionSummary` | frozen dataclass | Immutable collection of results + errors from one plan execution |
| `execute_relay_dispatch_plan` | function | Execute every lane in a plan via an injected model-call callable |

---

## Root Export Decision

Applying the three conditions (external caller need, stable domain shape, no undocumented internal dependencies):

### Names that qualify for `from meridian_core import ...`

**`RelayExecutionResult`** — qualifies.
- Prime/Compass inspects per-lane output directly.
- Stable frozen dataclass; no unexported dependencies.
- Add to `__all__` and `docs/package-api-surface-note.md`.

**`RelayExecutionSummary`** — qualifies.
- Prime/Compass receives this as the outcome of a plan execution.
- Stable frozen dataclass holding tuples of `RelayExecutionResult` and `RelayExecutionError`.
- Add to `__all__` and `docs/package-api-surface-note.md`.

**`RelayExecutionError`** — qualifies (companion to `RelayExecutionSummary`).
- Callers inspecting `summary.errors` need the type to pattern-match.
- Stable frozen dataclass; no unexported dependencies.
- Add to `__all__` and `docs/package-api-surface-note.md`.

### Names that should remain module-local

**`execute_relay_dispatch_plan`** — stays internal for now.
- Depends on `RelayDispatchPlan` (not yet a root export) and `ModelCallFn` (adapter protocol, never a root export).
- Exporting the entry point before its parameter type is exported would force callers to import from two levels.
- Revisit when `RelayDispatchPlan` is evaluated for root export.

**`ModelCallFn`** — stays internal.
- Adapter protocol; callers depend on the protocol through `execute_relay_dispatch_plan`, not by constructing it directly.
- Concrete adapter implementations never belong in the core executor API.

---

## How Package Exports Interact with FileMap and Docs Discovery

Per `docs/package-api-surface-note.md`, when names are added to `__all__`:
- Add each name to the "Current Export Direction" table in `docs/package-api-surface-note.md`.
- Do not add to `FileMap` unless a name has its own module entry; `FileMap` tracks files, not individual names.
- Cross-reference in `docs/relay-package-api-policy-note.md` if the name is a primary Relay entry point.

---

## Why Vendor/Account Adapters Do Not Belong in the Core Executor API

`meridian_core` is the domain layer. Vendor and account adapters bind to external systems (API keys, account IDs, rate limits, provider-specific payload shapes). Mixing adapters into the core executor API:

- Creates coupling between the stable domain model and volatile external contracts.
- Forces `meridian_core` to carry provider-specific dependencies.
- Prevents the adapter layer from being swapped, mocked, or extended without touching core.

Adapters belong in a separate account or adapter layer that depends on `meridian_core`, not the reverse. The executor accepts `ModelCallFn` — a pure protocol; concrete implementations are injected outside the core package.

---

## Next Step

Open an export task to add `RelayExecutionResult`, `RelayExecutionSummary`, and `RelayExecutionError` to `meridian_core/__init__.py` and `docs/package-api-surface-note.md`. Codex should review that task before it merges. Do not batch with unrelated changes.
