# Progress Intention Build Brief

## Purpose

Build the first Progress Intention slice for Prime.

Now that Prime can load `MISSION.md` and render the wake sequence, Prime should be able to state what stage it is entering, which mission objectives are active, what stage each objective is in, and what risk tier applies.

## Product Intent

The progress intention is not a loading transcript.

It is Prime saying what work is about to move.

The interface should also expose a persistent control/button to call up this mission objective view at any time.

Target shape:

```text
Stage: Mission Boot > Compass Initiating

Mission Objectives:
<Meridian - Stage Build - Risk Tier 2>
<CareGuide - Stage Review - Risk Tier 3>
<Meetup Automation - Stage Plan - Risk Tier 4>

Next Stage: Intention Engine Bootup
```

## Scope

Keep this small and domain-first.

Suggested files:

```text
meridian_core/intention.py
tests/test_intention.py
```

You may update `meridian_core/cli.py` to print the progress intention after the wake sequence.

## Required Behavior

Add native Python objects for:

```python
ProgressIntention
MissionObjectiveLine
ObjectiveStage
RiskTier
```

The first implementation may derive mission objective lines from the existing sample portfolio and decision result.

It should include:

- Current stage label, e.g. `Mission Boot`.
- Initiating harness label, e.g. `Compass`.
- Mission objective lines.
- Project/objective name.
- Stage for each objective, e.g. `Plan`, `Build`, `Review`, `Verify`, `Blocked`, `Gate`.
- Risk tier for each objective, at least tiers 0-4.
- Next stage label, e.g. `Intention Engine Bootup`.

## Risk Tier Guidance

Use simple deterministic logic for this slice.

Example:

- Tier 0: deterministic observation only.
- Tier 1: low-risk reversible work.
- Tier 2: meaningful build or coordination work.
- Tier 3: proof, completion, review, release preparation, or memory-writing work.
- Tier 4: human-gated, irreversible, public, financial, destructive, account-risking, or policy-sensitive work.

Do not implement model calls or dual-lane cognition yet. Represent the selected tier and reason in the domain object if useful.

## CLI Shape

After wake output, print something like:

```text
Stage: Mission Boot > Compass Initiating

Mission Objectives:
  Meridian - Stage Build - Risk Tier 2
  CareGuide - Stage Review - Risk Tier 3

Next Stage: Intention Engine Bootup
```

## Future UI Control

The future cockpit UI should include a mission/objectives control that can summon this same view on demand:

```text
Mission Objectives
Project | Stage | Risk Tier | Next Stage
```

This build does not need to implement the UI button, but the domain object should be reusable by that future control.

## Tests

Add focused tests for:

- Progress intention has current stage, initiating harness, and next stage.
- Objective lines are deterministic.
- Each objective line has a stage.
- Each objective line has a risk tier.
- Human-gated or blocked items can produce Tier 4.
- CLI/demo can render the intention without model calls.

## Done Criteria

- `python -m pytest -q` passes.
- CLI prints the progress intention after mission load/wake output.
- No UI, persistence, API adapters, model routing, or worker automation in this slice.
- Commit the slice to git, push to origin, and update the Meridian Obsidian build notes unless Scott explicitly says this is local-only.

Use the completion protocol in:

```text
docs/claude-handoff-completion-protocol.md
```
