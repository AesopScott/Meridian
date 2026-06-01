# Relay Heartbeat Model Routing Logic

**Status:** Draft routing logic
**Date:** 2026-06-01
**Owner harness:** Relay
**Consumes:** Heartbeat attention, Prime intent, Aegis risk/proof gates, Model Harness metadata

## Purpose

When the heartbeat sends Prime's attention to Relay, Relay answers:

- What model should Prime talk to?
- What vendor or route should Prime use?
- What are the risks of using that model or route?
- What evidence is needed before Relay can promote, demote, or block a route?

This document is the first model/vendor routing list for Meridian. It is not runtime code and does not grant Auto routing yet.

## Routing Principles

1. Prime owns the decision intention.
2. Relay owns model/vendor route selection.
3. Aegis owns proof and risk gates.
4. Bifrost displays the routing state; it does not choose.
5. Existing user account/session routes are preferred before paid/direct API routes when they can satisfy the job safely.
6. Direct provider APIs are preferred for high-trust work when account/session routes are unavailable, unsuitable, or insufficiently controllable.
7. Aggregator routes are useful but lower-trust unless separately proven.
8. DeepSeek direct is a candidate primary route, not automatically trusted.
9. Auto routing stays disabled until Relay logic, metadata, and proof are implemented.

## Top-To-Bottom Relay Flow

| Step | Relay Question | Logic |
|---|---|---|
| 1 | What is Prime trying to do? | Read Prime intent: plan, build, review, verify, summarize, research, route, voice, or explain. |
| 2 | What project and surface is active? | Read active project, right-panel mode, selected session/harness/settings surface, and user-visible gate. |
| 3 | What is the risk tier? | Ask Aegis/Risk: Tier 0-4, human gate required, proof required, account/public/destructive sensitivity. |
| 4 | What context shape is needed? | Choose focused packet, reuse session, summarize-and-reset, large context, or no model. |
| 5 | What role is needed? | Choose role: orchestrator, builder, reviewer, verifier, researcher, release operator, voice, or classifier. |
| 6 | Should this reuse a session or start a new one? | Reuse only when context is healthy and the reasoning mode still matches. Start new when context is filling, polluted, stale, or the work type shifts. |
| 7 | What model class fits? | Match role/risk/context to model family: highest reasoning, coding, fast cheap, independent review, voice, or fallback. |
| 8 | What access route should be tried first? | Prefer existing account/session routes, then direct APIs, then aggregator routes if risk allows. |
| 9 | What vendor route is safest? | Prefer direct provider API for Tier 3+ when account/session route cannot satisfy control/proof needs. Use aggregator only when risk allows and fallback/coverage matters. |
| 10 | What does the budget allow? | Check account quota, API cost posture, token budget, context pressure, and prompt payload size. |
| 11 | Is there a trust block? | Block routes with unknown trust, failed/expired review, prompt-drag degradation, route mismatch, or missing metadata. |
| 12 | Is dual-lane needed? | Tier 3 requires independent dual-model lanes; Tier 2 uses dual lane when meaningful work or review warrants it. |
| 13 | What should Prime see? | Return selected route, reason, risk notes, alternatives rejected, and proof requirements. |
| 14 | What should Bifrost show? | Show model/vendor, account/API/aggregator route, trust state, cost pressure, payload size, and warning state. |

## Risk Tier Routing Defaults

| Tier | Default Route Logic | Notes |
|---|---|---|
| Tier 0 | No model call. Deterministic local logic only. | Formatting, local checks, known state. |
| Tier 1 | Fast/cheap single lane allowed. Account/session route first; aggregator allowed if metadata is clear. | Low-risk drafting, summarization, classification. |
| Tier 2 | One primary lane plus independent review lane when meaningful work warrants it. Account/session route first; aggregator allowed for review/exploration, not authority. | Meaningful but reversible work. |
| Tier 3 | Independent dual-model lanes required. Prefer account/session routes first, then direct APIs if proof/control requires them. Aggregator cannot be authoritative. | Code changes, complex planning, provider-sensitive decisions. |
| Tier 4 | Human gate required plus independent model review for preparation. Prefer account/session routes where controllable, direct provider APIs for audit/proof; no autonomous execution. | Public, financial, destructive, account-risking, policy-sensitive. |

## Access Route Precedence

Relay should not jump to raw APIs when an existing user account or session route can do the job safely. The preferred route order is:

| Priority | Route Class | When To Use | When To Skip |
|---|---|---|---|
| 1 | Existing user account/session | The user is already logged in, the vendor session has the right tools/context, and Relay can capture enough metadata/proof. | Skip if session context is bloated, stale, polluted, wrong role, wrong project, missing proof metadata, or cannot be steered safely. |
| 2 | Local CLI-backed route | Codex/Claude CLI or similar account-backed local route can execute with known working directory and recoverable transcript. | Skip if CLI missing, unauthenticated, wrong cwd, wrong session identity, or cannot satisfy risk/proof gates. |
| 3 | Direct provider API | Need pinned model id, clean prompt packet, auditability, direct endpoint, structured telemetry, or stronger trust for Tier 3+. | Skip if account/session route is safer and sufficiently observable, or if API credentials/quota are unavailable. |
| 4 | Aggregator API | Need fallback, model availability, low-risk comparison, or exploratory routing. | Skip for authoritative Tier 3+, high-risk work, unknown data policy, model identity uncertainty, or unbounded cost. |

The route chosen must be visible as `route_class: account_session | local_cli | direct_api | aggregator_api`.

## Session Lifecycle Routing

Relay must decide whether to reuse a session, start a new session, summarize/reset, or transfer work. This is part of routing, not cleanup.

| Signal | Relay Decision | Reason |
|---|---|---|
| Context window filling or prompt payload over budget | Summarize important state and start a new session. | Prevent prompt drag and context collapse. |
| Session context polluted by unrelated work | Start a new focused session. | Avoid contaminating reasoning and model output. |
| Reasoning type shifts, such as planning to coding or coding to review | Start or switch to a role-appropriate session/model. | Different work needs different tools, instructions, and model strengths. |
| Project changes | Use project-specific orchestrator/session context; do not reuse cross-project context silently. | Prevent project bleed. |
| User moves from User Session mode to Settings mode | Preserve user session; use Settings configuration surface, not the old prompt context. | Keep configuration separate from project work. |
| User moves to Harness mode | Preserve previous user session; use selected harness logic list. | Harness logic updates are not general project chat. |
| Long-running session with healthy context and same role | Reuse session. | Preserve continuity when it is still useful. |
| Session hits tool/auth/cwd mismatch | Start corrected session or block with setup warning. | Avoid sending work to a broken or wrong environment. |
| Review finds defect in build output | Start repair or reviewer-specific lane, not necessarily the original builder session. | Use the right role for the next action. |
| Tier 3+ decision requires independence | Start independent second lane with different vendor/model family. | Reduce shared blind spots. |

## Vendor And Model Set

### Anthropic Direct

Use Anthropic direct routes when high-quality reasoning, long-context work, agentic coding, and human-readable collaboration matter.

| Model | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `claude-opus-4-8` | Highest-complexity reasoning, long-horizon architecture, difficult code review, strategic planning. | Prefer for Tier 3-4 preparation, complex harness design, independent deep review, and long-context synthesis. | Premium cost and slower latency. Use when value justifies cost. Human gate still required at Tier 4. |
| `claude-sonnet-4-6` | General builder/reviewer lane, strong coding, balanced speed/intelligence. | Default Anthropic workhorse for build/review when direct Claude route is available. | Still requires proof for code changes; may not be cheapest. |
| `claude-haiku-4-5` | Fast classification, short summaries, extraction, lightweight review, heartbeat triage. | Use for low-risk fast lane or preprocessing where near-frontier intelligence is enough. | Not default for high-risk planning or complex code authority. |

### OpenAI Direct

Use OpenAI direct routes when Codex/coding strength, professional reasoning, structured outputs, voice/audio, or OpenAI tool compatibility matter.

| Model / Family | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `GPT-5.3-Codex` | Agentic coding, codebase changes, refactors, debugging, security/correctness repair. | Prefer for Codex-style build/review lanes and repository work when direct OpenAI route is available. | Requires code proof and Aegis review for meaningful changes. |
| `GPT-5.2` / `GPT-5.2 pro` | Professional reasoning, planning, synthesis, difficult non-code work. | Use for high-quality planning/reasoning lane or independent comparison against Claude. | Cost/latency pressure. Verify exact API id through model registry before enabling. |
| `GPT-5.3 Chat` / latest Chat family | Conversational planning, user-facing explanation, general reasoning. | Use for Prime-facing conversational lane when OpenAI direct is selected. | Do not treat Chat route as code-authority without proof. |
| `gpt-realtime-*` / `gpt-audio-*` families | Voice input/output, spoken interaction with Spark/Prime. | Candidate for first-class speech/voice once voice layer is wired. | Voice privacy, mic permissions, cost, and transcript handling need gates. |
| Embedding models | Atlas/Echo retrieval support. | Use for retrieval/indexing when Atlas/Echo needs embeddings. | Not a reasoning route; do not use as Prime response model. |

### DeepSeek Direct

Use DeepSeek direct when cost-efficient reasoning, Q-mode flatness, and direct API validation are desired. DeepSeek direct must remain visibly distinct from DeepSeek through OpenRouter.

| Model | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `deepseek-v4-pro` | High-reasoning direct DeepSeek lane, comparison lane, cost-aware reasoning, structured outputs. | Candidate for Tier 1-2 reasoning/review; promote only after validation. | Candidate trust until external validation. Do not grant autonomous code authority without proof. |
| `deepseek-v4-flash` | Fast/cheap direct DeepSeek lane, Q-mode checks, classification, bounded summaries. | Use for low-risk fast lane and heartbeat/Q-mode checks if prompt payload stays flat. | Watch prompt-drag. Candidate trust until validation. |
| `deepseek-chat` | Compatibility alias only. | Do not choose for new routes; maps to non-thinking `deepseek-v4-flash`. | Deprecated on 2026-07-24. |
| `deepseek-reasoner` | Compatibility alias only. | Do not choose for new routes; maps to thinking `deepseek-v4-flash`. | Deprecated on 2026-07-24. |

### OpenRouter Aggregator

Use OpenRouter as an aggregator route for coverage, fallback, model comparison, and low-risk exploration. It is not the same trust class as a direct provider API.

| Route / Model Set | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `openrouter/auto` | Low-risk exploratory routing when Relay wants a quick external choice. | Tier 1 only until Meridian can audit selected model, provider, cost, and data policy. | Auto chooses outside Meridian. Must show selected model and cost. Not for authoritative work. |
| Curated OpenRouter allowlist | Independent review, fallback when direct provider unavailable, access to provider/model variants. | Use only from an explicit allowlist generated from OpenRouter's model catalog. | Aggregator trust: provider fallback, data retention, model identity, and endpoint mismatch risk. |
| OpenRouter provider preferences | Force or deny providers, disable fallbacks, require supported parameters, deny data collection where available. | Relay must set provider preferences for any nontrivial OpenRouter route. | Defaults may route differently than expected; show actual provider/model used. |

## Initial Preferred Routing Logic

| Situation | Preferred Route | Backup / Independent Lane | Reason |
|---|---|---|---|
| Prime planning with high ambiguity | Anthropic `claude-opus-4-8` | OpenAI `GPT-5.2 pro` or `GPT-5.2` | Highest reasoning and synthesis. |
| Routine project planning | Anthropic `claude-sonnet-4-6` | OpenAI latest Chat/Reasoning route | Balanced intelligence/cost. |
| Repository coding/build lane | OpenAI `GPT-5.3-Codex` | Anthropic `claude-sonnet-4-6` | Codex route for code, Claude for independent reasoning/review. |
| Deep code review / architecture review | Anthropic `claude-opus-4-8` | OpenAI `GPT-5.3-Codex` | Different model families reduce shared blind spots. |
| Fast triage / heartbeat summary | Anthropic `claude-haiku-4-5` or DeepSeek `deepseek-v4-flash` | None or OpenRouter low-risk route | Fast, low-cost, bounded context. |
| Cost-sensitive reasoning | DeepSeek `deepseek-v4-pro` | Claude/OpenAI reviewer if action matters | Candidate direct route with proof before authority. |
| Voice/Spark interaction | OpenAI realtime/audio family | Later voice provider fallback | OpenAI has first-class audio/realtime model families. |
| Low-risk external fallback | Curated OpenRouter route | Direct provider when available | Aggregator useful for uptime/coverage, not authority. |

## Route Risk Register

| Risk | Applies To | Relay Behavior |
|---|---|---|
| Unknown exact model id | Any vendor | Query provider model registry before enabling route. |
| Aggregator route mismatch | OpenRouter | Show actual model/provider; cap authority; prefer direct for Tier 3+. |
| Cost surprise | Opus/pro/auto routes | Require cost posture, warn on premium route, expose Balance surface. |
| Prompt drag | All model calls, especially Q-mode | Require prompt payload snapshot and growth delta. |
| Data retention / provider policy | OpenRouter and some direct routes | Prefer direct/ZDR/deny-data-collection where available; surface policy state. |
| Missing CLI/API key/login | Local Codex/Claude and direct APIs | Show setup guidance; do not silently fall back to another route. |
| Account/session route unavailable | Account-backed routes | Fall through to next route class only if risk allows and fallback is shown to Prime/user. |
| Context nearly full | All session routes | Summarize and start new role-appropriate session. |
| Reasoning-mode mismatch | Reused sessions | Start or switch session/model for the new role. |
| Cross-project context bleed | Reused sessions | Block reuse and start project-specific session. |
| Unvalidated DeepSeek route | DeepSeek direct or aggregator | Candidate trust; external validation required before high-risk authority. |
| Model identity drift | OpenRouter / aliases | Prefer pinned model IDs or registry snapshots for high-risk work. |
| Voice privacy | Realtime/audio routes | Visible mic state, permission check, transcript policy. |

## Relay Output Shape

Every Relay decision should return a structured explanation:

```text
route_id
heartbeat_id
project
surface_mode
intent
risk_tier
role
selected_vendor
selected_model
route_kind: direct | aggregator | local_cli
route_class: account_session | local_cli | direct_api | aggregator_api
session_action: reuse | start_new | summarize_and_reset | transfer | no_session
reason
alternatives_rejected
cost_posture
trust_state
proof_required
human_gate_required
prompt_payload_budget
telemetry_required
```

Runtime checkpoint: `meridian_core/relay.py` now carries the first typed
`RelayRouteAudit` slice for these answers. It records route kind/class,
account-session-first precedence, session lifecycle action, trust state,
alternatives rejected, fallback blockers, proof requirements, and telemetry
requirements. It remains deterministic metadata only: it does not enable Auto
routing, wire vendors, or add routing audit text to model payloads.

## Promotion Rules

A model/vendor route can move from candidate to trusted only when:

1. Provider/model id is current and verified from the provider registry.
2. Endpoint route is known: direct or aggregator.
3. Allowed task types are explicit.
4. Risk-tier cap is explicit.
5. Prompt payload telemetry exists.
6. Cost posture is known or marked unknown.
7. Aegis has a proof policy for the route.
8. External review passes where required.

## Immediate Product Implications

- Relay harness panel should show logic items, not a chat prompt.
- Models surface should show these model/vendor route options and trust states.
- Balance surface should show cost, quota, payload, and trust pressure.
- Filter surface should control what context Relay includes.
- Auto mode remains disabled until this logic has runtime metadata and proof.

## Source Anchors

- Anthropic Claude model overview: https://platform.claude.com/docs/en/about-claude/models/overview
- OpenAI model list: https://developers.openai.com/api/docs/models/all
- DeepSeek API quick start and model ids: https://api-docs.deepseek.com/
- OpenRouter model catalog API: https://openrouter.ai/docs/api/api-reference/models/get-models
- OpenRouter Auto Router: https://openrouter.ai/docs/guides/routing/routers/auto-router
- OpenRouter provider routing: https://openrouter.ai/docs/features/provider-routing
