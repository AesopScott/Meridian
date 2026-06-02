# Provider Result Validation Evidence Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Relay (post-transport evidence), Model Harness (adapter metadata), Aegis (policy gates), Bifrost (display)
**Scope:** Provider-return / adapter-result metadata summaries without raw response leakage

---

## Purpose

Define the next Relay post-transport validation evidence surface: how provider-return and adapter-result metadata should be summarized after a model adapter returns, without exposing raw provider responses, credentials, provider account state, live calls, or transport internals. This checklist follows the provider transport metadata pass-through slice by specifying the display-safe result side of the same boundary.

This is docs-only. It does not edit runtime code, tests, FileMap, Bifrost UI, provider credentials, model/account/process code, branches, shared main, pushes to main, or Polaris.

---

## Result Boundary

- [ ] Adapter/provider transport still returns model text to Relay, but post-transport evidence stores only metadata summaries and display-safe hashes/ids.
- [ ] Raw provider response bodies, raw HTTP envelopes, headers, credentials, account identifiers, billing/quota payloads, process ids, session-control state, branch/worktree state, shared-main paths, pushes to main, and Polaris references are never stored in result evidence.
- [ ] Relay result evidence is derived from adapter-declared metadata, prompt payload evidence, transport disposition, and safe output measurements.
- [ ] Provider-return metadata must never be appended to future prompts as prose.
- [ ] Any post-transport summary is deterministic for the same adapter metadata, dispatch envelope, prompt payload snapshot, and safe output measurement inputs.

---

## Provider-Return Metadata Summary

Future runtime work should produce a narrow post-transport evidence record per lane:

- [ ] `result_evidence_id`, heartbeat id, lane id, role, and route id.
- [ ] Provider id, exact model id, provider route kind, trust state, trust mode, proof strength, and capability tier.
- [ ] Direct endpoint evidence ref or aggregator evidence ref, copied from pre-transport metadata rather than recomputed from response text.
- [ ] Model metadata ref, validation evidence ref, and external-review evidence ref.
- [ ] External-review requirement and status at dispatch time.
- [ ] Prompt payload evidence ref, prompt payload snapshot hash, packet hash, and prompt budget ref when available.
- [ ] Output length, normalized output hash, and response hash availability/status, without raw output text or raw provider response bodies.
- [ ] Completion-token count, total-token count, latency bucket, and adapter telemetry support flags when available.
- [ ] Result validation status: `valid`, `warning`, `degraded`, `blocked`, or `unknown`.
- [ ] Deterministic warning/blocker tags and retry/demotion/human-gate requirements.

---

## Exact Model And Route Continuity

- [ ] Post-transport evidence preserves the exact model id used before transport.
- [ ] Provider-return model id, when available as safe metadata, must match the pre-transport exact model id.
- [ ] Provider marketing names, aliases, capability labels, lane labels, and variant labels remain display metadata only.
- [ ] DeepSeek direct result evidence must preserve `deepseek-chat` as the exact dispatch id; `deepseek-v4-pro` and `deepseek-v4-flash` remain variant labels only.
- [ ] Route kind, trust state, proof refs, and external-review state must not be changed by a successful provider result.
- [ ] Any mismatch between pre-transport metadata and provider-return safe metadata emits a deterministic `result_route_mismatch` / `result_model_id_mismatch` blocker.

---

## Prompt-Drag And Budget Continuity

- [ ] Result evidence carries forward prompt token estimate, context budget, prompt payload budget, budget percent/status, growth tokens/percent, and prompt-drag tags from pre-transport evidence.
- [ ] Result evidence adds only safe post-transport measurements, such as completion tokens, total tokens, latency bucket, response hash status, and output length.
- [ ] Missing or unsupported completion-token telemetry emits a warning tag; it must not invent token counts.
- [ ] Missing response hash support emits a warning tag when policy needs response integrity evidence.
- [ ] Over-budget, degraded prompt-drag, missing prompt snapshot, or invalid budget state remains visible after transport and may still fail closed for review/promotion.
- [ ] Result evidence must not include raw prompt text, raw source snippets, raw provider request bodies, raw provider responses, or raw model output text.

---

## External Review And Trust Gates

- [ ] Candidate trust remains candidate after a successful provider result.
- [ ] Successful output cannot promote provider trust, clear external review, clear blocked authorities, or authorize a higher risk tier.
- [ ] Pending, failed, expired, missing, or malformed external-review state remains a blocker for review-required tiers/actions.
- [ ] Review-cleared states require structured validation evidence and a review evidence id, not provider self-reporting.
- [ ] Result evidence records whether the post-transport result is usable for the current lane only; it does not grant review-clearing, branch/worktree movement, autonomous coding, process/session control, shared-main write, push-to-main, or Relay/Aegis bypass authority.

---

## Fail-Closed Behavior

Relay/Aegis should fail closed or mark result evidence unusable when:

- [ ] Provider-return safe metadata is missing where policy requires it.
- [ ] Exact model id, provider id, route kind, trust state, or proof refs disagree with pre-transport metadata.
- [ ] Response hash is required but unavailable or malformed.
- [ ] Completion-token telemetry is required but unavailable or malformed.
- [ ] Adapter result is empty, non-string where a string is required, or tagged with a transport error.
- [ ] Result evidence tries to carry raw response text, credentials, provider headers, account state, process/session-control state, branch/worktree data, shared-main paths, push-to-main data, or Polaris references.
- [ ] External review is required but not passed for the selected tier/action.
- [ ] Prompt-drag/budget evidence remains degraded or over budget in a policy-blocking way.

Fail-closed output should preserve deterministic blocker tags, warning tags, and evidence refs for Relay, Aegis, Bifrost, and review lanes.

---

## Relay And Aegis Binding

- [ ] Relay creates result validation evidence after adapter return and before any result is promoted into summaries, proof trails, Bifrost display, retry/fallback logic, or future prompts.
- [ ] Relay binds pre-transport metadata envelope refs to post-transport result evidence.
- [ ] Aegis receives exact model id, route kind, trust state, proof refs, external-review state, prompt-drag state, response hash status, telemetry availability, result validation status, and blocker/warning tags.
- [ ] Aegis treats missing or unsafe result metadata as policy input, not optional display data.
- [ ] Retry, fallback, demotion, and human-gate decisions require fresh pre-transport metadata validation plus fresh post-transport result validation for the new attempt.
- [ ] Model output content never becomes proof that the provider route, trust state, or external review gate is valid.

---

## Bifrost Display Expectations

Bifrost should receive display-safe result validation state only:

- [ ] Provider id, exact model id, route kind, trust state, capability tier, and safe variant/lane labels.
- [ ] Direct-vs-aggregator proof refs and route/result mismatch warnings.
- [ ] External-review requirement/status/evidence ref.
- [ ] Prompt payload budget/status/growth and prompt-drag tags.
- [ ] Output length, response hash status, completion-token availability, total-token availability, and latency bucket.
- [ ] Result validation status, fail-closed blockers, warnings, retry/demotion/human-gate state, and evidence refs.

Bifrost must not display raw provider responses, raw model output text, raw prompts, credentials, provider headers, account/billing payloads, process/session-control data, branch/worktree data, shared-main paths, push-to-main data, or Polaris references. It must not choose providers, approve trust promotion, call provider/account APIs, call Relay dispatch helpers, call Aegis evaluators, or mutate metadata.

---

## Deterministic Test Expectations

Future runtime implementation should add focused tests for:

- [ ] Result evidence serialization is stable and display-safe.
- [ ] Raw provider responses and raw model output text are absent or redacted from result evidence and Bifrost-facing dictionaries.
- [ ] Exact model id, provider id, route kind, trust state, direct/aggregator proof refs, external-review status, and prompt-drag fields carry through from pre-transport metadata.
- [ ] Safe provider-return model metadata mismatch fails closed.
- [ ] Candidate trust and pending external review remain blockers after successful adapter return.
- [ ] Response hash support/unavailability maps to deterministic tags.
- [ ] Completion-token and total-token telemetry support/unavailability maps to deterministic tags.
- [ ] Empty/invalid adapter result and transport-error result evidence produce deterministic blockers.
- [ ] Relay/Aegis receive result validation evidence before proof-trail promotion, Bifrost display, retry/fallback, or future prompt assembly.
- [ ] Sentinel raw prompt, raw provider response, credential, account, process/session-control, branch/worktree, shared-main, push-to-main, and Polaris strings are absent.
- [ ] Tests use fakes/fixtures only and do not perform live provider calls, credential/account probing, or process/session control.

---

## Explicit Exclusions

This checklist does not authorize:

- Live provider calls or live model validation.
- Credential discovery, provider billing calls, account probing, quota scraping, or provider account mutation.
- Raw prompt text, raw source text, raw provider request body, raw provider response, raw model output text, credential, request/response header, account identifier, process/session-control, branch/worktree, shared-main, push-to-main, or Polaris exposure.
- Runtime code changes, runtime tests, Relay runtime wiring, Bifrost UI implementation, FileMap edits, process/session control, branch movement, merge/rebase/reset/cherry-pick/stash-pop, shared-main writes, pushes to main, or Polaris work.

---

## Runtime Enablement Gate

Provider result validation evidence work is ready only after:

- This checklist clears Codex review.
- Pre-transport metadata pass-through is review-cleared.
- Relay result evidence is implemented as a pure provider-neutral structure.
- Relay validates result evidence before proof-trail promotion, Bifrost display, retry/fallback, or prompt reuse.
- Aegis consumes result blockers/warnings as policy inputs.
- Bifrost receives display-safe result validation state only.
- Deterministic tests cover result shape, raw-response exclusion, exact identity continuity, proof refs, trust/review state, prompt-drag continuity, response hash/telemetry status, fail-closed behavior, and no-live-call behavior.
- Reviews A/B clear the runtime implementation before live provider routing depends on it.
