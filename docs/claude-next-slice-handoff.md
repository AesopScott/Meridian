# Claude Next Slice Handoff

Please build the next Meridian slice and carry forward the open Codex review fix.

## Read First

- `context.md`
- `MISSION.md`
- `docs/meridian-capabilities.md`
- `docs/meridian-pillars.md`
- `docs/claude-handoff-completion-protocol.md`

## Carry-Forward Review Fix

Before starting the next new capability, resolve this Progress Intention review issue:

The previous handoff said:

```text
Human-gated or blocked items can produce Tier 4.
```

But the current implementation:

- defines `ObjectiveStage.BLOCKED`
- maps `BLOCKED` to `RiskTier.TIER_3`
- does not appear to derive `ObjectiveStage.BLOCKED`

Make blocked objective behavior explicit.

Options:

1. If blocked should require human gate in this slice, derive `ObjectiveStage.BLOCKED` where appropriate and map it to `RiskTier.TIER_4`.
2. If blocked should remain Tier 3, update the brief/tests/docs to remove the Tier 4 requirement and explain why.

Do not leave blocked behavior ambiguous. Add focused tests.

## Next Slice: Mission Objectives Recall

Build a small reusable mission-objectives recall layer so the future cockpit UI can call up current Compass-derived objectives at any time.

This should reuse the Progress Intention domain model rather than creating a separate competing model.

## Product Intent

The interface will have a persistent Mission Objectives / Compass control.

When invoked, it should show:

```text
Stage: Mission Boot > Compass Initiating

Mission Objectives:
  Project - Stage <Plan|Build|Review|Verify|Blocked|Gate> - Risk Tier <0-4>

Next Stage: Intention Engine Bootup
```

This view is not only wake output. It must be callable on demand.

## Scope

Keep this domain/CLI only.

Suggested files:

```text
meridian_core/objectives.py
tests/test_objectives.py
```

Or extend `meridian_core/intention.py` if that is cleaner. Prefer not to duplicate models.

You may update:

```text
meridian_core/cli.py
```

to expose a simple demo rendering.

## Required Behavior

- Provide a reusable function for generating the current mission objective view.
- Reuse or wrap `ProgressIntention`.
- Preserve current stage, initiating harness, objective lines, risk tiers, and next stage.
- Make the view suitable for a future UI button/control.
- Keep output deterministic.
- No model calls.
- No persistence.
- No UI implementation yet.

## Tests

Add or update tests proving:

- Mission objective view can be generated independently of wake rendering.
- It includes current stage and next stage.
- It includes objective lines with project, stage, and risk tier.
- Blocked behavior is explicit and covered.
- Output remains deterministic.

## Completion Protocol

Follow:

```text
docs/claude-handoff-completion-protocol.md
```

That means:

- Run `python -m pytest -q`.
- Commit only files for this slice/fix.
- Push to origin.
- Update the Meridian Obsidian build notes.

Keep scope tight.
