# Prime Autonomy V2 Contract

**Status:** V2 first-wave contract — domain slice not yet implemented; runtime in `meridian_core/prime_autonomy.py` to be built by Build 1 (or other runtime lane) after this contract lands.
**Owner harness:** Prime (autonomy surface). Consumes Echo, Atlas, Aegis, Session Lifecycle, Review Console, FileMap.
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, every harness, Scott, future contributors.
**Purpose:** Define `PrimeNextAction` and the deterministic selector that turns project/backlog/lane/review-gate state into a proposed next action with confidence, blockers, and required human-gate status. No model calls in the first slice.

V1 made Prime *visible*. V2 makes Prime *meaningfully proactive*. The autonomy surface is the seam where Prime stops asking "what do you want me to do, Scott?" and starts saying "given the state of this project, here is what I propose to do next, here is what would block it, and here is what would force a human gate." Scott can still steer or veto from the cockpit — but the default is Prime offering a typed, defensible recommendation, not silence.

This document is implementation-facing. It pins the domain shape, the deterministic selector inputs and ordering rules, the prompt-drag posture, the stop conditions that send Prime to Review Console instead of acting, and the first runtime tests.

---

## What Prime Autonomy Is — and Is Not

Prime autonomy is the *deterministic selector* that produces a `PrimeNextAction` from current project state. It is not:

- **A planner.** It does not invent multi-step roadmaps. It picks the next discrete action.
- **A model call.** The first slice has no inference. Everything is structural.
- **An executor.** It proposes; it does not spawn sessions, mutate backlogs, or dispatch model calls.
- **A bypass.** It cannot skip Aegis, cannot skip Review Console gates, cannot move branches or worktrees, cannot publish anything.
- **A backlog rewriter.** It reads backlog state. It does not edit it.
- **A confidence judge in disguise for prompt-budget escalation.** Echo/Atlas inputs come in as already-typed hits with their own scores; Prime autonomy combines them deterministically — no "let me think about this" injection.

Prime autonomy is the thing that lets Prime answer the question "what should I do next on project X?" with a structured, reviewable record. The record is what Bifrost renders, what Aegis gates, what Review Console may hold, and what Session Lifecycle eventually consumes if execution is approved.

---

## Harness Ownership

| Concern | Owner |
|---|---|
| Produce the `PrimeNextAction` record | Prime (autonomy module) |
| Provide durable memory hits | Echo |
| Provide retrieval hits over files/docs | Atlas |
| Produce the `CognitionPolicy` for the proposed action | Aegis |
| Provide backlog and project state | Project/backlog source (existing — out of scope for this contract) |
| Provide lane state (active, idle, stale) | Beacon + lane state module |
| Provide review-gate state | Review Console |
| Provide proof state | Aegis (`ProofTrail`) |
| Execute the action if approved | Session Lifecycle |
| Render to Scott | Bifrost |

Prime autonomy *reads* everything above and *writes* nothing except the `PrimeNextAction` record itself.

---

## Domain Shape

The runtime slice (`meridian_core/prime_autonomy.py`) introduces a small set of frozen dataclasses. Names and field semantics are normative; field types follow existing `meridian_core` conventions (frozen dataclasses, enums, tuples).

### `PrimeNextAction`

The proposed next action and everything Prime needs to defend it.

- `action_id` — stable identifier, deterministic from inputs where possible.
- `project` — project key (e.g., `meridian`, `polaris`, `aesop`). Required.
- `objective_ref` — reference to the backlog/objective record the action advances (id + short label). Required when the action is backlog-derived; omitted only for `MAINTENANCE` and `OBSERVE` action types.
- `action_type` — `PrimeActionType` enum: `BUILD`, `REVIEW`, `VERIFY`, `REPAIR`, `PLAN`, `OBSERVE`, `ESCALATE`, `MAINTENANCE`. Maps to Aegis's `CognitionActionType` for policy lookup.
- `summary` — short human-readable headline, ≤ ~200 chars. The one line Bifrost shows in the cockpit.
- `risk_tier` — integer 1–4, from Aegis's tier engine for the (project, action_type, objective) triple.
- `confidence` — `PrimeConfidence` enum: `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`. Confidence is a deterministic function of input completeness (see Confidence Rules), not a learned score.
- `blockers` — tuple of `PrimeBlocker` records. Empty when the action is unblocked.
- `required_human_gate` — `PrimeHumanGateStatus` enum: `NONE`, `RECOMMENDED`, `REQUIRED`. `REQUIRED` always when `risk_tier == 4` or when any blocker is `HUMAN_GATE`.
- `echo_inputs` — tuple of `MemoryHit` summaries Prime consulted (already typed via Echo's contract — see prompt-drag note).
- `atlas_inputs` — tuple of `AtlasHit` records Prime consulted (already typed via Atlas's contract).
- `cognition_policy_result` — `CognitionPolicyResult` from Aegis for the proposed action. Required.
- `session_command_recommendation` — optional `PrimeSessionCommand` (see below). Present when execution would route through Session Lifecycle.
- `proof_trail_required` — optional `ProofTrail` handle describing the evidence the action would need before promotion. Present when `risk_tier >= 2`.
- `created_at` — UTC timestamp.
- `selector_version` — short string identifying the selector ruleset that produced this action. Bumps on rule changes for reproducibility audits.

`PrimeNextAction` is immutable. A reissue is a new record with a new id and a new `created_at`.

### `PrimeBlocker`

A typed reason the action cannot proceed unmodified.

- `kind` — `PrimeBlockerKind` enum: `STALE_LANE`, `OPEN_REVIEW_GATE`, `FAILED_PROOF`, `MISSING_PROOF`, `HUMAN_GATE`, `BRANCH_PERMISSION_REQUIRED`, `WORKTREE_COLLISION`, `MISSING_FILEMAP_ENTRY`, `MISSING_ECHO_CONTEXT`, `MISSING_ATLAS_CONTEXT`, `POLICY_DENIED`.
- `target` — short string identifying what is blocked on (lane name, gate id, proof id, file path, etc.).
- `summary` — short prose, ≤ ~200 chars.
- `severity` — `PrimeBlockerSeverity` enum: `HARD` (must clear before action can proceed) or `SOFT` (action can proceed at reduced confidence). The selector reduces confidence one level per `SOFT` blocker, capped at `LOW`.

`HARD` blockers always force `confidence = INSUFFICIENT` and `action_type` may be coerced to `OBSERVE` or `ESCALATE` (see Selection Rules).

### `PrimeSessionCommand`

The recommended Session Lifecycle command that would execute the action. Pure recommendation — Session Lifecycle is the actor.

- `command_kind` — `PrimeSessionCommandKind` enum: `SPAWN`, `STEER`, `WATCH`, `RECOVER`, `STOP`, `ARCHIVE`, `NONE` (when the action is observation-only).
- `target_lane` — lane name (e.g., `build-1`, `codex-reviews-a`). Required for `SPAWN` and `STEER`.
- `branch_permission_object_required` — bool. True for any command that would move branch or worktree state.
- `input_packet_summary` — short string describing what context Session Lifecycle would hand to the workflow sub-agent. The full work-order construction happens at execution time and follows `docs/workflow-subagent-harness-contract.md`.

---

## Deterministic Selection Rules

The selector is a pure function of: `project`, the backlog/objective snapshot, the lane state snapshot, the review-gate snapshot, the proof snapshot, available `MemoryHit`s, available `AtlasHit`s, and the `CognitionPolicy` engine. Two identical inputs must produce identical `PrimeNextAction` records.

Rules are applied in the order below. The first rule whose condition fires determines `action_type`. Subsequent rules may add blockers and adjust confidence but do not change `action_type` once set.

### Rule order (highest priority first)

1. **Tier-4 work in flight without human gate** → `action_type = ESCALATE`. The action is "surface the tier-4 work to Scott." `required_human_gate = REQUIRED`. `confidence = HIGH` because the rule is structural.
2. **Open Review Console gate awaiting Scott** → `action_type = ESCALATE`. The action is "surface the gate." `HUMAN_GATE` blocker (HARD). `required_human_gate = REQUIRED`.
3. **Failed proof on the highest-priority backlog item that has any tier-2+ activity** → `action_type = REPAIR`. Add `FAILED_PROOF` blocker (HARD) targeting the failed proof. `confidence = HIGH` only if Echo + Atlas can supply context for the repair; otherwise `MEDIUM` and add `MISSING_*` SOFT blockers as appropriate.
4. **Stale active lane that holds a higher-priority objective than the next candidate** → `action_type = REPAIR` (recovery). Add `STALE_LANE` blocker (HARD). `session_command_recommendation.command_kind = RECOVER` targeting that lane. Recommend `WATCH` first if Beacon staleness age is below the configured `recover_threshold`.
5. **Worktree collision detected for the next candidate's lane** → `action_type = OBSERVE`. Add `WORKTREE_COLLISION` blocker (HARD). Prime does not propose execution into a colliding lane.
6. **Next ready backlog item exists, is not blocked, and Aegis policy is `ALLOW`** → `action_type` is the backlog item's natural type (`BUILD`, `REVIEW`, `VERIFY`, `PLAN`). `session_command_recommendation.command_kind = SPAWN` against the matching lane. `confidence = HIGH` if Echo + Atlas inputs are sufficient and no SOFT blockers fire; otherwise step down per the Confidence Rules.
7. **Next ready backlog item exists but Aegis policy is `BLOCKED_BY_PROOF` or `BLOCKED_BY_HUMAN_GATE`** → `action_type = OBSERVE` or `ESCALATE` (per blocker kind). Add the corresponding HARD blocker. `required_human_gate = REQUIRED` for the human-gate variant.
8. **No ready backlog item, but there is maintenance work** (FileMap gap, stale Echo memory cleanup, idle-lane heartbeat overdue) → `action_type = MAINTENANCE`. `session_command_recommendation.command_kind = NONE`. `confidence = HIGH` only if the maintenance task itself is fully specified by inputs; otherwise `MEDIUM`.
9. **None of the above** → `action_type = OBSERVE`. `summary` describes what Prime is waiting on. `session_command_recommendation.command_kind = NONE`. `confidence = HIGH` because the rule is structural.

### Prompt-drag avoidance (cross-cutting)

These rules are checked at the *input gathering* step, before rule order is applied. They are normative.

- Echo inputs MUST come from a typed `MemoryQuery` against the project, capped at the Echo hard upper bound (recommended ≤ 25 hits in first slice). The selector never quotes `MemoryRecord.body`; only `summary` and `reason` may live on `PrimeNextAction.echo_inputs`.
- Atlas inputs MUST come from a typed `AtlasQuery` against the project's relevant terms and required paths, capped at the Atlas hard upper bound (recommended ≤ 25 hits). The selector never includes whole files; only `AtlasHit.excerpt` may appear on `PrimeNextAction.atlas_inputs`.
- The selector MUST request `CognitionPolicy` from Aegis with the proposed `action_type`, `risk_tier`, and the action's intent — and MUST honor `requires_proof`, `requires_review`, and `requires_human_gate` in the resulting `CognitionPolicyResult`.
- The selector MUST NOT inflate the input lists beyond what fits in `PrimeNextAction` rendering (recommended ≤ 5 of each on the rendered action; the rest live in audit trail only).
- If Echo or Atlas would return more candidates than the selector can use, the selector takes the top-ranked subset and records `truncated=True` on internal telemetry — it does NOT issue a broader query to "get more context."

### Confidence Rules

Confidence is deterministic:

- Start at `HIGH`.
- Step down one level for each `SOFT` blocker present.
- Coerce to `INSUFFICIENT` if any `HARD` blocker is present.
- Coerce to `INSUFFICIENT` if Aegis returns `BLOCKED_BY_PROOF` or `BLOCKED_BY_HUMAN_GATE` (these always also produce a HARD blocker).
- Floor at `LOW` for SOFT-only step-down.

`INSUFFICIENT` confidence means Prime will not propose execution; the action is either `OBSERVE` or `ESCALATE` and Bifrost renders it as "Prime is waiting on X" or "Prime needs Scott's attention on X."

---

## Echo and Atlas Inputs — Posture

Echo and Atlas inputs are how the selector justifies its choice. They are **not** how Prime "thinks" about the action. The selector reads them, scores them only for inclusion in the audit record (top-N), and threads them through Aegis policy lookup. The selector does not summarize them, does not re-rank them with a model, and does not concatenate them into a prompt.

`echo_inputs` and `atlas_inputs` on `PrimeNextAction` exist so that:

- Bifrost can render *why* Prime proposes this action.
- Aegis can audit *what context* informed the proposal.
- Review Console can show Scott the same evidence Prime saw.
- Future workflow sub-agents that execute the action receive a pre-vetted input bundle without Prime having absorbed it raw.

If Echo and Atlas have nothing relevant, `echo_inputs` and `atlas_inputs` are empty tuples. Empty is normal, not a failure. The selector still produces an action — it just records `MISSING_ECHO_CONTEXT` and/or `MISSING_ATLAS_CONTEXT` as SOFT blockers, which steps confidence down.

---

## Stop Conditions — Route to Review Console Instead of Acting

The selector must surface to Review Console (via `action_type = ESCALATE` and `required_human_gate = REQUIRED`) in any of these cases. These are hard rules, not heuristics.

| Condition | Why |
|---|---|
| `risk_tier == 4` | Tier-4 actions are irreversible / public-facing / financial / account-affecting / policy-setting. Scott decides. |
| Aegis returns `BLOCKED_BY_HUMAN_GATE` for the action's policy | The policy itself requires Scott. |
| Failed proof on tier-2+ work and the highest-confidence repair Prime can construct still requires a `BRANCH_PERMISSION_REQUIRED` blocker | Branch/worktree moves require Scott or Prime permission per `docs/prime-restart-resteer-logic.md`. |
| Open Review Console gate older than the configured stale-gate threshold | The gate should not be silently bypassed. |
| Tier-3 dual-lane disagreement that the Council Chairman cannot resolve | Council escalation rule — Scott judges the fork. |
| Worktree collision detected on the only viable lane for the highest-priority objective | Collision risk is not auto-resolvable. |
| Stale active lane that holds tier-3+ work and Beacon staleness age exceeds the configured `escalate_threshold` | Stale tier-3+ work is a release-discipline event. |
| Backlog item is missing required FileMap entries and no candidate exists for the FileMap lane to fill them | Information gap that needs Scott's prioritization. |
| Two or more rules at the same priority would coerce contradictory `action_type` values | Ambiguity is not silently broken. Scott decides which rule wins for this project. |

In all of the above, the selector still produces a `PrimeNextAction` — but the action is "tell Scott about this" rather than "do this." Bifrost renders it with the same shape; Review Console treats it as a gate.

---

## What This Contract Does Not Decide

- It does not decide *how* Bifrost renders the action. That belongs to the Bifrost V2 extensions contract.
- It does not decide *how* Session Lifecycle constructs the workflow work order. That belongs to `docs/workflow-subagent-harness-contract.md`. The `PrimeSessionCommand` is a recommendation, not the work order.
- It does not decide *what* counts as a stale lane or what staleness thresholds are. Those come from Beacon's configuration.
- It does not decide backlog ordering. The backlog source provides the priority list; the selector reads it.
- It does not decide model adapter choice. Relay's `RelayRoute` plus Aegis's policy do.
- It does not decide *when* to invoke the selector. That's an orchestrator concern (Prime restart/resteer loop per `docs/prime-restart-resteer-logic.md`).

---

## Failure-Soft Behavior

The selector must fail soft from Prime's perspective.

| Condition | Behavior |
|---|---|
| Backlog source returns empty | Produce `PrimeNextAction(action_type=OBSERVE, summary="no backlog work available")`. |
| Echo store empty or absent | `echo_inputs = ()`; add `MISSING_ECHO_CONTEXT` SOFT blocker. No exception. |
| Atlas returns no hits | `atlas_inputs = ()`; add `MISSING_ATLAS_CONTEXT` SOFT blocker if the rule expected hits. No exception. |
| Aegis policy lookup fails | Coerce `action_type = OBSERVE`; add `POLICY_DENIED` HARD blocker with summary describing the failure. No exception bubbles up. |
| Lane state snapshot unavailable | Coerce `action_type = OBSERVE`; add `STALE_LANE` HARD blocker with target `"all"`. |
| Review Console snapshot unavailable | Coerce `action_type = OBSERVE`; add a `POLICY_DENIED` HARD blocker rather than guess. |
| Selector internal error | Last-resort: return `PrimeNextAction(action_type=ESCALATE, confidence=INSUFFICIENT, required_human_gate=REQUIRED, summary="selector failed; route to Scott")`. The selector never raises into the orchestrator. |

The orchestrator never sees a bare exception from prime autonomy. Every failure produces a `PrimeNextAction`.

---

## First Runtime Tests

Build 1 (or whichever runtime lane picks up `meridian_core/prime_autonomy.py`) should land at minimum the following tests in `tests/test_prime_autonomy.py` before the slice is marked built. These are the proof gates the V2 Prime Autonomy first slice must clear. No model calls in any test.

### Domain shape

- `PrimeNextAction`, `PrimeBlocker`, `PrimeSessionCommand` are frozen dataclasses.
- `PrimeActionType`, `PrimeConfidence`, `PrimeBlockerKind`, `PrimeBlockerSeverity`, `PrimeHumanGateStatus`, `PrimeSessionCommandKind` enums cover the listed values.
- Mutation attempts raise `FrozenInstanceError`.
- `tuple[..., ...]` fields are tuples (not lists) on returned actions.

### Selector — rule order

- Tier-4 work in flight without human gate ⇒ `action_type=ESCALATE`, `required_human_gate=REQUIRED`.
- Open Review Console gate awaiting Scott ⇒ `action_type=ESCALATE`, `HUMAN_GATE` blocker present.
- Failed proof on highest-priority tier-2+ item ⇒ `action_type=REPAIR`, `FAILED_PROOF` blocker present.
- Stale active lane holding higher-priority objective ⇒ `action_type=REPAIR`, `STALE_LANE` blocker, `session_command_recommendation.command_kind=RECOVER`.
- Worktree collision on next candidate ⇒ `action_type=OBSERVE`, `WORKTREE_COLLISION` blocker.
- Next ready backlog item, unblocked, policy `ALLOW` ⇒ `action_type` matches backlog item type, `session_command_recommendation.command_kind=SPAWN`.
- Backlog item with policy `BLOCKED_BY_HUMAN_GATE` ⇒ `action_type=ESCALATE`, `required_human_gate=REQUIRED`.
- No ready backlog, maintenance available ⇒ `action_type=MAINTENANCE`.
- Truly nothing to do ⇒ `action_type=OBSERVE`, `confidence=HIGH`.

### Selector — determinism

- Two identical input snapshots produce identical `PrimeNextAction` (compare full record except `created_at`).
- `selector_version` is stable for a given selector ruleset.

### Confidence rules

- Zero blockers ⇒ `HIGH`.
- One SOFT blocker ⇒ `MEDIUM`.
- Two SOFT blockers ⇒ `LOW`.
- Three+ SOFT blockers ⇒ `LOW` (floor).
- Any HARD blocker ⇒ `INSUFFICIENT`.
- Aegis `BLOCKED_BY_PROOF` or `BLOCKED_BY_HUMAN_GATE` ⇒ `INSUFFICIENT` and corresponding HARD blocker present.

### Prompt-drag posture

- `echo_inputs` length ≤ rendered cap (recommended 5) on the returned action even when Echo returned more.
- `atlas_inputs` length ≤ rendered cap (recommended 5) on the returned action even when Atlas returned more.
- No `MemoryRecord.body` text appears anywhere in `PrimeNextAction` (test by field walk + substring check on a stub record with a unique body marker).
- No raw file content appears in `atlas_inputs` (test similarly on a stub Atlas hit with a unique full-file marker that should never appear in `excerpt`).

### Stop conditions → Review Console

- Tier-4 action ⇒ `required_human_gate=REQUIRED`.
- Aegis `BLOCKED_BY_HUMAN_GATE` ⇒ `required_human_gate=REQUIRED`.
- Tier-3 dual-lane disagreement (simulated with a fake Council fork) ⇒ `action_type=ESCALATE`.
- Stale tier-3+ lane past `escalate_threshold` ⇒ `action_type=ESCALATE`.
- Worktree collision on only viable lane ⇒ `action_type=OBSERVE` with `WORKTREE_COLLISION` HARD blocker.
- Contradictory rules at same priority ⇒ `action_type=ESCALATE` (selector refuses to silently pick).

### Failure-soft

- Empty backlog ⇒ `action_type=OBSERVE`, `confidence=HIGH`.
- Empty Echo store ⇒ no exception; `MISSING_ECHO_CONTEXT` SOFT blocker if rule expected hits.
- Empty Atlas hits ⇒ no exception; `MISSING_ATLAS_CONTEXT` SOFT blocker if rule expected hits.
- Aegis policy lookup raises ⇒ selector returns `action_type=OBSERVE` with `POLICY_DENIED` HARD blocker; no exception bubbles up.
- Lane state snapshot unavailable ⇒ `STALE_LANE` HARD blocker; no exception.
- Forced selector internal error ⇒ returns `action_type=ESCALATE`, `confidence=INSUFFICIENT`, `required_human_gate=REQUIRED`.

These tests are domain-only and use fake/stub providers for backlog, lane state, Echo, Atlas, Aegis, and Review Console — they do not require live runtime for any of those harnesses.

---

## Out-of-Scope Guardrails (first slice)

- No real session spawning. `PrimeSessionCommand` is a recommendation only; Session Lifecycle is the actor.
- No backlog mutation.
- No Review Console gate bypass.
- No model calls.
- No prompt expansion via Echo/Atlas (the selector reads typed hits and bounds them; that is the entire ingestion surface).
- No autonomous branch or worktree movement.
- No federation (cross-Meridian backlog), no public/account adapter strategy, no vendor-specific model presets.

---

## Cross-References

- `docs/v2-detailed-build-plan.md` Track 1 — the V2 plan entry this contract operationalizes.
- `docs/echo-memory-contract.md` — Echo's prompt-drag posture this contract honors.
- `docs/atlas-retrieval-contract.md` — Atlas's prompt-drag posture this contract honors.
- `docs/workflow-subagent-harness-contract.md` — where execution lands after the selector recommends a `SPAWN`/`STEER`/`RECOVER`.
- `docs/cognition-policy-v2-contract.md` (when written) — Aegis's `CognitionPolicy` and `CognitionPolicyResult` that this contract requires.
- `docs/session-lifecycle-v2-contract.md` (when written) — where Session Lifecycle defines what `SPAWN`/`STEER`/`RECOVER`/`WATCH`/`STOP`/`ARCHIVE` actually do.
- `docs/review-console-surface-contract.md` — where `ESCALATE`-type `PrimeNextAction`s are routed for Scott's disposition.
- `docs/prime-restart-resteer-logic.md` — restart/resteer semantics that govern when the selector is invoked.
