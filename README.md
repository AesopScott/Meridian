# Meridian

Meridian is a local orchestrator for agentic software work.

You talk to the orchestrator. The orchestrator drives worker sessions, harnesses, proof, and project motion.

## Actual UI

The actual Meridian user interface is `index.html` at the repository root.

This is the working cockpit UI: harness dock, Prime panel, user/session panel, Spark center, right-panel modes, model harness views, and local bridge wiring. Electron wraps this same file through `electron/main.js`. `npm start` opens `index.html`; it must not regenerate or substitute `bifrost/preview.html`.

`bifrost/preview.html` is a generated backend/render proof artifact created by `bifrost/preview.py`. It is not the product UI entrypoint.

## What It Is

Meridian is a proactive portfolio orchestrator and builder. It advances projects, businesses, websites, tools, and experiments until Scott's judgment is the bottleneck — not execution.

The intended model:

```
Scott → Orchestrator
Orchestrator → Workers
Workers → Harnesses
Harnesses → Heartbeat / Events
Orchestrator → Scott only for judgment bottlenecks
```

## Current State

Meridian now has a working local cockpit UI in `index.html`, an Electron wrapper, and a local model bridge in `scripts/meridian-model-bridge.js`. The Python core continues to provide deterministic backend/runtime logic for the visible harness surfaces.

### Package: `meridian_core`

```
meridian_core/
  models.py         — domain objects: Portfolio, Venture, Initiative, Objective,
                      NextMove, Harness, Heartbeat, Decision, ScottBottleneck,
                      SessionInjection, ProviderAdapter, and supporting types
  sample_state.py   — sample portfolio (Meridian, Advanced AI Concepts, CareGuide),
                      heartbeats, and provider adapters
  decisions.py      — deterministic kernel decision loop
  events.py         — in-memory event recorder
  injections.py     — SessionInjection factory
```

### What the skeleton proves

- Portfolio state → harness heartbeat → kernel decision → session injection → Scott bottleneck queue
- Blocked harnesses with known blockers produce targeted directive injections
- Scott-required next moves become bottlenecks and are never auto-advanced
- Autonomous moves with unverified proof produce verification injections
- Provider adapters carry compliance tier metadata (public-safe vs. private/disabled)

## Install and run tests

Requires Python 3.12+.

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Not built yet

- Real Claude / Codex / OpenRouter model integrations
- Public model setup flow: Scott's local Max/Claude and Codex CLI logins are already configured for this development machine, but a public Meridian build must not assume that. If a selected model CLI is missing or not authenticated, Meridian should tell the user to install the relevant CLI and log in to their account instead of showing raw process errors.
- Model routing intent: each project's Prime/orchestrator should normally choose the model automatically through Relay harness logic. Manual model selection may be exposed for direct use and testing, but the expected operating mode is automated Prime/Relay decision-making.
- Real session injection (modeled only)
- SQLite or other persistence
- Git / worktree harness
- Browser automation
- Full workflow engine
- Public packaging

## Primary docs

- [`context.md`](context.md) — shared vocabulary and canonical project anchors
- [`docs/meridian-v0-build-brief.md`](docs/meridian-v0-build-brief.md) — V0 target and first build slice
- [`docs/polaris-lessons-for-meridian.md`](docs/polaris-lessons-for-meridian.md) — what Polaris proved and what Meridian carries forward
- [`docs/polaris-ui-lessons-for-meridian.md`](docs/polaris-ui-lessons-for-meridian.md) — UI carry-forward notes
- [`docs/meridian-provider-compliance.md`](docs/meridian-provider-compliance.md) — provider adapter compliance strategy
