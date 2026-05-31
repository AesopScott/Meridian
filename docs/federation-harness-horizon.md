# Federation Harness Horizon

## Purpose

Federation is the horizon harness for connecting one Meridian to another Meridian. It belongs in V2 planning because Prime's session, proof, permission, and workflow contracts must be shaped so they can later cross a Meridian boundary without leaking unsafe state.

Federation runtime is not in V2. V2 only defines the architectural boundary.

## Owner

- Harness owner: Federation Harness
- Supervising intelligence: Prime
- Safety gate: Aegis
- UI surface: Bifrost harness panel, not permanent top navigation

## Discovery Principle

One Meridian may discover another Meridian only through explicit project/user consent. Discovery must not imply trust, shared memory, shared worktrees, shared branches, or shared account access.

Safe discovery data may include:

- instance name
- user-approved project alias
- supported harness capabilities
- accepted work-order shapes
- public proof/result schema versions

Unsafe by default:

- raw memory stores
- raw queue files
- raw worker transcripts
- filesystem paths beyond the approved project alias
- credentials or vendor account state

## Permission Boundaries

Federation must preserve user and project boundaries:

- no cross-Meridian action without explicit consent
- no silent branch movement
- no shared worktree
- no hidden account-based automation
- no implicit durable memory import
- no remote execution without a typed work order and proof return

Each cross-Meridian action must name:

- requesting Meridian
- responding Meridian
- project scope
- requested action
- allowed files or surfaces
- expected proof packet
- human gate, if required

## Prime-to-Prime Handoff Concepts

Federation handoffs should use typed packets:

- `ProjectSummary`: bounded project context, current objective, risk tier, active constraints
- `TaskRequest`: requested work, allowed files, expected output, proof commands
- `ProofPacket`: evidence, tests, render checks, review verdicts, or blocked reason
- `ReviewResult`: findings ordered by severity, repairs routed, clearance state
- `RefusalOrBlocker`: why the remote Meridian cannot or should not act

No handoff should include raw full transcripts by default.

## Shared Work Principles

- Prime may request work from another Prime, but the responding Prime owns local execution safety.
- A remote Meridian may decline a task when its local policy, queue state, risk tier, or user permission forbids it.
- Durable state changes require local proof and local permission.
- Cross-Meridian collaboration should prefer small bounded work orders over shared context windows.

## UI Implication

Federation appears as a harness panel in Bifrost. It is opened by Prime or by the user, not pinned permanently into top navigation.

The panel should show:

- known Meridian instances
- permission state
- active handoffs
- pending proof packets
- blocked/refused requests
- recent federation events

## Out Of V2 Scope

- network protocol
- authentication implementation
- marketplace/public registry
- shared mutable project state
- cross-account automation
- live multi-user editing

V2 only ensures Prime, Session Lifecycle, Aegis, and Workflow contracts do not paint Federation into a corner.
