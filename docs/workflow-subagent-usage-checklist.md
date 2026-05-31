# Prime Workflow / Sub-Agent Usage Checklist

**Status:** V2 operational reference — derived from the architecture note `docs/workflows-subagent-harness-architecture.md` and the domain contract `docs/workflow-subagent-harness-contract.md`.
**Audience:** Prime (orchestrator deciding what to offload).
**Purpose:** A short, actionable checklist Prime uses every time it considers whether bounded harness work should run in a separate workflow / sub-agent context instead of inside Prime's own window.

This checklist does not replace the architecture note or the contract. It is the **decision surface** Prime consults before issuing a `WorkflowWorkOrder`. Read the note for the *why*, the contract for the *shapes*; use this checklist for the *decision*.

---

## Quick Decision: Workflow or Not?

Answer these three questions before anything else.

1. **Is this job "spend up to N minutes doing this bounded thing and report back"?**
   - Yes → workflow candidate.
   - No (one prompt → one response) → use Model Harness / Relay call. Stop here.

2. **Would the intermediate noise of this job (raw text, transcripts, logs, drafts) bloat Prime's working context if it ran inline?**
   - Yes → strong workflow candidate.
   - No → may still be a workflow, but the case is weaker.

3. **Can this job be described with a clear `intent`, `action`, and `expected_result_shape`?**
   - Yes → issue a `WorkflowWorkOrder`.
   - No → the job is not yet bounded enough for a workflow. Refine the framing first.

If all three are Yes, proceed to the per-harness checklist below.

---

## Per-Harness Decision Checklist

For each harness, ask the same set of questions. If any answer is Yes for that harness, the job should run as a workflow.

### Echo (Durable Memory)

| Question | Example trigger |
|---|---|
| Will the job involve bulk text that must be distilled into typed `MemoryRecord` tuples? | Importing 50 log lines, compacting a memory store, distilling a long conversation into records. |
| Is the source material noisy (logs, transcripts, search results, raw notes)? | Agent chat logs, build output, raw Obsidian notes. |
| Would Prime reading the source material verbatim add no value? | Prime needs distilled records, not raw source text. |

**If any Yes → workflow.** Echo's job is to produce typed summaries. The raw source never belongs in Prime's window.

**Do NOT workflow:** A single `MemoryRecord` lookup or a targeted `MemoryHit` query — those are synchronous Model Harness calls.

### Atlas (Retrieval)

| Question | Example trigger |
|---|---|
| Will the job scan many files, many FileMap entries, or many Echo records? | Wide retrieval over 20+ files, broad doc-allowlist reads. |
| Will the job need to read, rank, and excerpt many candidates before returning a short list? | Searching docs for "session lifecycle" across the whole repo, ranking by relevance. |
| Would Prime reading every intermediate candidate degrade its ability to judge the final hits? | The retrieval space is large; Prime only needs the top-N ranked hits with excerpts. |

**If any Yes → workflow.** Atlas already returns `AtlasHit.excerpt`; running the full scan in a sub-agent keeps the intermediate reads out of Prime.

**Do NOT workflow:** A single `AtlasQuery` with ≤ 5 expected candidates — synchronous call is fine.

### Aegis (Gated Cognition / Proof)

| Question | Example trigger |
|---|---|
| Will the job review a `ProofTrail`, synthesize findings, or triage evidence? | Reviewing test output against a contract, cross-finding synthesis across lanes. |
| Will the job produce verbose intermediate analysis that Prime does not need to see? | Parsing raw test logs, comparing screenshots, reading long diff outputs. |
| Will the job produce a verdict (`ProofReviewVerdict`) rather than open-ended analysis? | "Does this commit pass the contract's runtime tests?" with a yes/no/blocking-reasons answer. |

**If any Yes → workflow.** Aegis review work is naturally verbose; the verdict is what Prime needs.

**Do NOT workflow:** A single `CognitionPolicy` check that is already a fast synchronous lookup — use a direct Aegis call.

### Relay (Model Dispatch)

| Question | Example trigger |
|---|---|
| Can the host primitive run a model call in a separate sub-agent context? | The backing model/workflow API supports sub-agent dispatch. |
| Would the raw model transcript bloat Prime's window? | Multi-call aggregation, dual-lane comparison synthesis. |
| Does Prime only need the structured dispatch summary, not the full token stream? | Prime wants "3 calls made, 2 passed, 1 failed with X error" — not the transcripts. |

**If any Yes → workflow.** This is the cleanest way to enforce model-output discipline: never let the transcript touch Prime.

**Do NOT workflow:** A single `PromptPacket` dispatch where Prime needs to read the full response inline.

### Bifrost (Cockpit UI)

| Question | Example trigger |
|---|---|
| Will the job involve a local preview build, render check, or UI verification? | Running `npm run build`, taking screenshots, checking escape/accessibility. |
| Would the raw HTML, CSS, console output, or screenshots swamp Prime's context? | A full render-check run produces a lot of artifact text. |
| Does Prime only need pass/fail and where to look, not the raw render? | Prime needs `BifrostRenderCheck` summary with file references, not the full page HTML. |

**If any Yes → workflow.** UI verification is verbose and Scott-facing; the verbose part stays in the sub-agent.

**Do NOT workflow:** A single view-model property check that is a fast synchronous assertion.

### Beacon (Liveness)

| Question | Example trigger |
|---|---|
| Will the job sweep many targets (files, sessions, harnesses) for liveness? | Checking all 5 live-build queue files, all worker sessions, all harnesses. |
| Is liveness work naturally bursty and periodic rather than continuous? | "Every 5 minutes, check all lanes" — this is a batch sweep. |
| Would raw per-target results flood Prime? | 50 individual health checks each with age, status, and reasons. |

**If any Yes → workflow.** Liveness sweeps in a sub-agent yield a compact `BeaconLivenessReport`.

**Do NOT workflow:** A single health ping against one session — synchronous call is fine.

### Session Lifecycle (Spawn / Watch / Steer / Recover)

| Question | Example trigger |
|---|---|
| Will the job involve watching, steering, or recovering a worker session? | Monitoring a build lane, attempting a restart, diagnosing a stale session. |
| Could the worker session's output be very chatty? | Build lanes produce long transcripts; watch loops accumulate text quickly. |
| Would keeping the raw session chat in Prime's window damage Prime's ability to coordinate other lanes? | Yes — this is the most damaging case for context bleed. |

**If any Yes → workflow.** Session Lifecycle is the case where prompt-drag protection matters most.

**Do NOT workflow:** A single "spawn session" command that returns a `session_id` — synchronous call is fine.

---

## What Must NEVER Be a Workflow

These jobs should *never* be dispatched as a workflow sub-agent. Prime must handle them directly.

| Job | Why not a workflow |
|---|---|
| "What should we do next?" | Prime's own deliberation. Prime does not delegate intent. |
| Anything that must mutate global state directly | Workflows return summaries; durable writes go through Prime + Aegis gates. |
| Long-running background loops without a bounded work order | "Watch forever" is not a workflow — it is a background process. Meridian does not run those in V2. |
| Single inferences | Use the Model Harness / Relay. A workflow for one prompt is overhead with no benefit. |
| Cross-project deliberation | A workflow operates on a single `project`. Cross-project decisions are Prime's job. |

---

## Risk-Tier Gating on Workflow Results

Before issuing the work order, confirm the risk tier (1–4). The tier determines what the workflow must return and what gates apply before Prime promotes the result.

| Tier | Required for promotion | Workflow must |
|---|---|---|
| **1** | Prime accepts the summary. No extra gate. | Return a valid `WorkflowResultSummary`. |
| **2** | Non-empty `proof_trail` + Aegis policy `ALLOW`. | Produce and attach a `ProofTrail`. |
| **3** | Tier-2 conditions + Review Console entry. | Same as Tier-2; Prime routes the summary to Review Console. |
| **4** | Tier-3 conditions + explicit Scott approval via human gate. | Set `requires_human_gate=True`; Prime refuses promotion otherwise. |

**Rule:** If you are unsure of the risk tier, default to Tier-2 (proof required) rather than Tier-1. An under-gated workflow result silently promoted is an Aegis finding.

---

## Pre-Dispatch Validation Checklist

Before issuing the `WorkflowWorkOrder`, verify every item.

- [ ] `intent` is a single sentence stating what success looks like.
- [ ] `action` matches the harness's published vocabulary.
- [ ] `expected_result_shape` names a known schema (`AtlasResult`, `ProofReviewVerdict`, `BifrostRenderCheck`, etc.).
- [ ] `risk_tier` is set (1–4) and consistent with the job's impact.
- [ ] `time_budget_seconds` and `hard_timeout_seconds` are set and reasonable.
- [ ] `input.allowed_tools` is explicit — no implicit "everything" grants.
- [ ] `input.allowed_paths` is scoped to the minimum needed.
- [ ] `input.forbidden_paths` blocks secrets, other lanes' queues, and `.env*`.
- [ ] `input.prompt_budget` is carried from Relay — not omitted.
- [ ] For tier-3+: `input.gate_context` is present.
- [ ] `parent_work_order_id` is only set if this is a legitimate nested delegation (max depth 2).

---

## What Prime Keeps After Dispatching

Once the work order is issued, Prime tracks only:

- The `work_order_id`.
- The last `WorkflowHeartbeat` summary line (liveness — not contents).
- The `risk_tier` and whether a gate is pending.

Prime does NOT keep:
- Raw transcripts, raw file content, raw search results, raw logs from the sub-agent.
- Heartbeat history — Bifrost renders it; Prime keeps only the latest line.

---

## When a Result Comes Back

### Success (`WorkflowResultSummary`)

- [ ] `result_shape` matches `expected_result_shape`.
- [ ] `proof_trail` is non-empty if `risk_tier >= 2`.
- [ ] `summary` is ≤ ~1000 chars.
- [ ] No raw transcript, file content, or log fields in `outputs`.
- [ ] `requires_human_gate` is respected; route to Review Console if true.
- [ ] Promote according to tier rules (see table above).

### Error (`WorkflowErrorSummary`)

- [ ] `failure_kind` is one of the typed enum values.
- [ ] If `failure_kind == RESTEER_REQUESTED`, examine `resteer_request.suggested_changes`.
- [ ] If `failure_kind == TIMEOUT`, check `partial_outputs` for salvageable work.
- [ ] If `failure_kind == GATE_REQUIRED`, the work order was misconfigured — fix and re-issue.
- [ ] If `failure_kind == INTERNAL_ERROR`, log and decide: restart (same order, fresh sub-agent) or resteer (new order).
- [ ] **Never promote outputs from an error result.** Errors do not write to durable state.

### Restart vs. Resteer Decision

| Condition | Action |
|---|---|
| Failure was contextual (timeout, transient tool error, stale session) | **Restart**: same work order, fresh sub-agent context. |
| Original framing was wrong (wrong paths, wrong action, wrong tier) | **Resteer**: new work order derived from `resteer_request.suggested_changes`. |
| Sub-agent says `do_not_retry=True` | Do not re-issue. Escalate to Review Console. |
| Multiple restarts fail in a row (≥ 3) | Escalate to Review Console. Do not loop indefinitely. |

---

## Cadence and Review

- After every **three workflow-backed results** that affect durable state (Echo records, FileMap entries, Review Console gates, branch operations), Prime must gate on Codex review before issuing further workflow work orders from the same lane.
- If a workflow result surfaces `requires_human_gate=True`, Prime must route to Review Console before issuing the next work order for that harness.
- Workflow dispatch telemetry (orders issued, results accepted, errors handled, time spent) should be observable in the Review Console and in per-lane build logs.

---

## Cross-References

- `docs/workflows-subagent-harness-architecture.md` — the *why* (narrative architecture).
- `docs/workflow-subagent-harness-contract.md` — the *shapes* (domain types, prompt-drag rules, runtime tests).
- `docs/prime-autonomy-v2-contract.md` — Prime's autonomy rules that decide *which* workflow to spawn.
- `docs/prime-restart-resteer-logic.md` — restart vs. resteer semantics.
- `docs/review-console-surface-contract.md` — where tier-3+ results route for Scott's disposition.
- `docs/echo-memory-contract.md`, `docs/atlas-retrieval-contract.md` — prompt-drag guardrails workflows must honor.

---

## Summary

1. Ask the three quick-decision questions.
2. Check the per-harness triggers.
3. Confirm the job is not on the "never workflow" list.
4. Set the risk tier and pre-dispatch validations.
5. Issue the `WorkflowWorkOrder`.
6. Track only liveness; let Bifrost render heartbeats.
7. On result: verify, gate by tier, promote or error-handle.
8. Restart for transient failures; resteer for framing failures; escalate if `do_not_retry` or after 3 consecutive restarts.
9. Gate on Codex review after every 3 durable-state-affecting workflow results.
