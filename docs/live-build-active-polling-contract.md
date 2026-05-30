# Live Build Active Polling Contract

This contract exists because a live build queue is only useful if the worker session actively pulls, reads, acts, and returns to polling.

Markdown queues are coordination files. They do not make a model autonomous by themselves. A worker session must stay in an active polling loop or the session harness must drive that loop externally.

## Non-Negotiable Worker Behavior

When a build session is assigned a live queue, it must:

- Pull latest `origin/main` before every queue read.
- Read only its assigned queue file.
- Treat `## Active Task` as authoritative when present.
- Execute the active task immediately if it has not completed it.
- Never report `idle` unless it has just pulled latest and confirmed there is no executable active task.
- After completing a task, commit, push, update Obsidian, report the commit, then return to polling.
- While waiting, keep the session alive and check every 30 seconds.

## Required Poll Cycle

Every poll cycle must do this exact sequence:

```text
1. git fetch origin main
2. git pull --ff-only origin main
3. read docs/live-build-N.md
4. append a timestamped Read Checks entry
5. if Active Task exists and is not completed by this session, execute it
6. if no executable Active Task exists, wait 30 seconds and repeat
```

If the model cannot keep itself alive for repeated polling, it must say so explicitly:

```text
I cannot maintain an autonomous polling loop from this session. I need the harness or user to wake me again.
```

## Idle Definition

`idle` means:

- the session pulled latest successfully
- the session read the current queue file
- there is no active task assigned to that lane
- there is no review-required task assigned to that lane
- there is no repair task assigned to that lane

Historical completion logs do not make the queue idle if a later `## Active Task` exists.

## Harness Requirement

Meridian must not rely on model self-discipline for this long term. The Session Harness needs a real polling driver that can:

- wake a worker session
- pull latest
- extract the current active task
- send only the active task to the worker model
- detect completion
- route completion to Codex/Prime for review
- write the next task only after review clears

Until that harness exists, the live build sessions must be pasted the strict active polling command.
