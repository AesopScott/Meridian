# V2 Continuation Handoff - 2026-06-07

This file is the coordinator handoff for Main. It records the current
conflict-free backend build state after the June 7 continuation pass.

## Authority

- Main coordinates all worker and review activity and keeps `main`
  conflict-free.
- Implementation workers must run through Polaris Opus sessions
  (`launch-chat`, tier `power`, `anthropic/claude-opus-4-7`).
- Code review sessions must run in Codex.
- Workers must use unique detached worktrees and must not write shared main,
  commit, push, merge, rebase, reset, cherry-pick, move branches/worktrees, or
  copy files across worktrees.
- Main may promote reviewed worker output only after `main` is clean, Codex
  review passes, and Main proof passes.
- The Electron app is the Meridian UI. Root `index.html` is the current
  renderer source loaded by Electron; it is not a separate UI product target.
  `bifrost/preview.html` is generated backend/view-model proof output only.

## Current Promoted Backend State

- `96c0b1956` - `goal-runtime: add v3 domain slice`
- `1b2847baa` - `filemap: register goal runtime slice`
- `83fbcf777` - `provider-balance: add v3 domain slice`
- `75edb31c5` - `filemap: register v3 intake and goal runtime`
- `28002a9b7` - `workflow: add dispatch domain slice`
- `c1c803fba` - `filemap: register workflow dispatch slice`

Workflow Dispatch implementation was built by Polaris Build 1 Opus worker
`chat_1780869321133` in:

`C:/Users/scott/AppData/Local/Temp/polaris-wt/build1-workflow-dispatch-20260607-1620`

Workflow Dispatch FileMap registration was built by Polaris Build 3 Opus worker
`chat_1780871322289` in:

`C:/Users/scott/AppData/Local/Temp/polaris-wt/build3-workflow-dispatch-filemap-20260607-1715`

Both implementation and FileMap registration passed Codex Review A and Codex
Review B before promotion.

## Main Proof

After promoting the Workflow Dispatch FileMap registration to Main:

- `python -m pytest tests/test_filemap.py tests/test_workflow_dispatch.py -q`
  -> 208 passed.
- `git diff --check -- meridian_core/filemap.py docs/FileMap.md
  tests/test_filemap.py docs/live-build-3.md` -> clean.
- `git status --short --branch` -> `## main...origin/main` after push.

## Next Backend Direction

The Workflow Dispatch domain slice is pure and local. Remaining workflow work
belongs in separate coordinator-promoted tasks:

- per-harness workflow handlers and typed output records for Echo, Atlas,
  Aegis, Relay, Bifrost, Beacon, and Session Lifecycle;
- real PromptBudgetPlan / CognitionPolicy integration beyond local value
  carriers;
- Session Lifecycle timeout/restart/resteer operation surfaces without raw
  transcript leakage;
- Bifrost display-only workflow status rendering, with Electron UI authority
  preserved.

Before assigning the next task, Main should verify `git status --short
--branch` is clean and write the task into the appropriate live-build queue
top block. Use Opus workers for implementation and Codex Review A/B for review.
