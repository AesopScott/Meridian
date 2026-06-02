# Relay Heartbeat Model Routing Implementation Checklist

**Status:** Build-ready checklist; runtime routing not yet authorized
**Owner harness:** Relay
**Consumes:** Heartbeat attention, Prime intent, Aegis gates, Model Harness metadata, Session Lifecycle, Bifrost visibility
**Source docs:** `docs/relay-heartbeat-model-routing-logic.md`, `docs/relay-completeness-audit.md`, `docs/model-harness-v2-contract.md`, `docs/deepseek-direct-provider-implementation-handoff.md`, `docs/live-codex-reviews-2.md`, `docs/v2-progress-tracker.md`

## Boundary

This checklist turns the reviewed Relay model/vendor/session routing logic into implementation gates. It does not enable Auto routing, add live model calls, probe accounts, start sessions, change Bifrost UI, move branches, or authorize runtime provider work by itself.

Runtime routing remains blocked until every required item below has deterministic implementation, tests, visible proof, and review clearance.

## 1. Account-First Route Intake

- [ ] Implement a Relay intake record that captures `heartbeat_id`, project, surface mode, intent, role, risk tier, proof requirement, human gate, prompt budget, and requested action type before any model route is selected.
- [ ] Evaluate route classes in this order: `account_session`, `local_cli`, `direct_api`, `aggregator_api`.
- [ ] Record the first available route tried, selected route, and every rejected alternative with a concrete reason.
- [ ] Treat account/session availability as insufficient by itself; Relay must also know project scope, role, tool access, context health, steering capability, and proof capture capability.
- [ ] Prefer existing user account/session routes only when they are authenticated, correctly scoped, role-matched, tool-capable, steerable, under context budget, and sufficiently observable for the tier.
- [ ] Skip to API/aggregator fallback only for allowed rejection classes, never silently.

## 2. Wrong-Scope Correction And Blocking

- [ ] If an account/session route has the wrong project, wrong role, or wrong tools, Relay must start a corrected project-specific or role-matched controllable session.
- [ ] If a corrected controllable session cannot be started, Relay must block with a setup/scope reason.
- [ ] Wrong project, wrong role, and wrong tools must not fall through to direct API or aggregator fallback as generic "session rejected" cases.
- [ ] Wrong project must never reuse cross-project context, even for low-tier work.
- [ ] Wrong role may start a role-matched session for low-tier work, but Tier 3+ must block until the corrected session or approved direct route is available.
- [ ] Wrong tools or wrong cwd must block rather than route work to a session that cannot execute or prove the task.

## 3. API, Direct, And Aggregator Fallback Gates

- [ ] Implement fallback only after Relay records why the account/session or CLI route cannot satisfy the job.
- [ ] Allow direct provider API when pinned exact model id, clean prompt packet, audit trail, telemetry, or stronger Tier 3+ proof/control is explicitly required and credentials/quota are valid.
- [ ] For Tier 3+ account session missing or expired, choose exactly one: start/re-auth a controllable session, use direct API for explicit proof/audit needs with valid credentials, or block.
- [ ] Block when API credentials are missing, quota is unavailable for the required route, cost exposure is unclear, or Aegis has not allowed the route.
- [ ] Allow aggregator routes only for low-risk fallback, comparison, or exploration where provider/model identity, cost, data policy, and selected model can be shown.
- [ ] Cap aggregator authority at Tier 2 or lower, and never use an aggregator as an authoritative Tier 3+ lane.
- [ ] For OpenRouter, require an explicit curated allowlist/provider preference for any nontrivial route; `openrouter/auto` is Tier 1 exploration only.
- [ ] If aggregator selected provider/model identity cannot be captured and shown, block.

## 4. Exact Model Identity Requirements

- [ ] Implement registry resolution through the Model Harness exact-id rule: `ProviderCapability.model` is the dispatch key and must match the provider API request value.
- [ ] Treat provider marketing names, version labels, route family names, UI labels, and compatibility aliases as non-dispatch metadata.
- [ ] For DeepSeek direct, register and dispatch `deepseek-chat` as the exact API model id.
- [ ] Treat `deepseek-v4-pro` and `deepseek-v4-flash` only as capability/marketing variant metadata for the `deepseek-chat` route, not as dispatch keys.
- [ ] Block Tier 2+ routing when the exact model id is unknown, unresolved, aliased, or inconsistent between Relay, Model Harness metadata, and Bifrost display.
- [ ] For Claude and OpenAI labels used in routing docs, require the runtime registry to resolve them to current provider-deployable exact ids before enabling dispatch.
- [ ] Add tests that unknown aliases such as `deepseek-v4-pro`, `deepseek-v4-flash`, and marketing-only labels cannot dispatch directly.

## 5. Model Metadata And Trust Binding

- [ ] Add immutable Model Harness metadata for every registered route: `ProviderCapability`, `ModelTrustState`, `AllowedTaskTypes`, and `TelemetryCapability`.
- [ ] Enforce the registration invariant: no adapter without metadata and no metadata without a resolvable adapter.
- [ ] Gate dispatch through allowed action types, blocked action types, max risk tier, trust mode, proof strength, external-review status, blocked authorities, and telemetry support.
- [ ] Treat `TrustMode.UNKNOWN` and `ProofStrength.NONE` as blockers for Tier 2+.
- [ ] Treat non-empty `blocked_authorities` as a dispatch blocker at every tier.
- [ ] Keep credentials, API keys, account internals, and transport details out of prompt context and Bifrost human copy.

## 6. DeepSeek Direct Provider Gates

- [ ] Register DeepSeek direct with endpoint `https://api.deepseek.com/v1/chat/completions`, provider `deepseek`, model `deepseek-chat`, and `trust_mode = DIRECT`.
- [ ] Require `DEEPSEEK_API_KEY` validation before any live call, without logging or surfacing the key.
- [ ] Start DeepSeek in candidate trust: `proof_strength = WEAK`, `external_review_required = True`, `external_review_status = PENDING`.
- [ ] Allow DeepSeek only for Tier 1 `VERIFY` and `EXPLAIN` until external review passes.
- [ ] Block DeepSeek `BUILD`, `REVIEW`, `RELEASE`, and `DESTRUCTIVE` actions while candidate trust holds.
- [ ] Enforce `temperature = 0`, `stream = false`, no cached responses, payload snapshot hash, and response hash for Q-mode verification.
- [ ] Keep DeepSeek direct visibly distinct from DeepSeek through OpenRouter or any other aggregator.

## 7. Dual-Model And External Review Triggers

- [ ] Require independent dual-model lanes for Tier 3 code changes, complex planning, architecture review, provider-sensitive decisions, and other meaningful high-risk work unless an explicit waiver exists.
- [ ] Require Tier 4 human gate plus independent model/human review for preparation only; no autonomous execution.
- [ ] Ensure dual lanes use different vendor/model families except Q-mode flatness self-verification, where same-model duplicate calls are allowed only under the DeepSeek direct Q-mode rules.
- [ ] Block Tier 3+ when only one trusted independent lane is available and no waiver exists.
- [ ] Trigger external Codex/PQA review when a provider moves from candidate to production trust, when DeepSeek seeks Tier 2+ authority, when a route's proof type changes, or when model output quality degrades.
- [ ] Treat external review as asynchronous and blocking for route promotion until the passed evidence is recorded and unexpired.

## 8. Session Lifecycle Decisions

- [ ] Return a `session_action` for every Relay decision: `reuse`, `start_new`, `summarize_and_reset`, `transfer`, `archive`, or `no_session`.
- [ ] Reuse only when project, role, reasoning mode, context health, steering capability, tools, cwd, auth, and user expectation still match.
- [ ] Start a new session when context reaches 70%+ capacity, project changes, role changes, tools/cwd/auth mismatch, session is stale, or context is polluted.
- [ ] Summarize and reset when context is full but continuity matters; include decisions, proof/test status, active project, work type, and excluded stale context.
- [ ] Transfer when work started in the wrong project, wrong role, wrong vendor, or needs a different model family for independent review.
- [ ] Archive completed, superseded, or abandoned sessions with final proof, key decisions, tokens, latency, cost, model, route class, and trust state.
- [ ] Never reuse Settings or Harness mode as generic project chat context.

## 9. Cost, Token, Rate-Limit, And Account Exhaustion Handling

- [ ] Track cost posture as minimal, standard, premium/thorough, unknown, quota-limited, or exhausted before dispatch.
- [ ] Warn before premium routes under cost caution, block or require approval under high/exhausted cost pressure, and never surprise-spend.
- [ ] Track prompt payload status and context budget; warn at filling levels, require summarization/reset near full, and block full sessions.
- [ ] For account quota warning, proceed only if the route remains safe; for quota exhausted, block account routes and use direct API or aggregator only when tier/trust/cost policy allows.
- [ ] For account billing failure or MFA/auth lapse, block account routes and require setup/re-auth unless a valid direct API route is explicitly allowed.
- [ ] Retry rate limits with bounded backoff; persistent rate limits may switch to a safer account/session route or block.
- [ ] Do not cascade through every provider when all trusted routes are rate-limited; block and surface reset timing.

## 10. Block Conditions

Relay must block rather than guess when any of these are unresolved:

- [ ] Risk tier unknown.
- [ ] Route class unknown.
- [ ] Exact model id unknown for Tier 2+.
- [ ] Aegis gate missing or unknown.
- [ ] Proof requirement unknown.
- [ ] Context health unknown for session reuse.
- [ ] Wrong project, role, tools, cwd, or auth cannot be corrected.
- [ ] Tier 3+ cannot get independent lanes and no waiver exists.
- [ ] API credentials, account auth, quota, or cost exposure is missing for the selected route.
- [ ] Aggregator provider/model identity or data policy cannot be shown.
- [ ] DeepSeek remains candidate trust for Tier 2+ or high-risk authority.
- [ ] Silent fallback would reduce trust, change provider, increase cost, or hide proof loss.
- [ ] Relay cannot explain the selection in a structured decision record.

## 11. Bifrost Visibility Requirements

- [ ] Bifrost must show selected vendor, exact model id, route class, route kind, account/API/aggregator source, and session action.
- [ ] Bifrost must show risk tier, proof requirement, human gate, trust state, external-review status, and blocked authorities.
- [ ] Bifrost must show prompt payload size, budget percent, growth delta, context health, token pressure, and prompt-drag warnings.
- [ ] Bifrost must show cost posture, account quota status, rate-limit state, credential/setup blockers, and any fallback reason.
- [ ] Bifrost must show alternatives rejected and why the selected route was chosen.
- [ ] Bifrost must visibly distinguish DeepSeek direct from DeepSeek through aggregator.
- [ ] Bifrost must render Relay logic as deterministic harness/configuration data, not hidden Auto routing or fake completion claims.
- [ ] Auto must remain disabled until the runtime route contract, metadata, Aegis gates, and Bifrost proof display are reviewed and cleared.

## 12. Required Decision Record Shape

- [ ] Runtime Relay decisions must produce a structured record with:

```text
route_id
heartbeat_id
project
surface_mode
intent
role
risk_tier
action_type
selected_vendor
selected_model
route_kind
route_class
session_action
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
alternatives_rejected
observability_fields
telemetry_required
explanation_for_prime
```

- [ ] The decision record must be serializable for Bifrost and review without including raw prompt payload text, credentials, raw provider responses, or full transcripts.

## 13. Tests And Proofs Required Before Runtime Routing

- [ ] Unit tests for account-first precedence and explicit fallback reasons.
- [ ] Unit tests proving wrong project, wrong role, and wrong tools start corrected sessions or block, never direct/aggregator fallback.
- [ ] Unit tests for Tier 3+ account missing/expired choices: start/re-auth, explicit direct API with proof/audit and valid credentials, or block.
- [ ] Unit tests for exact-id registry resolution and alias blocking.
- [ ] Unit tests for metadata registration invariants and dispatch gating error tags.
- [ ] Unit tests for DeepSeek candidate trust, action blocks, Tier 2+ external-review blocks, Q-mode flags, payload hashes, and response hashes.
- [ ] Unit tests for aggregator caps, OpenRouter allowlist/provider preference enforcement, and provider identity visibility.
- [ ] Unit tests for dual-lane required/waived/blocked paths.
- [ ] Unit tests for session lifecycle action selection.
- [ ] Unit tests for cost, token, account exhaustion, and rate-limit routing changes.
- [ ] Snapshot/render tests proving Bifrost displays route, trust, prompt payload, cost, fallback, blockers, and no hidden Auto routing.
- [ ] Integration proof that Relay snapshot generation remains deterministic and does not call live models.
- [ ] Aegis policy tests must pass before any model call path is enabled.
- [ ] Review Console/Codex review evidence must exist before route promotion, especially DeepSeek candidate-to-trusted changes.
- [ ] FileMap registration must be routed for any new runtime module or doc added by implementation lanes.

## 14. Runtime Enablement Gate

Runtime routing may be enabled only after:

- [ ] All metadata and decision-record fields above are implemented.
- [ ] Aegis gates enforce tier, proof, trust, action type, and human gate constraints.
- [ ] Bifrost displays the selected route and blockers from deterministic runtime data.
- [ ] Tests above pass in the owning runtime lanes.
- [ ] Codex review clears the implementation checklist and the runtime implementation.
- [ ] Auto routing remains disabled until Scott or Prime explicitly promotes it after proof review.
