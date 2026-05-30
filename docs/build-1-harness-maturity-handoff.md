# Build 1 Handoff: Harness Build And Maturity

Build 1, please build the Harness Build And Maturity slice.

## Read First

- `context.md`
- `docs/build-and-harness-maturity-brief.md`
- `docs/claude-handoff-completion-protocol.md`

## Scope

Allowed files:

```text
meridian_core/builds.py
tests/test_builds.py
```

You may update `meridian_core/cli.py` only if you add a tiny demo output, but prefer domain/tests only.

Do not edit Relay, Risk, Mission, Wake, Intention, Objectives, or UI files in this slice.

## Goal

Add a first-class way to track:

- Meridian overall build number
- per-harness build number
- per-harness maturity state

Build number and maturity are separate fields.

## Suggested Objects

```text
MeridianBuild
HarnessBuild
HarnessMaturity
BuildRegistry
```

## Maturity States

Use:

```text
Concept
Skeleton
Prototype
Operational
Hardened
Deprecated
```

## Required Behavior

- Meridian build number exists.
- Known harnesses can have build number and maturity.
- Build number and maturity are independent.
- Unknown harness lookup fails clearly or returns explicit unknown metadata.
- Deterministic sample registry exists for current known harnesses.

Known harness labels:

```text
Bifrost
Beacon
Echo
Atlas
Vault
Forge
Aegis
Charter
Loom
Compass
Relay
Groot
Lens
Launch
```

## Tests

Add focused tests for:

- overall build number
- per-harness build number
- per-harness maturity
- maturity ordering/comparison if implemented
- unknown harness behavior
- deterministic registry output

## Completion

Follow `docs/claude-handoff-completion-protocol.md`:

- Run `python -m pytest -q`.
- Commit only files for Build 1.
- Push to origin.
- Update Meridian Obsidian build notes.

Keep scope tight.
