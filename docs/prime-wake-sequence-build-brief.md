# Prime Wake Sequence Build Brief

## Purpose

Build the first concrete Meridian experience around Prime coming online.

This is not a full UI build yet. It is a small domain and CLI slice that proves the wake sequence can be generated from real portfolio and harness state.

## Product Intent

Meridian should feel less like a passive dashboard and more like a command system coming online.

The user enters through the UI Harness, but the primary relationship surface is the orchestrator session. Prime should greet the user, summarize system readiness, identify meaningful changes, and present bottlenecks or next moves.

Target feeling:

```text
Prime online.
Meridian has established position.
Beacon stable.
Echo loaded.
Relay standing by.
Good morning, Scott.

I reviewed the portfolio. Three initiatives are active, one worker is stalled, and two decisions need your judgment.
```

## Naming Context

Use these names as presentation names only. Do not overfit code identifiers if plain domain names are clearer.

- Prime: Orchestrator / Local Brain
- Bifrost: UI Harness
- Beacon: Heartbeat / Health Harness
- Echo: Memory Harness
- Atlas: Knowledge / RAG Harness
- Vault: Archive / Records Harness
- Forge: Tool Harness
- Aegis: Proof Harness
- Charter: Policy Harness
- Loom: Workflow Harness
- Compass: Portfolio / Objective Harness
- Relay: Agent / Model Harness
- Groot: Git / Worktree Harness, private/internal favorite
- Lens: Browser Harness
- Launch: Release Harness

## Build Scope

Add a small wake-sequence layer to the existing `meridian_core` skeleton.

Suggested files:

```text
meridian_core/wake.py
tests/test_wake.py
```

You may update `meridian_core/cli.py` to show the wake sequence before the current demo summary.

## Required Behavior

The wake sequence should:

- Accept the existing sample portfolio/harness state.
- Produce ordered wake lines from actual state, not hard-coded decoration only.
- Mark each important harness as one of: `online`, `stable`, `standing_by`, `degraded`, `blocked`, `offline`, or `unknown`.
- Include a concise portfolio orientation line.
- Include a concise bottleneck line when Scott/user judgment is required.
- Include a concise stalled/failed session line when harness state indicates a problem.
- Be deterministic in tests.

## Output Shape

Prefer native Python objects over JSON.

Suggested domain objects:

```python
WakeStatus
WakeLine
WakeBrief
```

A `WakeBrief` should contain:

- `title`
- `lines`
- `summary`
- `bottlenecks`
- `recommended_actions`

The CLI can render this as text, but the core should remain UI-independent.

## Important Constraint

Every cinematic line should map to a real check or known placeholder.

Good:

```text
Beacon stable.
```

Only if the heartbeat/health harness has usable liveness state.

Acceptable placeholder:

```text
Echo pending.
```

If the memory harness is not implemented yet but the system knows it is configured as a planned harness.

Avoid:

```text
All systems glorious and alive.
```

Unless the state actually proves that.

## Tests

Add focused tests for:

- Healthy wake sequence.
- Degraded/stalled harness appears in the brief.
- Bottlenecks appear when Scott/user judgment is required.
- Wake output order remains stable.

## Done Criteria

- `python -m pytest -q` passes.
- `python -m meridian_core.cli` prints a wake section followed by the existing local brain demo or an equivalent summary.
- No persistence, API adapters, Electron UI, or worker-session automation are introduced in this slice.
