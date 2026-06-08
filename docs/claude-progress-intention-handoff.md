# Claude Progress Intention Handoff

Please build the next Meridian slice: Progress Intention.

Read first:

- `context.md`
- `MISSION.md`
- `docs/progress-intention-build-brief.md`

Scope:

- Add a small domain-first Progress Intention layer.
- Keep it deterministic and testable.
- Do not add UI, persistence, model calls, worker automation, or model routing yet.

Suggested files:

```text
meridian_core/intention.py
tests/test_intention.py
```

You may update:

```text
meridian_core/cli.py
```

only to print the progress intention after mission load and wake output.

Target output shape:

```text
Stage: Mission Boot > Compass Initiating

Mission Objectives:
  Meridian - Stage Build - Risk Tier 2
  CareGuide - Stage Review - Risk Tier 3
  Meetup Automation - Stage Plan - Risk Tier 4

Next Stage: Intention Engine Bootup
```

Required behavior:

- Create native Python objects for progress intention.
- Include current stage.
- Include initiating harness, currently `Compass`.
- Include mission objective lines.
- Include project/objective name.
- Include stage for each objective.
- Include risk tier for each objective.
- Include next stage.
- Use simple deterministic risk-tier logic for now.
- Make the output reusable by a future UI button/control that calls up mission objectives at any time.

Tests:

- Progress intention has current stage, initiating harness, and next stage.
- Objective lines are deterministic.
- Each objective line has a stage.
- Each objective line has a risk tier.
- Human-gated or blocked items can produce Tier 4.
- CLI/demo can render the intention without model calls.

Run:

```text
python -m pytest -q
```

Completion protocol:

1. Confirm `python -m pytest -q` passes.
2. Commit the finished slice to git with a clear message, for example:

```text
git add meridian_core/intention.py tests/test_intention.py meridian_core/cli.py
git commit -m "feat: add progress intention slice"
```

3. Push the commit to origin:

```text
git push origin main
```

4. Update the Meridian Obsidian build notes with:

- what changed
- tests run
- commit hash
- any follow-up needed

Obsidian build folder:

```text
G:\My Drive\Obsidian\Meridian_Build
```

If the working tree contains unrelated uncommitted files, do not include them in the commit. Commit only the files for this slice.

Keep the slice tight.
