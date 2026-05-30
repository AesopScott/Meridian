# Claude Progress Intention Review Fix

Please make one focused correction to the Progress Intention slice.

## Issue

The handoff says:

```text
Human-gated or blocked items can produce Tier 4.
```

But the current implementation:

- defines `ObjectiveStage.BLOCKED`
- maps `BLOCKED` to `RiskTier.TIER_3`
- never appears to derive `ObjectiveStage.BLOCKED`

That makes the blocked-stage behavior unclear and leaves the test requirement undercovered.

## Required Fix

1. Decide the deterministic signal for blocked objective state using the existing domain objects.
   - Prefer using existing `DecisionResult`, bottlenecks, injections, next moves, or heartbeat-derived data if available.
   - Keep scope tight. Do not add model calls or persistence.
2. Make blocked objective behavior explicit.
3. Add tests proving blocked items can be represented and assigned the expected risk tier.
4. If blocked means human gate in this slice, map it to Tier 4.
5. If blocked should remain Tier 3, update the build brief/tests to remove the Tier 4 requirement and explain why. Do not leave it ambiguous.
6. Run:

```text
python -m pytest -q
```

## Completion Protocol

After tests pass:

1. Commit only the files for this fix.
2. Push to origin.
3. Update the Meridian Obsidian build notes.

Use:

```text
docs/claude-handoff-completion-protocol.md
```

Keep this as a small review fix only.
