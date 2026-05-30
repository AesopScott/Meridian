# Risk Tier Engine Build Brief

## Purpose

Build the first small Risk Tier Engine slice.

Risk tier is not just display metadata. In Meridian, changing risk tier changes the decision process: deterministic logic, single-lane cognition, dual-lane cognition, proof requirements, and human gates.

## Product Intent

Risk-tiered dual-lane cognition is Meridian's decision engine.

Prime should be able to explain:

```text
Risk Tier: 2
Mode: Dual-lane cognition
Reason: meaningful work instruction with file changes
Requirements: two candidate paths + Prime adjudication
Escalates if: tests fail, disagreement is high, release risk appears
```

This slice should make risk tier callable and inspectable as a domain object, not only inferred inside `ProgressIntention`.

## Scope

Keep this domain/CLI only.

Suggested files:

```text
meridian_core/risk.py
tests/test_risk.py
```

You may update:

```text
meridian_core/intention.py
meridian_core/objectives.py
meridian_core/cli.py
```

only if needed to reuse the risk engine.

## Required Behavior

Create native Python objects for:

```python
RiskAssessment
RiskRequirement
RiskTier
RiskMode
```

The risk engine should expose:

- tier number, 0-4
- mode label
- reason
- requirements
- escalation triggers
- whether dual-lane cognition is required
- whether Aegis proof is required
- whether Scott/human gate is required

## Initial Tier Semantics

Use these deterministic defaults:

- Tier 0: deterministic local logic only.
- Tier 1: one model lane allowed for low-risk reversible actions.
- Tier 2: dual-lane cognition for meaningful Prime decisions.
- Tier 3: dual-lane cognition plus Aegis proof for high-risk/completion/proof claims.
- Tier 4: human gate for irreversible, public, financial, destructive, account-risking, policy-sensitive, blocked, or strategic actions.

## Integration Guidance

Do not implement model routing yet.

This slice should make the future Relay decision easier by giving Prime a structured risk assessment that Relay can later use.

The existing `ProgressIntention` risk tier values should either reuse the new `RiskTier` enum or convert cleanly to a `RiskAssessment`.

## Tests

Add focused tests for:

- each tier maps to the correct mode and requirements
- Tier 2 requires dual-lane cognition
- Tier 3 requires dual-lane cognition and Aegis proof
- Tier 4 requires a human gate
- blocked actions assess as Tier 4
- risk assessment output is deterministic

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

Keep scope tight. No UI, persistence, model calls, or Relay routing implementation yet.
