# Live Build 1 Queue

This file is the standing assignment queue for Build 1.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- Always pull latest `origin/main` before editing.
- Every time you check/read this file, add a timestamped entry to the Read Checks section.
- Every time you modify this file or complete a task from it, add a timestamped entry to the Write/Completion Log section.
- Every minute while idle, check for cross-check activity relevant to your slice: review notes, Codex findings, Aegis findings, failing tests, or Obsidian build log updates.
- If cross-check activity affects your task, record it in this file's Cross-Check Activity section and address it before starting unrelated work.
- Use local time with timezone when possible.
- Own only the files listed in the active task.
- Do not edit Build 2 or Build 3 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Build 1 checked queue; status: idle/running/blocked
2026-05-30 ~22:30 CDT - Build 1 checked queue; status: running (active task found)
```

## Write/Completion Log

Append entries here when this file is modified or an active task is completed.

```text
YYYY-MM-DD HH:MM TZ - Build 1 completed <task>; commit <hash>; tests <result>
2026-05-30 ~22:30 CDT - Build 1 completed Prompt Budget package API + FileMap; commit d18d651; tests 604 passed
```

## Cross-Check Activity

Append entries here when you check or act on cross-check activity.

```text
YYYY-MM-DD HH:MM TZ - Build 1 cross-check: none/finding/fix; details: <short note>
```

## Active Task

Goal: finish Prompt Budget package API and FileMap exposure.

Important review finding:

`docs/FileMap.md` currently appears to have a duplicate `meridian_core/prompt_budget.py` row because Build 3's integration brief already added a prompt budget row.

Allowed files only:

- `meridian_core/__init__.py`
- `tests/test_package_api.py`
- `meridian_core/filemap.py`
- `tests/test_filemap.py`
- `docs/FileMap.md`

Task:

- Keep exactly one `meridian_core/prompt_budget.py` row in `docs/FileMap.md`.
- Preserve the useful details:
  - deterministic prompt token budget per risk tier
  - prevents Relay prompt drag
  - bounded context sources and token limits
  - related test: `tests/test_prompt_budget.py`
  - note future RelayRoute integration / integration brief if useful
- Export these stable Prompt Budget names from package root:
  - `PromptBudgetTier`
  - `PromptBudget`
  - `PromptBudgetPlan`
  - `prompt_budget_for_risk_tier`
- Add package API import smoke coverage.
- Add FileMap required-path coverage.

Tests:

```text
python -m pytest -q
```

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.
