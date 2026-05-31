# Session Card Queue Activation Contract

## Purpose

Meridian must inherit the useful part of Polaris Q mode without inheriting the manual supervision tax. Queue activation belongs to Prime and the Session Lifecycle Harness. Bifrost renders the control and state; it does not decide what work a session should do.

## Owner

- Product surface: Bifrost Harness
- Runtime owner: Session Lifecycle Harness
- Orchestrator: Prime
- Safety gate: Aegis for high-risk command plans

## Q Mode Contract

When Q mode is enabled for a session card, the session must poll only its assigned queue.

Required identity fields:

- project name
- session name
- harness role
- assigned queue file
- worktree path
- branch name
- model provider
- model name
- current status
- last queue read timestamp
- last queue write timestamp

## Routing Rules

- Build sessions read build queues only.
- Review sessions read review queues only.
- UI sessions read UI/build queues only when assigned by Prime.
- A session may inspect another queue as evidence only when its task says so.
- Wrong-queue polling is a degraded state and should trigger Prime resteer.

## Idle Does Not Mean Done

An idle Q-enabled session must continue polling. It should surface:

- no active task
- stale active task
- completed active task not cleared
- cadence/review gate
- blocked provider/model state
- failed pull or push
- shared worktree violation

The session should not require Scott to nudge it just because its visible prompt is quiet.

## No Read-Check Commit Spam

Read-check-only commits are not work. Polling state should be recorded in Session Lifecycle state and displayed in Bifrost.

Acceptable status fields:

- last read
- last write
- last proof
- last command plan
- current blocker

Do not create repeated main-branch commits that only say "still idle."

## Bifrost Display Fields

Each session card should display:

- project
- role
- model/provider
- assigned queue
- active task
- next candidate
- last read/write
- cadence count
- review gate state
- proof state
- blocker summary
- worktree uniqueness status

Collapsed cards should be quiet. Expanded cards can show proof and queue detail.

## Prime Controls

Prime may propose or execute, subject to permission:

- force poll
- pause polling
- resume polling
- reassign queue
- archive
- restart
- resteer
- request human gate

Branch movement and worktree changes require Scott or Prime permission and must be represented as typed `SessionCommandPlan` objects.

## Degraded States

Bifrost must make these visible:

- wrong assigned queue
- stale active task
- no next candidate
- shared worktree
- main worktree violation
- provider limit
- model capacity limit
- failed pull
- failed push
- review gate blocked
- lost heartbeat
- prompt payload growth during Q mode

Prime should route repair or resteer actions before asking Scott unless a human gate is required.

## Out Of Scope

- implementing live session automation
- changing Polaris
- changing Electron packaging
- running vendor account automation
- granting branch movement automatically

This contract defines the product/runtime behavior for Meridian. Implementation belongs in later Session Lifecycle and Bifrost slices.
