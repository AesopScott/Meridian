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
