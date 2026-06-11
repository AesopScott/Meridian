# Routine Authority Contract

This V2 backend slice owns routine authority boundaries for `ROU2`, `ROU3`,
the non-executable planning portion of `ROU4`, and Prime-owned routine review
posture for `ROU9`.

## Authority Owned

- Typed routine definitions with owner, scope refs, triggers, creator, state,
  timestamp, and evidence refs.
- Enable/disable state transitions that are recorded as backend domain state.
- Manual run planning that produces a display-safe plan or a disabled blocker.
- Prime routine review decisions over reviewed workflow result/error summaries,
  including accept, repair-route, retry-after-repair, and human-gate
  escalation posture.
- Serialization with explicit `execution_authorized=False` and
  `scheduler_mutation_authorized=False` sentinels.

## Authority Not Owned

- Scheduler mutation, timer registration, background monitors, cron-like runs,
  queue mutation, workflow execution, provider/model calls, bridge routes, or UI
  controls.
- Executable accept/reroute/retry/escalate actions, quiet-mode routing, run
  history, and archive/history remain later backend slices.
- Raw prompts, provider responses, worker chat, transcripts, credentials,
  tokens, local paths, and raw artifact bodies must never appear in routine
  definitions or run plans.

## Display-Safe Evidence

Routine payloads may include only typed IDs, names, owners, safe refs, trigger
labels, state, timestamps, reason text, reviewed result summaries, disposition
posture, and evidence refs. Safe URI refs are semantic identifiers such as
`routine://review/checkpoint`, not filesystem paths. Prime routine review
payloads never include raw worker outputs, raw result bodies, raw worker
history, prompt text, provider responses, or action-authorized controls.
