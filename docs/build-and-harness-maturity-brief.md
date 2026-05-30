# Build And Harness Maturity Brief

## Purpose

Add a first-class way to track Meridian build identity and per-harness maturity.

Meridian needs both:

- an overall build number
- per-harness build numbers
- per-harness maturity states

Build number is not the same thing as maturity.

## Product Intent

Prime should eventually be able to report:

```text
Meridian Build: 0001

Bifrost: build 0000, maturity Concept
Beacon: build 0000, maturity Concept
Echo: build 0000, maturity Concept
Compass: build 0002, maturity Prototype
Relay: build 0000, maturity Concept
Aegis: build 0000, maturity Concept
```

This lets Scott and Prime see which parts of Meridian are merely named, which parts are skeletal, which parts work in demos, and which parts are trusted operationally.

## Definitions

Overall build number answers:

```text
Which generation of Meridian as a system is this?
```

Harness build number answers:

```text
Which implementation generation of this harness is currently present?
```

Harness maturity answers:

```text
How trustworthy, complete, proven, and operational is this harness?
```

## Suggested Maturity States

- Concept: named and defined, not implemented.
- Skeleton: domain shape exists, limited behavior.
- Prototype: works in controlled demo/sample state.
- Operational: useful in real workflow with tests/proof.
- Hardened: resilient, observable, recoverable, and trusted.
- Deprecated: retained for compatibility but no longer preferred.

## Future Uses

This metadata should eventually influence:

- Prime wake/system view
- Compass mission objectives
- risk tier selection
- Relay routing confidence
- Aegis proof gates
- release readiness
- public/private capability disclosure

## Scope For First Slice

Domain-only.

Suggested files:

```text
meridian_core/builds.py
tests/test_builds.py
```

Suggested objects:

```python
MeridianBuild
HarnessBuild
HarnessMaturity
BuildRegistry
```

No persistence yet unless explicitly requested.

Use deterministic in-memory sample data first.

## Tests

Add tests for:

- Meridian build number exists.
- Each known harness can have build number and maturity.
- Build number and maturity are separate fields.
- Maturity ordering/comparison is deterministic if implemented.
- Unknown harness metadata fails clearly or returns an explicit unknown state.

## Completion Protocol

Follow:

```text
docs/claude-handoff-completion-protocol.md
```
