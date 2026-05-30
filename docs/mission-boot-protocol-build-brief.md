# Mission Boot Protocol Build Brief

## Purpose

Build the first `MISSION.md` boot protocol slice for Prime.

Prime should not wake and act from ambient assumptions. Prime's first authority is the mission file.

## Product Intent

Meridian is governed by logic, not brittle rule piles.

`MISSION.md` should be a readable launch protocol that tells Prime what to follow before it acts:

- Immutable Prime Directives.
- Harness boot/check order.
- Current mission objective.
- Risk/gating defaults.
- What belongs in the orchestrator queue versus the non-orchestrator queue.

## Scope

Keep this small and testable.

Suggested files:

```text
MISSION.md
meridian_core/mission.py
tests/test_mission.py
```

You may update:

```text
meridian_core/cli.py
meridian_core/wake.py
```

only if needed to show that Prime loads the mission before rendering wake output.

## Required Behavior

Add a native Python mission layer that can:

- Locate a `MISSION.md` file from the repository root.
- Parse a small, explicit structure from it.
- Return a `Mission` object.
- Expose immutable directives.
- Expose harness boot order.
- Expose the current mission objective.
- Expose queue display guidance.
- Fail clearly if the mission file is missing required sections.

Prefer native Python objects over JSON.

Suggested objects:

```python
Mission
PrimeDirective
MissionLoadError
QueueDisplayGuidance
```

## Initial MISSION.md Content

The first mission file should include these ideas in plain Markdown:

```markdown
# Meridian Mission

## Prime Directives

1. Logic, not rules.
2. Prime reads this mission file before meaningful action.
3. Prime states progress intention before meaningful work.
4. Prime uses risk-tiered dual-lane cognition when risk requires it.
5. Prime does not take irreversible, public, financial, destructive, account-risking, or policy-sensitive actions without the required gate.

## Harness Boot Order

1. Bifrost
2. Beacon
3. Echo
4. Atlas
5. Vault
6. Forge
7. Aegis
8. Charter
9. Loom
10. Compass
11. Relay
12. Groot
13. Lens
14. Launch

## Current Mission Objective

Advance Meridian by building Prime's boot, wake, progress intention, and queue architecture in small reviewed slices.

## Queue Display Guidance

Orchestrator Queue:
Prime's conversational messages, progress intentions, judgment requests, and outcomes.

Non-Orchestrator Queue:
System messages, NASA-style Go calls, harness health, proof status, worker/session state, artifacts, review gates, and instrumentation Prime wants visible.

These queues may be tabs of the same main cockpit screen rather than two simultaneous panels.

The non-orchestrator queue is also a prompt window. It should preserve the ability for Scott to respond directly to the artifact, plan, proof, comparison, or gate Prime is presenting.
```

## Wake / Queue Display Rule

The NASA-style wake sequence belongs in the non-orchestrator window if shown as text:

```text
Bifrost Go.
Beacon Go.
Echo Go.
Relay Go.
```

It may also be rendered as audio-first system instrumentation: each spoken "Go" call lights the matching cockpit indicator.

Prime's conversational message belongs in the orchestrator queue:

```text
Good morning, Scott.
Allow me to check today's mission file.
My progress intention is...
```

This build does not need to create the UI. It only needs to preserve this split in domain objects/output shape so the future UI can render it correctly.

## Tests

Add focused tests for:

- Successful mission load from `MISSION.md`.
- Required sections are present.
- Prime Directives are parsed in order.
- Harness boot order is parsed in order.
- Queue display guidance preserves orchestrator versus non-orchestrator distinction.
- Missing required section raises `MissionLoadError`.

## Done Criteria

- `python -m pytest -q` passes.
- CLI or demo output proves the mission file loads before wake output.
- No persistence, API adapters, worker automation, Electron UI, or model routing implementation is introduced in this slice.
