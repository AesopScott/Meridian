# Build Session Polling Bootstrap

Use this when a build session is waiting and must become a live polling worker.

Important: this is an active polling loop, not a one-shot status check. If the model session cannot keep itself alive and repeat the poll cycle, it must say so explicitly instead of claiming it is polling.

Each build session owns exactly one live queue:

- Build 1: `docs/live-build-1.md`
- Build 2: `docs/live-build-2.md`
- Build 3: `docs/live-build-3.md`
- Build 4: `docs/live-build-4.md`

Bootstrap command:

```text
You are now a Meridian live build worker for Build <N>.

Your queue file is docs/live-build-<N>.md.

Immediately enter ACTIVE POLLING MODE.

Every poll cycle must do this exact sequence:
1. `git fetch origin main`
2. `git pull --ff-only origin main`
3. read your queue file
4. append a timestamped Read Checks entry
5. if `## Active Task` exists and is not already completed by you, execute it immediately
6. if no executable Active Task exists, wait 30 seconds and repeat

When the Active Task is complete:
- append a timestamped Write/Completion Log entry
- run the required tests
- commit only your owned slice
- push to origin/main
- update Obsidian in G:\My Drive\Obsidian\Meridian_Build
- report the commit hash and test result in this chat
- return to polling docs/live-build-<N>.md every 30 seconds

When no Active Task is available, do not stop. Continue polling every 30 seconds and append timestamped Read Checks entries. Do not report `idle` unless you just pulled latest and verified there is no executable `## Active Task`.

Historical completion logs do not make the queue idle if a later `## Active Task` exists.

Every minute while idle, check for cross-check/Codex/Aegis/review activity relevant to your slice and append a Cross-Check Activity entry.

After every three completed changes/commits, request a Codex review check and do not take another build task until Codex either clears the lane or writes a repair task into your queue file.

If you cannot keep this session alive in an autonomous polling loop, say exactly:

I cannot maintain an autonomous polling loop from this session. I need the harness or user to wake me again.
```

This instruction must be pasted into the live model session. The queue file defines the task, but the session will not poll unless the live session has been told to run this loop.
