# Relay Dispatch Hardening Implementation Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Owner harnesses:** Relay (dispatch), Model Harness (provider adapter metadata), Aegis (proof policy), Bifrost (visibility)
**Source docs:** `docs/relay-heartbeat-model-routing-implementation-checklist.md`, `docs/relay-prompt-payload-visibility-implementation-checklist.md`, `docs/model-harness-v2-contract.md`, `docs/relay-completeness-audit.md`, `docs/v2-progress-tracker.md`, `docs/live-codex-reviews-2.md`

## Boundary

This checklist defines implementation gates for provider-neutral Relay dispatch hardening and metadata pass-through. It does not edit runtime code, add live model calls, probe accounts, start sessions, wire Bifrost UI, edit FileMap, move branches, touch Polaris, or enable Auto routing.

Dispatch hardening is complete only when Relay can build a deterministic dispatch envelope, validate it against Model Harness metadata and Aegis policy, pass safe metadata through the transport boundary, and expose enough structured state for Bifrost and review without leaking credentials, raw prompts, raw provider responses, or transport internals.

## 1. Provider-Neutral Dispatch Envelope

- [ ] Define a provider-neutral dispatch envelope before any provider adapter is called.
- [ ] Include stable identifiers: `dispatch_id`, `route_id`, `packet_id`, `heartbeat_id` when available, project, surface mode, role, action type, risk tier, and session/lane id when available.
- [ ] Include selected route fields: provider, exact model id, route class, route kind, trust mode, proof strength, external-review status, and blocked authorities.
- [ ] Include prompt payload evidence references: prompt token count, budget status, payload snapshot hash when available, allowed source compliance, and prompt growth state.
- [ ] Include Aegis proof policy references: cognition policy result, proof requirement, human gate, fallback blockers, waiver/approval/evidence references when present.
- [ ] Include transport requirements: streaming allowed, response hash required or optional, snapshot support required or unavailable, timeout/retry policy, and expected output type.
- [ ] Keep the envelope serializable, deterministic, and reviewable without provider-specific request bodies.
- [ ] Do not include raw prompt text, raw provider responses, API keys, account identifiers, billing state details, cookies, auth tokens, or process handles.

## 2. Exact Model Id And Metadata Resolution

- [ ] Resolve every dispatch through `AdapterRegistry.resolve_metadata(exact_model_id)` before transport.
- [ ] Treat `ProviderCapability.model` as the only dispatch key; marketing names, aliases, UI labels, and route family names are metadata only.
- [ ] Block dispatch when exact model id is unknown, aliased, missing from metadata, missing from adapter registration, or inconsistent with the selected provider.
- [ ] Validate provider/model agreement across `ProviderCapability`, `ModelTrustState`, `AllowedTaskTypes`, `TelemetryCapability`, and the resolved adapter.
- [ ] Enforce the registration invariant: no adapter without metadata and no metadata without a resolvable adapter.
- [ ] Preserve DeepSeek exact-id handling: direct DeepSeek dispatch uses `deepseek-chat`; `deepseek-v4-pro` and `deepseek-v4-flash` are variant metadata, not dispatch keys.

## 3. Metadata Pass-Through Fields

- [ ] Pass safe provider capability metadata into Relay decision/audit output: provider, exact model id, context window, max output tokens, cost posture, latency tier, tokenizer family, streaming support, thinking support, Q-mode flatness, and known authorities.
- [ ] Pass safe trust metadata: trust mode, direct API endpoint identity as an audit string when allowed, proof strength, external-review required/status/evidence, blocked authorities, and last validated timestamp.
- [ ] Pass safe allowed-task metadata: allowed action types, blocked action types, max risk tier, and human-readable gate reason.
- [ ] Pass safe telemetry capability metadata: completion-token support, latency support, payload snapshot support, and response hash support.
- [ ] Exclude credential material, request headers, account secrets, raw transport config, raw provider body, and provider account billing details.
- [ ] Keep metadata pass-through immutable or snapshot-like for the dispatch; later registry changes must not mutate prior dispatch audit records.

## 4. Transport Envelope Boundaries

- [ ] Keep provider-specific HTTP wire format inside adapter implementation only.
- [ ] Keep Relay dispatch envelope provider-neutral; adapters may translate it to provider request bodies after gates pass.
- [ ] Allow adapter transport to receive only the approved prompt payload and safe dispatch metadata needed for endpoint/model/options selection.
- [ ] Ensure endpoint selection cannot be overridden by prompt content, UI labels, or aggregator defaults.
- [ ] Ensure direct-provider endpoints remain fixed by adapter metadata or adapter configuration, not runtime prompt text.
- [ ] Ensure aggregator routes carry explicit provider/model preferences or allowlist constraints before transport.
- [ ] Block transport when route kind, route class, trust mode, endpoint identity, or selected provider cannot be represented unambiguously.

## 5. Aegis Proof Policy Hooks

- [ ] Gate every dispatch through Aegis/CognitionPolicy before provider transport.
- [ ] Check action type against `AllowedTaskTypes.allowed_action_types` and `blocked_action_types`.
- [ ] Check risk tier against `AllowedTaskTypes.max_risk_tier`.
- [ ] Check trust mode, proof strength, external-review status, blocked authorities, and human gate requirements.
- [ ] Check prompt payload budget/source compliance and context health before dispatch.
- [ ] Require structured waiver/approval/evidence records where policy allows demotion or continuation.
- [ ] Return explicit error tags for blocked policy paths, never vague boolean failures.
- [ ] Do not let model output become its own proof of dispatch safety.

## 6. Blocked And Error States

- [ ] Define deterministic error tags for dispatch hardening, including `unknown_model_id`, `missing_adapter_metadata`, `metadata_adapter_mismatch`, `disallowed_task_type`, `blocked_task_type`, `risk_tier_exceeded`, `unknown_trust_route`, `blocked_authority`, `external_review_required`, `external_review_failed`, `external_review_expired`, `insufficient_proof_strength`, `prompt_budget_exceeded`, `prompt_snapshot_missing`, `telemetry_unavailable`, `credential_missing`, `quota_unavailable`, `rate_limited`, `transport_timeout`, `provider_identity_unknown`, and `aggregator_without_allowlist`.
- [ ] Preserve all error tags in Relay audit output and Bifrost-visible state.
- [ ] Distinguish pre-dispatch blocks from transport failures and post-response telemetry gaps.
- [ ] Never silently retry with a different provider, model, route class, trust mode, or aggregator provider.
- [ ] Retry only when the retry policy is explicit and does not alter trust/cost/proof posture.
- [ ] Block rather than fallback when fallback would reduce trust, hide provider identity, lose required snapshot proof, exceed cost policy, or bypass Aegis.

## 7. Payload Evidence Propagation

- [ ] Attach prompt payload evidence from the prompt-payload checklist to the dispatch envelope before transport.
- [ ] Preserve prompt token count, budget percent/status, allowed source compliance, payload snapshot hash, growth delta/state, and prompt-drag warning state.
- [ ] Record `adapter_supports_snapshot` and whether snapshot evidence is required, optional, unavailable, or missing.
- [ ] For direct providers, compute or carry prompt and response hashes when supported.
- [ ] For aggregator routes, explicitly mark payload/response snapshots unavailable and cap authority according to risk policy.
- [ ] Surface missing snapshot evidence as a review flag or block according to risk tier and route trust requirements.

## 8. Credential And Raw Prompt Exclusions

- [ ] Exclude API keys, bearer tokens, cookies, OAuth material, account ids, billing identifiers, environment variable values, and local process handles from envelopes, telemetry, Bifrost handoff, and logs.
- [ ] Exclude raw prompt text from Bifrost-visible dispatch state; use packet id, payload size, allowed-source proof, and snapshot hash instead.
- [ ] Exclude raw provider responses from Bifrost-visible dispatch state; use response hash, completion token count, latency, and error tags instead.
- [ ] Redact provider transport errors before they reach user-visible surfaces if they contain secrets, raw headers, or full request/response bodies.
- [ ] Add tests that known secret-like values cannot appear in serialized dispatch audit or Bifrost handoff output.

## 9. Bifrost Visibility Handoff

- [ ] Expose dispatch hardening state as structured data for Bifrost; Bifrost must not reconstruct it by calling Relay internals, Aegis validators, adapters, or provider APIs.
- [ ] Bifrost must show provider, exact model id, route class, route kind, trust state, proof strength, external-review status, and blocked authorities.
- [ ] Bifrost must show prompt payload status, budget status, snapshot availability, telemetry availability, fallback blockers, and dispatch error tags.
- [ ] Bifrost must show direct-vs-aggregator status and actual selected provider/model for aggregator routes when available.
- [ ] Bifrost must show when Auto routing remains disabled and dispatch is blocked, degraded, or review-required.
- [ ] Bifrost must not choose providers, override Aegis gates, approve trust promotion, mutate proof payloads, or hide degraded dispatch state.

## 10. Deterministic Tests And Proof

- [ ] Unit tests for dispatch envelope construction with deterministic field values and stable serialization.
- [ ] Unit tests for exact model id resolution, alias blocking, missing metadata, adapter/metadata mismatch, and DeepSeek `deepseek-chat` dispatch-key handling.
- [ ] Unit tests for metadata pass-through snapshots and immutability.
- [ ] Unit tests for action type, risk tier, trust mode, proof strength, external-review, blocked-authority, and human-gate blocks.
- [ ] Unit tests for prompt payload evidence propagation, over-budget blocks, missing snapshot review flags, and aggregator snapshot-unavailable behavior.
- [ ] Unit tests for retry/fallback rules proving no silent provider/model/trust downgrade.
- [ ] Unit tests for credential/raw prompt/raw response exclusion from serialized audit and Bifrost handoff.
- [ ] Snapshot/render tests proving Bifrost can display dispatch hardening state from structured data only.
- [ ] Scope proof that dispatch snapshot generation does not call live models, probe accounts, start sessions, inspect live processes, edit branches, or touch Polaris.
- [ ] FileMap registration must be routed for any future runtime module, test file, or implementation doc created by implementation lanes.

## 11. Runtime Enablement Gate

Dispatch hardening may be treated as runtime-ready only after:

- [ ] Provider-neutral dispatch envelope exists and is tested.
- [ ] Metadata resolution and pass-through are enforced before transport.
- [ ] Aegis proof policy hooks block unsafe routes before provider calls.
- [ ] Payload evidence propagates through dispatch audit and Bifrost handoff.
- [ ] Credentials, raw prompts, raw responses, and transport internals are excluded from visible/audit surfaces.
- [ ] Bifrost displays dispatch hardening state from structured data.
- [ ] Required tests pass in owning runtime/UI lanes.
- [ ] Codex review clears this checklist and the future runtime implementation.
- [ ] Auto routing remains disabled until routing, payload visibility, dispatch hardening, Aegis policy, and Bifrost proof display are reviewed together.
