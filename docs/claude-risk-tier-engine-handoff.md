# Claude Risk Tier Engine Handoff

Please build the next Meridian slice: Risk Tier Engine.

Read first:

- `context.md`
- `MISSION.md`
- `docs/meridian-capabilities.md`
- `docs/meridian-pillars.md`
- `docs/risk-tier-engine-build-brief.md`
- `docs/claude-handoff-completion-protocol.md`

Goal:

Make risk tier a first-class domain engine, not just a display field on mission objectives.

Build:

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

only if needed to reuse the new risk engine cleanly.

Required behavior:

- Native Python objects for risk assessment.
- Tier number 0-4.
- Mode label.
- Reason.
- Requirements.
- Escalation triggers.
- `requires_dual_lane`.
- `requires_aegis_proof`.
- `requires_human_gate`.
- Deterministic tier semantics.

Initial semantics:

- Tier 0: deterministic local logic only.
- Tier 1: one model lane allowed for low-risk reversible actions.
- Tier 2: dual-lane cognition for meaningful Prime decisions.
- Tier 3: dual-lane cognition plus Aegis proof.
- Tier 4: human gate for irreversible, public, financial, destructive, account-risking, policy-sensitive, blocked, or strategic actions.

Tests:

- each tier maps to the correct mode and requirements
- Tier 2 requires dual-lane cognition
- Tier 3 requires dual-lane cognition and Aegis proof
- Tier 4 requires human gate
- blocked actions assess as Tier 4
- output is deterministic

Do not add UI, persistence, model calls, or Relay routing implementation yet.

Completion:

- Run `python -m pytest -q`.
- Commit only files for this slice.
- Push to origin.
- Update the Meridian Obsidian build notes.

Keep scope tight.
