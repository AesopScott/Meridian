# Review Console Surface Contract

**Status:** Strategic/architectural — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Audience:** Prime, Bifrost, Beacon, Aegis, Relay, Scott, future contributors
**Purpose:** Define what the Review Console is, what belongs there, how Prime populates it, what actions Scott can take from it, and how it avoids the failure modes of prior surfaces.

The Review Console is the honest product name for what `context.md` calls the "non-orchestrator queue." The name change is intentional: "non-orchestrator" describes what it isn't, not what it does. The Review Console describes what it does — a surface where Prime surfaces review material, proof, gates, and findings for Scott's inspection or disposition.

---

## The Fundamental Distinction

Meridian has two conversational surfaces. They serve different purposes and must remain separate.

### Orchestrator Queue

The Orchestrator Queue is where **Scott and Prime talk**.

- Progress intentions: Prime saying what it intends to work on and why.
- Judgment requests: Prime asking Scott to decide something only Scott should decide.
- Strategic updates: important state changes Scott should know about.
- Bottleneck escalations: work that has stalled waiting for Scott's approval.
- Scott's instructions to Prime: direction, override, correction, prioritization.

The Orchestrator Queue is conversational. Its content is Prime's voice and Scott's voice. It should not fill with system noise, proof ledgers, or worker logs.

### Review Console

The Review Console is where **Prime surfaces material for Scott's eyes or disposition**.

- Artifacts and outputs Prime has produced or received that Scott may want to see.
- Proof results from Aegis: test results, browser checks, screenshots, waivers.
- Cross-check findings: independent review outputs, lane disagreement summaries.
- Gate items: decisions that require Scott's explicit approval before Prime can proceed.
- System readiness: Go call status for harnesses during wake.
- Worker completion summaries: what a builder, reviewer, or verifier finished.

The Review Console is not conversational. It is a review surface with disposable items. Scott reads, acknowledges, approves, rejects, inspects, or defers. Prime does not chat here.

The two surfaces may be tabs within the same screen, or the Review Console may be a persistent panel. Either way, their content streams are independent. An item placed in the Review Console does not appear in the Orchestrator Queue, and vice versa.

---

## What Prime May Place in the Review Console Without Asking Scott First

Prime may route these item types to the Review Console autonomously, without prompting Scott in the Orchestrator Queue:

### Informational Items (no Scott action required)

- **Cross-check findings (informational):** A review lane found a note, suggestion, or low-severity observation. No blocking action needed. Scott may inspect or dismiss.
- **Worker completion summaries:** A builder, reviewer, or verifier finished a task. Summary of what changed, what tests passed, commit hash. No Scott action required unless there is a proof gap.
- **System Go calls:** Harness readiness signals during wake (e.g., `Beacon Go`, `Relay Go`). Compact status lines, not prose. No Scott action needed unless a harness fails.
- **Proof results (passing):** Aegis completed a proof check and all evidence is in order. Logged as a record. No gate.
- **Council deliberation summary (low-risk tiers):** A summary of which Council voices Prime consulted and how the Chairman resolved the deliberation, logged for inspectability. No gate for tier 1–2.

### Gate Items (Scott action required before Prime continues)

- **Plan approval gates:** Prime has finished building a plan and is waiting for Scott's approval before beginning irreversible work.
- **Proof failures needing waiver:** Aegis could not complete proof automatically and the risk tier requires human attestation before Prime marks the work done.
- **Cross-check findings (blocking):** A review lane found a CRITICAL issue. Prime has stopped and is surfacing the finding. Scott must acknowledge or approve a repair plan.
- **Tier-4 risk actions:** Any action classified as irreversible, public-facing, financial, account-affecting, or policy-setting. Prime will not proceed without explicit Scott approval.
- **Council disagreement at high tier:** At tier 3–4, if the Council Chairman cannot resolve lane disagreement, Prime escalates the fork to Scott for judgment.
- **Release gates:** Before anything ships externally, the Review Console shows the artifact, its proof record, and waits for Scott's release approval.

Prime does not ping Scott in the Orchestrator Queue just because it placed something in the Review Console. Items go to the Orchestrator Queue only when Scott's direct attention is urgently needed: escalations, urgent bottlenecks, tier-4 decisions, or explicit progress intention updates.

---

## What Must Become a Human Gate

The following actions always require Scott's explicit approval in the Review Console before Prime proceeds. These are not heuristics — they are hard policy.

| Action class | Reason |
|---|---|
| Final plan approval before irreversible build work | Scope and direction judgment only Scott can make |
| Publishing to external audiences | Brand, message, timing — strategic judgment |
| Financial actions (spend, invoice, subscribe) | Irreversible cost, only Scott can authorize |
| Account operations (new accounts, permissions, deletions) | Scope and risk only Scott should approve |
| Policy changes (Charter mutations, permission expansions) | Authority chain integrity |
| Release to production (public deploy) | Responsibility and timing judgment |
| Tier-4 risk-tier actions (from risk assessment engine) | Systemic gate, not per-action heuristic |

A gate is not a suggestion. When an item is a gate, Prime does not attempt the action, does not approximate the action, and does not retry after timeout. The action queues in the Review Console until Scott provides explicit disposition. If Scott is unavailable, the gate holds. It does not silently degrade to tier-3 or auto-approve.

---

## How Content Should Appear

The Review Console shows typed item cards, not a plain message log.

### Card anatomy

Every item in the Review Console is a card with:

- **Type badge:** the item kind (PROOF, FINDING, GATE, SUMMARY, GO-CALL, ARTIFACT).
- **Provenance:** which harness, worker lane, or Prime process produced it.
- **Timestamp:** when it was placed.
- **Summary:** one sentence. What happened or what is needed.
- **Detail link:** expands to full output, diff, log, transcript, or screenshot.
- **Disposition controls:** the actions Scott can take (see below).
- **Status:** pending / acknowledged / approved / rejected / deferred / expired.

### Content rules by type

**PROOF cards (Aegis):**
- Show: evidence type (test / browser check / screenshot / log / waiver), pass/fail, which objective or task the proof covers.
- Passing proof: auto-status acknowledged after Scott reads; no action required.
- Failing proof: status stays pending until Scott approves a waiver or Prime re-attempts and passes.

**FINDING cards (cross-check / review lane):**
- Show: severity (informational / low / medium / high / critical), which file or area was reviewed, the finding summary, suggested action.
- Informational: auto-expire after read.
- Critical/blocking: stay pending, block the next build task until acknowledged.

**GATE cards:**
- Show: what action is pending, why it requires a gate, the risk tier, the evidence Prime has assembled.
- Status stays pending until Scott explicitly approves or rejects.
- Gate cards cannot auto-expire. They persist until disposed.

**SUMMARY cards (worker completion):**
- Show: role (builder / reviewer / verifier), task title, changed files, commit hash, test result.
- Auto-status acknowledged after read. No action required.

**GO-CALL cards (system boot):**
- Show: harness name, status (Go / degraded / failed), brief reason if degraded.
- Passing Go calls are informational only — auto-expire after Scott's first session view.
- Failed Go calls stay visible and escalate to the Orchestrator Queue if they affect Prime's ability to work.

**ARTIFACT cards:**
- Show: artifact type (document / screenshot / PR / build output), which task produced it, a preview or link.
- Some artifact cards include a release gate control if the artifact is destined for external publication.

---

## Actions Scott Can Take

Every card supports a subset of these disposition actions. Not all actions are available on all card types.

| Action | Meaning | Available on |
|---|---|---|
| **Acknowledge** | I've seen this; no further action needed | Informational, passing proof, Go calls, summaries |
| **Approve** | Proceed — gate unblocks | Gate cards, plan approvals, release gates |
| **Reject** | Do not proceed — route back to Prime | Gate cards, failing proof, critical findings |
| **Inspect** | Open full detail (diff, log, screenshot, transcript) | All card types |
| **Defer** | Keep visible; I'll act later | Gate cards (does not unblock — gate remains) |
| **Override** | Proceed despite finding; waiver recorded with reason | Proof failures, blocked findings (requires explicit waiver text) |
| **Escalate** | Promote to Orchestrator Queue for direct conversation | Any card, at Scott's discretion |

Override is not the same as Approve. Override records a waiver with Scott's explicit reason. Both are logged in Aegis's proof record. An override without a reason is rejected by the form — the waiver text field is required.

---

## How to Avoid Recreating the Polaris Worker-Card Wall

Polaris's session-card wall was useful as a diagnostic surface but harmful as a primary surface. It turned worker management into Scott's job. The Review Console must not repeat this.

**Rules that enforce the inversion:**

1. **Sessions are not primary items.** A worker session in progress is not a Review Console card. The Review Console receives the *output* of sessions, not their status feed. Session status belongs in Beacon (health) and is viewable on demand, not by default.

2. **Routine coordination is not visible here.** Builder routes correction to reviewer → reviewer routes back → Prime adjudicates. None of these internal loops appear in the Review Console unless a finding is blocking, a gate is required, or Prime explicitly chooses to surface a summary.

3. **No transcript walls.** Detail views show structured output (diffs, test results, proof records). They do not show raw model output transcripts by default. Transcripts may be available behind an expand, but they are never the default view.

4. **Card count is Prime's responsibility.** If the Review Console fills with noise, that is a Prime configuration problem, not a Scott attention problem. Prime should auto-acknowledge informational items that are clearly passing. Scott should not need to manually clear a backlog of routine events.

5. **"Inspect session" is a drill-down, not a primary workflow.** If Scott wants to see a specific worker's full state, there is a link. But arriving at the Review Console should not mean opening a wall of session cards.

---

## Relationship to Bifrost

Bifrost is the UI harness — the bridge between Scott and Meridian. The Review Console is a surface within Bifrost.

Bifrost owns:
- How the Review Console is rendered (card layout, tabs, panels).
- Navigation between Orchestrator Queue and Review Console.
- Visual hierarchy and attention signals (badge counts, color coding for gate states).
- The "inspect session" panel — opened on demand, not the default view.
- Audio integration (if Go calls become spoken, Bifrost manages the audio output and associated light/status indicators).

The Review Console surface contract (this document) defines *what goes there and why*. Bifrost's design specifies *how it looks*. These are separate concerns. Bifrost should not change what Prime routes to the Review Console; it only changes how that content is presented.

---

## Relationship to Beacon

Beacon is the heartbeat and health harness. It reports liveness, degraded states, and harness readiness.

Beacon data flows into the Review Console in two modes:

**Mode 1: System wake (Go calls)**
During Prime's wake sequence, Beacon checks each harness and sends Go-call cards to the Review Console. These are compact and auto-expire after Prime's first operational cycle. They are not conversational — they confirm Meridian came alive correctly.

**Mode 2: Runtime degradation**
If Beacon detects a harness has gone degraded or failed during a work session, it sends a FINDING card (severity: high or critical) to the Review Console. If the degraded harness affects Prime's active work, Prime also escalates to the Orchestrator Queue. If it is unrelated to current work, it remains visible in the Review Console until Scott acknowledges or Prime resolves it.

Beacon's full health feed (per-harness heartbeat, timing, liveness) is available in Beacon's own view, not streamed into the Review Console by default. The Review Console receives Beacon's judgments (Go / degraded / failed), not Beacon's raw telemetry.

---

## What This Contract Does Not Define

This contract is architectural. The following are out of scope and belong in later design work:

- Visual design, layout, animations, or component library choices — Bifrost's territory.
- Specific card UI component implementation — Bifrost/build work.
- Notification channels (email, push, Slack) for gate items when Scott is away — Charter/policy territory.
- Card expiry timers and retention policies — Aegis/harness policy territory.
- How Prime decides what risk tier to assign a given action — risk tier engine, separate contract.
- FileMap entries for this document — Build 3 owns FileMap.

---

## Summary

The Review Console is the named, typed surface where Prime routes review material, proof results, cross-check findings, gate items, worker summaries, and system Go calls — separated from the Orchestrator Queue so Prime's conversational voice stays clean and Scott's attention is not pulled into routine coordination.

Prime populates it autonomously for informational items. Gate items require Scott's explicit disposition before Prime continues. Cards are typed, provenance-tagged, and actionable. Sessions are not primary items. The console surfaces Prime's work product, not Prime's process.

The goal: Scott opens the Review Console and sees a tightly curated set of items that are either informational (passing, confirming, logging) or decisional (gates, escalations, waivers). Not a wall. Not a transcript. Not a session dashboard.
