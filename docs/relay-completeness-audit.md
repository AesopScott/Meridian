# Relay Completeness Audit

**Status:** Active design audit
**Date:** 2026-06-01
**Owner harness:** Relay
**Purpose:** Prevent Relay from being under-specified before Auto routing, model dispatch, or harness UI wiring.

## Why This Exists

Relay is one of Meridian's load-bearing harnesses. It decides which model, vendor, route, session, and proof posture Prime should use when the heartbeat points Prime at model work.

The danger is not only choosing the wrong model. The danger is failing to ask a question we did not realize mattered.

Use this audit before:

- enabling Auto model routing,
- adding a new provider/model route,
- wiring Relay harness UI,
- promoting a candidate model route to trusted,
- letting Prime use Relay for Tier 2+ work.

## Completeness Rule

Relay is not complete until it can answer every category below with a structured value, an explicit unknown, or a block reason.

Unknown is acceptable. Silent omission is not.

## Relay Must Decide

| Area | Question Relay Must Answer | Missing-Depth Failure |
|---|---|---|
| Intent | What is Prime trying to do: plan, build, review, verify, research, summarize, voice, release, settings, or harness logic? | One default model gets used for incompatible work. |
| Surface mode | Is the active surface User Session, Settings, or Harness mode? | Settings or harness logic accidentally inherits project chat context. |
| Project scope | Which project, initiative, repo, or venture owns this work? | Cross-project context bleed. |
| Role | What role is needed: orchestrator, builder, reviewer, verifier, researcher, release operator, classifier, voice, or memory helper? | The model gets the wrong instructions and proof expectations. |
| Risk tier | What is the risk tier and what gates follow from it? | High-risk work is routed like routine chat. |
| Human gate | Does the user need to approve before action, dispatch, release, or account use? | Prime acts past the user's intended boundary. |
| Account/session route | Can an existing account-backed session safely do the job before using APIs? | Meridian burns API cost or loses useful vendor session capabilities. |
| CLI route | Is a local CLI route available, authenticated, in the right cwd, and recoverable? | Work goes to a stale or wrong local environment. |
| Direct API route | Is direct API required for auditability, pinned model id, clean packet control, or telemetry? | Relay uses a weaker session/aggregator when proof needs direct control. |
| Aggregator route | Is an aggregator route allowed by tier, trust, policy, and cost? | OpenRouter or similar becomes hidden authority. |
| Session action | Should Relay reuse, start new, summarize/reset, transfer, or avoid a session? | Context fills, pollutes, or crosses reasoning modes. |
| Context health | Is context clean, bounded, project-specific, and below payload limits? | Prompt drag and stale reasoning become invisible. |
| Reasoning mode | Did work shift from planning to coding, coding to review, review to repair, or discussion to proof? | Session/model role no longer matches the work. |
| Dual lane | Is independent second-lane reasoning required? | Tier 3 loses independence; shared blind spots persist. |
| Model family | Which model family best matches the role: Claude, OpenAI/Codex, DeepSeek, OpenRouter route, local, or future model? | Model choice is based on habit instead of task fit. |
| Vendor | Which vendor is actually being contacted? | UI says one thing while route uses another. |
| Exact model id | What exact model id/version is in use? | Model identity drifts or aliases change under us. |
| Tool access | Does the model/session have the tools required for the task? | Prime routes coding or browser work to a route that cannot act. |
| Steering capability | Can Relay steer the session: none, user-message, directive, resume-context, system-prompt, or API parameter? | Prime assumes control that backend does not support. |
| Output type | What output is expected: plan, patch, review, proof, summary, voice, metadata, or decision? | Response cannot be validated or routed. |
| Proof requirement | What proves this route's output is good enough? | Model output becomes its own evidence. |
| Aegis gate | Does Aegis allow this route for the action and tier? | Relay bypasses proof/security policy. |
| Trust state | Is the route trusted, candidate, degraded, blocked, or unknown? | Candidate routes gain production authority by accident. |
| External review | Does this provider/model require independent review before Tier 3+? | New routes become trusted without validation. |
| Prompt budget | What budget applies and what prompt payload is being sent? | Prompt size grows invisibly. |
| Cost pressure | Is the route cheap, standard, premium, unknown, quota-limited, or exhausted? | Expensive routes are used without reason. |
| Latency pressure | Does the work need fast interaction or can it tolerate slow deep reasoning? | Prime waits on premium/slow routes for trivial work. |
| Privacy/data policy | What data leaves local/session boundaries and under what provider policy? | Sensitive content goes to inappropriate routes. |
| Account risk | Does this use an account, paid quota, external service, or public action surface? | The user pays or exposes data unintentionally. |
| Availability | Is the route healthy, rate-limited, unavailable, stale, or failing auth? | Relay keeps choosing broken routes. |
| Fallback | What is the fallback if the preferred route fails? | Silent fallback changes trust/cost/model behavior. |
| No-fallback condition | When should Relay block instead of fallback? | High-risk work silently downgrades to weaker route. |
| Observability | What will Bifrost show: model, vendor, route class, cost, trust, payload, and blockers? | User cannot tell what Prime used. |
| Telemetry | What metadata must be captured: latency, tokens, payload hash, response hash, cost, selected provider, warnings? | Route cannot be audited later. |
| Memory boundary | What should Echo/Atlas store or retrieve, and what must not enter prompt context? | Long-term memory and live session context blur together. |
| Prompt filter | What should Filter include/exclude before Relay sends context? | Too much or too little context enters the route. |
| Harness mode | If this is harness work, what logic item is being reviewed or updated? | Harness panel becomes generic chat. |
| Settings mode | If this is settings work, what configuration item is being changed? | Settings panel becomes generic chat. |
| User decision | If this is user-facing, what decision or plan is the user reviewing? | User mode becomes an unstructured work log. |
| Cancellation | Can the route be stopped, interrupted, or ignored safely? | Long-running work cannot be controlled. |
| Retry | Should retry use same session/model, new session, different model, or repair lane? | Failures repeat blindly. |
| Promotion/demotion | Did this call provide evidence to promote, demote, or block a route? | Trust state never learns from experience. |

## Tier-Specific Completeness Gates

| Tier | Completeness Gate |
|---|---|
| Tier 0 | Relay must prove no model route is needed. |
| Tier 1 | Relay may use single lane, but must know route class, cost posture, and fallback. |
| Tier 2 | Relay must know proof requirement, context health, and whether independent review is needed. |
| Tier 3 | Relay must use independent dual-model lanes unless explicitly waived; account/session-first still applies, but each lane needs route class, trust, proof, and telemetry. |
| Tier 4 | Relay may prepare or review only; human gate required; no fallback may reduce trust without explicit approval. |

## Account-First Route Audit

Before using a direct API, Relay must ask:

1. Is the user already logged into an account-backed vendor session that can do this safely?
2. Does that session have the right project, role, tools, and context health?
3. Can Prime steer it?
4. Can Meridian capture enough proof and telemetry?
5. Is the session cheaper or more capable than API use?
6. Would direct API be safer because it gives a pinned model id, clean prompt packet, and audit trail?

If the answer to 1-5 is yes and 6 is no, use the account/session route first.

## Session Lifecycle Audit

Before reusing a session, Relay must ask:

1. Is the session for the same project?
2. Is it the same role/reasoning mode?
3. Is context under budget?
4. Is the context clean, not polluted by unrelated work?
5. Is the session still steerable?
6. Does the user expect continuity here?
7. Would a fresh session reduce risk or improve reasoning?

Start a new session when:

- context is near full,
- prompt payload is growing without reason,
- role changes,
- project changes,
- session is stale or polluted,
- tool/cwd/auth state is wrong,
- Tier 3+ needs independent reasoning,
- review or repair requires a different cognitive stance.

## Red-Team Questions

Ask these before declaring Relay logic complete:

1. What route would Relay choose if every preferred model is unavailable?
2. What route would Relay choose if the cheapest model is unsafe?
3. What happens if the account session is logged in but pointed at the wrong project?
4. What happens if a model alias silently changes provider/model version?
5. What happens if OpenRouter returns a different underlying provider than expected?
6. What happens if a direct API has no quota but an account session is available?
7. What happens if a session is context-full but still appears "working"?
8. What happens if Tier 3 needs two lanes but only one trusted route is available?
9. What happens if DeepSeek gives a good answer before validation passes?
10. What happens if a model route is fast but cannot produce proof?
11. What happens if the user has asked for low cost but Aegis requires stronger proof?
12. What happens if Relay cannot explain why it chose a model?

## Required Relay Decision Record

Every Relay route decision should be able to produce:

```text
heartbeat_id
project
surface_mode
intent
role
risk_tier
session_action
route_class
vendor
model_id
account_or_api_source
context_health
prompt_payload_status
dual_lane_required
lane_independence_reason
trust_state
proof_required
human_gate_required
cost_posture
latency_posture
privacy_notes
fallback_allowed
fallback_blockers
observability_fields
telemetry_required
explanation_for_prime
```

## Stop Conditions

Relay must block instead of route when:

- risk tier is unknown,
- route class is unknown,
- exact model id is unknown for Tier 2+,
- context health is unknown for session reuse,
- Tier 3 cannot get independent lanes and no waiver exists,
- Aegis gate is missing,
- proof requirement is unknown,
- route would silently downgrade trust,
- user/account cost exposure is unclear,
- provider identity cannot be shown to Bifrost,
- Relay cannot explain the selection.

## Product Implication

The Relay harness panel should show this audit as logic items:

- route class,
- session action,
- model/vendor choice,
- risk/proof gates,
- context health,
- dual-lane status,
- account/API/aggregator precedence,
- cost/privacy pressure,
- fallback blockers,
- explanation for Prime.

If the panel cannot show these, Relay is not ready for Auto.

## Current Implementation Snapshot -- 2026-06-02

**Git state:** Relay harness work has been restored onto `main`.

**Main commits now carrying the visible Relay harness depth:**

- `1af564f9` -- Relay panel reads backend/domain snapshot instead of static UI copy.
- `1d809d06` -- Relay dispatch lane/order/payload policy is visible.
- `fb0dd4c9` -- Relay audit depth is visible.
- `98a2c137` -- Relay capability sections render as collapsible harness headers.
- `24e15ba5` -- Relay Prime Directives and Prime Directive Proofs render at the top of the harness.

**Visible Relay harness now starts with Prime Directives:**

1. Account/session-first, never silent fallback.
2. Risk tier determines model depth.
3. No drift between route, proof, and visible harness.

**Visible Relay harness then shows Prime Directive Proofs:**

1. What route was tried first, what route was selected, and what alternatives were rejected?
2. What risk tier was assigned, and what model-lane depth did that tier require?
3. Where is the visible proof in the harness for the route, blockers, dispatch lanes, prompt budget, and audit reason?

**Backend source of truth:**

- `meridian_core/relay.py` owns deterministic route, tier, lane, session, proof, and blocker logic.
- `meridian_core/relay_dispatch.py` owns immutable dispatch plan shape.
- `meridian_core/relay_logic_snapshot.py` serializes the visible Relay harness snapshot.
- `scripts/meridian-model-bridge.js` exposes `/bridge/relay-logic`.
- `index.html` renders `/bridge/relay-logic` into collapsible Relay headers.

**Visible collapsible sections now include:**

- Prime Directives
- Prime Directive Proofs
- Relay logic source
- Relay Job
- Risk Tier Routing
- Model Lane Logic
- Access Route Precedence
- Session Lifecycle Logic
- Context Latency Privacy
- Prompt Budget Logic
- Audit Logic
- Dispatch Logic
- Current Limits
- Tier 3 dual-model logic
- Fallback blocker logic
- Proof and telemetry logic

**Verification recorded in Git context:**

- `python -m pytest tests\test_relay.py tests\test_relay_dispatch.py tests\test_relay_logic_snapshot.py -q` -> 163 passed.
- `index.html` script parse passed.
- Served `http://127.0.0.1:5500/index.html` includes `Prime Directives`, `Prime Directive Proofs`, and `/bridge/relay-logic`.
- Served page no longer includes old static `const relayModels`.
- Live `/bridge/relay-logic` returns 3 directives, 3 proofs, and 10 capability sections.
- Relay snapshot contains no `heartbeat` text.

**Current boundary:**

Relay is now visible enough for Prime integration planning. Auto routing remains disabled until Prime consumes this route contract end to end. Heartbeat mechanics still belong outside Relay; the Relay directives/proofs are only the model-routing guardrails Heartbeat will later trigger Prime to ask against.

**Obsidian update status:** This section is the durable Obsidian-facing context update for the current Relay harness state.
