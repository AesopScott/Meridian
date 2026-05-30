# Relay Routing Build Brief

## Purpose

Build the first small Relay Routing slice.

Relay is the Agent / Model Harness. Prime should not choose models by habit or static preference alone. Prime should choose a model/session strategy from risk tier, task type, context pressure, cost, latency, independence needs, modality, tool access, and user defaults.

## Product Intent

Risk tier changes the decision process. Relay routing turns that decision process into a model/session plan.

Example:

```text
Risk Tier: 2
Routing Mode: dual-lane
Builder Lane: selected default model
Reviewer Lane: independent reviewer model
Context Strategy: focused packet
Reason: meaningful build work with file changes
```

This slice should make routing inspectable and testable without calling real models.

## Scope

Keep this domain-only.

Suggested files:

```text
meridian_core/relay.py
tests/test_relay.py
```

You may update:

```text
meridian_core/risk.py
meridian_core/cli.py
```

only if useful for integration/demo output.

## Required Behavior

Create native Python objects for:

```python
RelayRoute
RelayLane
RoutingMode
ContextStrategy
ModelRole
```

The routing layer should expose:

- routing mode
- lane list
- role for each lane
- preferred model/provider label, if known
- context strategy
- reason
- cost posture
- independence requirement
- whether human gate is required before execution

## Initial Routing Semantics

Use deterministic defaults:

- Tier 0: no model lanes; deterministic local logic.
- Tier 1: one fast/cheap lane.
- Tier 2: two lanes for dual-lane cognition.
- Tier 3: two lanes plus proof/review posture.
- Tier 4: no autonomous execution until human gate; may prepare an explanation or plan packet.

Context strategy:

- `focused_packet`: default for most tasks.
- `reuse_session`: when continuity matters and context is still healthy.
- `summarize_and_reset`: when context is bloated or polluted.
- `large_context`: only when task truly benefits from a large window.

Do not implement real model calls, APIs, provider credentials, or account automation.

## Tests

Add focused tests for:

- Tier 0 produces no model lanes.
- Tier 1 produces one lane.
- Tier 2 produces two independent lanes.
- Tier 3 includes proof/review posture.
- Tier 4 requires human gate before execution.
- focused packet is the default context strategy.
- output is deterministic.

## Completion Protocol

Follow:

```text
docs/claude-handoff-completion-protocol.md
```

That means:

- Run `python -m pytest -q`.
- Commit only files for this slice.
- Push to origin.
- Update the Meridian Obsidian build notes.

Keep scope tight. No UI, persistence, model calls, provider adapters, or worker automation yet.
