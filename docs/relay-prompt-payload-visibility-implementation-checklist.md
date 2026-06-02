# Relay Prompt Payload Visibility Implementation Checklist

**Status:** Build-ready checklist; runtime/UI implementation not authorized by this doc
**Owner harnesses:** Relay (dispatch evidence), Bifrost (display), Model Harness (telemetry capability), Aegis (policy/proof gates)
**Source docs:** `docs/relay-bifrost-proof-payload-contract.md`, `docs/bifrost-balance-payload-surface-contract.md`, `docs/relay-heartbeat-model-routing-implementation-checklist.md`, `docs/model-harness-v2-contract.md`, `docs/v2-progress-tracker.md`, `docs/live-codex-reviews-2.md`

## Boundary

This checklist defines what implementation lanes must build before prompt payload visibility can be treated as runtime evidence. It does not add live model calls, change Bifrost UI, probe provider balances, edit FileMap, start sessions, move branches, or enable Auto routing.

The implementation goal is simple: every Relay dispatch, queue/Q-mode prompt, and review/model prompt must have structured payload evidence that Bifrost can display without calling Relay internals or inferring hidden state.

## 1. Relay Payload Evidence Record

- [ ] Add or bind a Relay-side payload evidence record for every dispatch candidate before the model call boundary.
- [ ] Include the prompt source: `relay`, `queue_q_mode`, `review`, `manual`, or `unknown`.
- [ ] Include stable route context: `route_id`, `heartbeat_id` when available, project, lane/session id when available, selected provider, selected model, route class, and route kind.
- [ ] Include payload sizing fields: estimated prompt tokens, prompt budget tokens, model context window tokens, max output tokens when known, and remaining context tokens.
- [ ] Include budget state: `budget_percent`, `budget_status`, `budget_compliant`, and `over_budget_reason`.
- [ ] Include growth fields: previous prompt tokens, delta tokens, delta percent, comparison scope, and reason for expected growth when growth is intentional.
- [ ] Include telemetry/snapshot fields from Model Harness when available: `prompt_payload_snapshot_hash`, `response_payload_snapshot_hash`, `adapter_supports_snapshot`, `supports_completion_tokens`, `supports_latency_ms`, `supports_payload_snapshot`, `supports_response_hash`.
- [ ] Include Aegis proof payload keys when relevant: `gate_decision`, `severity`, `evidence_ids`, `waiver_present`, `explanation`, and `fallback_blockers_from_aegis`.
- [ ] Keep raw prompt text, raw provider responses, credentials, API keys, account internals, and full transcripts out of the visible payload evidence record.

## 2. Budget Percent And Display Labels

- [ ] Compute `budget_percent` deterministically as prompt tokens divided by the applicable prompt/context budget.
- [ ] Preserve both the raw numeric value and a display-ready rounded value for Bifrost.
- [ ] Use `(under 1k)` when prompt tokens are below 1000.
- [ ] Use `(N.Nk)` for known prompt sizes at or above 1000 tokens, rounded to one decimal place.
- [ ] Use `(over budget)` when prompt tokens exceed the selected budget.
- [ ] Use `(unknown)` only when Relay cannot estimate prompt tokens; unknown is a warning or blocker depending on risk tier.
- [ ] Do not let Bifrost recalculate labels from raw prompt text; Bifrost displays the structured label and numeric fields supplied by Relay/Model Harness telemetry.

## 3. Growth Delta, Watch, And Degraded States

- [ ] Track prompt growth against the previous prompt in the same lane/session/source scope.
- [ ] Mark growth state as `flat`, `growing_expected`, `growing_unexpected`, `over_budget`, or `unknown`.
- [ ] Mark watch state as `ok`, `watch`, `degraded`, or `blocked`.
- [ ] Enter `watch` when payload growth is nonzero but explained by a task-changing event, new evidence, or bounded summary expansion.
- [ ] Enter `degraded` when payload grows across repeated idle/read-check/Q-mode polls without a task-changing reason.
- [ ] Enter `blocked` when payload is over budget, context health is unknown for Tier 2+, or Relay cannot explain unexpected growth.
- [ ] Preserve growth evidence as structured telemetry so Prime can see whether prompt drag is improving, stable, or worsening.

## 4. Queue And Q-Mode Prompt-Drag Detection

- [ ] Treat queue/Q-mode prompts as first-class payload sources, not invisible background checks.
- [ ] For repeated queue polls, send only the current task or bounded delta unless a recorded reason justifies more context.
- [ ] Detect additive prompt growth across idle checks, read-check-only loops, or unchanged task state.
- [ ] Mark queue/Q-mode additive growth as `degraded` until Relay proves prompts are flat or bounded.
- [ ] For DeepSeek Q-mode, require direct route metadata, `q_mode_flat = True`, `temperature = 0`, no cached responses, and payload snapshot support before treating duplicate checks as flatness proof.
- [ ] If a DeepSeek Q-mode prompt is expected to use direct DeepSeek but telemetry shows an aggregator/OpenRouter route, emit a route mismatch warning.
- [ ] Read-check-only activity must not count as productive work and must not hide prompt growth.

## 5. Relay Evidence Requirements

- [ ] Relay must attach prompt payload evidence to the dispatch decision record before dispatch proceeds.
- [ ] Relay must record whether the payload was measured, estimated, unavailable, or blocked.
- [ ] Relay must record which tokenizer family or counting method was used.
- [ ] Relay must record the allowed prompt sources from the budget plan and whether the payload complied with source limits.
- [ ] Relay must record missing telemetry as explicit error tags, such as `telemetry_unavailable`, `budget_exceeded`, `prompt_snapshot_missing`, `context_window_unknown`, or `growth_unexplained`.
- [ ] Relay must surface missing direct-provider snapshots as a review flag; for aggregator routes, it must show snapshots as unavailable rather than silently absent.
- [ ] Relay must never let successful model output stand in for payload evidence.
- [ ] Relay must block or demote routes according to Aegis/risk policy when payload evidence is missing, unknown, over budget, or unexpectedly growing.

## 6. Bifrost Visibility Handoff

- [ ] Bifrost must receive a structured view-model handoff; it must not call Relay executor methods or Aegis validators to reconstruct payload state.
- [ ] Bifrost must display current prompt label, estimated tokens, budget percent, prompt budget, context budget, growth delta, growth state, and watch/degraded/block state.
- [ ] Bifrost must display the producer: Relay, queue/Q-mode, review, or manual prompt.
- [ ] Bifrost must show evidence references to payload snapshot, telemetry, Aegis proof payload, and adapter metadata when available.
- [ ] Bifrost must show provider/model, trust state, route class, route kind, direct-vs-aggregator status, and DeepSeek candidate/direct/aggregator distinction.
- [ ] Bifrost must show missing prompt snapshot evidence, missing provider metadata, unknown routing owner, and Aegis dispatch blocks as visible warnings.
- [ ] Bifrost must not hide prompt growth to keep the UI clean.
- [ ] Bifrost must not decide routing, approve DeepSeek trust promotion, call vendor billing APIs, or mutate proof payloads.

## 7. Provider Balance Surface Binding

- [ ] Bind payload evidence into `ProviderBalanceView` without making provider balance display a routing authority.
- [ ] Populate provider fields where known: provider id, display name, model name, trust state, health, context budget tokens, prompt budget tokens, current prompt tokens, prompt budget percent, prompt delta tokens, cost pressure, quota state, and short notes.
- [ ] Use `unknown` for unavailable balance/quota fields unless a trusted source explicitly provides them.
- [ ] Treat quota/cost unknown during active dispatch as a warning state.
- [ ] Keep provider remaining credit visible only when explicitly available from a trusted source.
- [ ] Preserve evidence refs for telemetry, adapter metadata, budget snapshot, and user override when present.

## 8. Block Conditions

Relay or downstream implementation must block, demote, or raise Review Console evidence when:

- [ ] Prompt token estimate is unknown for Tier 2+ dispatch.
- [ ] Prompt payload exceeds budget and no approved summarization/reset exists.
- [ ] Payload source lineage violates the budget plan's allowed sources.
- [ ] Context window tokens are unknown for the selected model.
- [ ] Exact model id is unknown, aliased, or inconsistent with Model Harness metadata.
- [ ] Direct-provider snapshot support is expected but missing.
- [ ] Aggregator route is used for work that requires payload snapshot evidence.
- [ ] Queue/Q-mode payload grows without a task-changing reason.
- [ ] DeepSeek Q-mode is not flat, not direct, not temperature-zero, or lacks snapshot proof.
- [ ] Aegis gate evidence is missing for work whose risk tier requires it.
- [ ] Bifrost cannot show prompt payload state, provider/trust state, or blockers from structured data.

## 9. Tests And Proof Expectations

- [ ] Unit tests for prompt label formatting: `(under 1k)`, `(N.Nk)`, `(over budget)`, and `(unknown)`.
- [ ] Unit tests for budget percent calculation, rounding, over-budget detection, and unknown-budget handling.
- [ ] Unit tests for payload evidence field stability and serialization without raw prompt text.
- [ ] Unit tests for growth delta and watch/degraded/block transitions.
- [ ] Unit tests for queue/Q-mode additive prompt growth detection across repeated idle/read-check prompts.
- [ ] Unit tests proving read-check-only loops do not mask prompt drag.
- [ ] Unit tests for DeepSeek Q-mode direct route, flatness, temperature-zero, snapshot availability, and aggregator mismatch warnings.
- [ ] Unit tests for missing telemetry error tags and missing snapshot review flags.
- [ ] Unit tests for Aegis proof payload keys flowing into Relay/Bifrost evidence without mutation.
- [ ] Snapshot/render tests proving Bifrost displays prompt label, tokens, budget percent, growth delta, degraded state, provider trust, route class, and blockers.
- [ ] Scope tests or review proof showing snapshot generation does not call live models, vendor billing APIs, account probes, or process/session controls.
- [ ] FileMap registration must be routed for any new runtime module, test file, or implementation doc added by future lanes.

## 10. Runtime Enablement Gate

Prompt payload runtime visibility may be treated as implemented only after:

- [ ] Relay emits structured payload evidence for every dispatch and Q-mode prompt.
- [ ] Model Harness metadata declares tokenizer/context/telemetry capability for every registered route.
- [ ] Aegis gates can block or demote missing, over-budget, or degraded payload evidence.
- [ ] Bifrost renders payload state from structured handoff data without making routing decisions.
- [ ] Tests above pass in the owning runtime/UI lanes.
- [ ] Codex review clears both this checklist and the future runtime implementation.
- [ ] Auto routing remains disabled until the routing checklist, payload visibility, Aegis gates, and Bifrost proof display are reviewed together.
