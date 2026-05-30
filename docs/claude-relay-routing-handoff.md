# Claude Relay Routing Handoff

Please build the next Meridian slice: Relay Routing.

Read first:

- `context.md`
- `MISSION.md`
- `docs/meridian-capabilities.md`
- `docs/meridian-pillars.md`
- `docs/risk-tier-engine-build-brief.md`
- `docs/relay-routing-build-brief.md`
- `docs/claude-handoff-completion-protocol.md`

Goal:

Make Relay able to produce a deterministic model/session routing plan from risk tier and task context, without calling real models.

Build:

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

Required objects:

```text
RelayRoute
RelayLane
RoutingMode
ContextStrategy
ModelRole
```

Required behavior:

- Tier 0 produces no model lanes.
- Tier 1 produces one fast/cheap lane.
- Tier 2 produces two lanes for dual-lane cognition.
- Tier 3 produces two lanes plus proof/review posture.
- Tier 4 requires human gate before execution.
- Focused packet is the default context strategy.
- Route includes reason, cost posture, and independence requirement.
- Output is deterministic.

Do not add UI, persistence, model calls, provider adapters, credentials, account automation, or worker automation yet.

Completion:

- Run `python -m pytest -q`.
- Commit only files for this slice.
- Push to origin.
- Update the Meridian Obsidian build notes.

Keep scope tight.
