# Relay/Bifrost Prompt Payload Meter Checklist

**Status:** Implementation checklist
**Date:** 2026-06-02
**Owner harnesses:** Relay (dispatch evidence), Bifrost (cockpit visibility), Model Harness (prompt telemetry), Aegis (policy blockers)
**Source docs:** `docs/v2-progress-tracker.md`, `docs/relay-prompt-payload-visibility-implementation-checklist.md`, `docs/bifrost-balance-payload-surface-contract.md`, `docs/model-harness-v2-contract.md`, `docs/relay-bifrost-proof-payload-contract.md`

## Purpose

Build the frontend-critical prompt payload meter remaining in `docs/v2-progress-tracker.md`: Relay must carry reviewed `PromptPayloadSnapshot`, budget, and growth metadata through dispatch, and Bifrost must render a deterministic cockpit-visible meter for every model dispatch and queue/Q-mode prompt.

This checklist is docs-only. It does not edit runtime code, UI code, FileMap, model/provider adapters, session/process control, shared main, push state, or Polaris.

## Relay Dispatch Evidence

- [ ] Bind the reviewed `PromptPayloadSnapshot` helper into Relay dispatch evidence before the provider/model boundary.
- [ ] Preserve snapshot identity fields: snapshot id/ref, packet id/hash when present, prompt payload snapshot hash, payload source, producer lane, dispatch id, and comparison scope.
- [ ] Preserve numeric fields: estimated prompt tokens, context window tokens, prompt budget tokens, max output tokens when known, remaining context tokens, previous prompt tokens, delta tokens, delta percent, and budget percent.
- [ ] Preserve status fields: budget status, budget compliant flag, over-budget reason, growth state, prompt-drag state, measurement status, snapshot availability, and telemetry availability.
- [ ] Preserve route continuity fields beside the meter: provider id, exact model id, route kind, direct-vs-aggregator state, trust state, proof refs, external-review state, and metadata evidence refs.
- [ ] Relay must not let successful model output replace missing payload evidence.

## Meter Labels And Formatting

- [ ] Produce display labels from structured token counts only, never from raw prompt text.
- [ ] Use `under-1k` for nonzero payloads below 1,000 estimated prompt tokens.
- [ ] Use one-decimal `N.Nk` formatting for 1,000+ token payloads, such as `12.4k`.
- [ ] Use `0` for empty measured payloads when empty payloads are valid for the lane.
- [ ] Use `unknown` when token estimation or payload snapshot evidence is unavailable.
- [ ] Use `over budget` when prompt tokens exceed the selected prompt/context budget.
- [ ] Preserve both machine values and display strings: `prompt_tokens`, `prompt_label`, `budget_percent`, `budget_percent_label`, `delta_tokens`, `delta_percent`, and `growth_delta_label`.
- [ ] Round labels deterministically; Bifrost must not recalculate labels from hidden raw prompt content.

## Budget And Growth Semantics

- [ ] Compute `budget_percent` as prompt tokens divided by the applicable prompt or context budget.
- [ ] Mark budget state as `ok`, `watch`, `over_budget`, `unknown`, or `blocked`.
- [ ] Mark growth state as `flat`, `growing_expected`, `growing_unexpected`, `degraded`, `blocked`, or `unknown`.
- [ ] Attach expected-growth reasons when new task evidence, approved retrieval, approved summary expansion, or human edits explain growth.
- [ ] Treat unexplained positive growth across repeated queue, idle, read-check, or Q-mode polls as prompt-drag degradation.
- [ ] Preserve prompt-drag tags and blocker tags so Relay, Aegis, Bifrost, and review lanes see the same state.

## Queue And Q-Mode Degradation

- [ ] Queue/Q-mode prompts are first-class meter sources, not invisible background checks.
- [ ] Repeated Q-mode checks should show whether the payload is flat, bounded, growing, degraded, or blocked.
- [ ] Additive prompt growth across unchanged task state emits a deterministic `prompt_drag_degraded` warning or blocker.
- [ ] DeepSeek Q-mode flatness display requires direct route metadata, `q_mode_flat = true`, temperature-zero evidence, payload snapshot support, and route continuity.
- [ ] If a direct DeepSeek Q-mode route is expected but telemetry shows aggregator/OpenRouter, display a route mismatch warning and keep Q-mode degraded.
- [ ] Read-check-only work must not clear degradation or count as productive progress.

## Aegis And Relay Blockers

- [ ] Relay blocks or demotes dispatch when payload evidence is missing, unknown for the risk tier, over budget, source-lineage invalid, unexpectedly growing, or route continuity is broken.
- [ ] Aegis receives prompt payload meter state as policy evidence: measurement status, budget status, growth state, prompt-drag state, proof refs, external-review state, and route continuity.
- [ ] Aegis/Relay blocker tags remain visible to Bifrost without mutation.
- [ ] Missing provider/model metadata, unknown exact model id, aggregator route where direct proof is required, missing prompt snapshot, missing budget ref, or missing proof refs fail closed according to lane risk.
- [ ] Successful provider output cannot clear a prompt meter blocker, trust blocker, external-review blocker, or route mismatch blocker.

## Bifrost Cockpit Visibility

- [ ] Bifrost receives a structured view-model handoff from Relay; it must not call Relay executors, Aegis validators, provider adapters, or vendor/account APIs to reconstruct meter state.
- [ ] The cockpit shows prompt label, prompt tokens, budget percent label, growth delta label, growth state, prompt-drag state, snapshot availability, provider id, exact model id, route kind, trust state, and blocker/warning tags.
- [ ] The meter is visible next to model dispatch events and queue/Q-mode poll events.
- [ ] Bifrost shows route continuity warnings when provider/model/route metadata changed between pre-dispatch evidence and result evidence.
- [ ] Bifrost shows degraded and blocked states in a deterministic order and does not hide prompt growth to keep the UI clean.
- [ ] Bifrost renders display-safe labels only; no raw prompt, source text, provider response, credential, account state, branch/worktree path, process id, or session-control data enters the view-model.

## Escaping And Display Safety

- [ ] Escape all labels, ids, refs, warning tags, blocker tags, route labels, and provider/model display names before rendering.
- [ ] Treat `prompt_label`, `growth_delta_label`, route labels, and blocker text as untrusted display data even when generated locally.
- [ ] Tests include sentinel strings for HTML/script injection, raw prompt text, raw provider response text, credentials, account ids, process ids, branch/worktree paths, shared-main paths, push-to-main strings, and Polaris references.
- [ ] Unsafe sentinel values must be escaped or redacted in Bifrost-facing output and absent from raw evidence dictionaries where not explicitly allowed.

## Deterministic Test Expectations

- [ ] Unit tests for prompt labels: `under-1k`, `12.4k`, `0`, `unknown`, and `over budget`.
- [ ] Unit tests for budget percent calculation, rounding, unknown budget, zero/invalid budget, over-budget state, and blocked budget state.
- [ ] Unit tests for growth delta labels, expected versus unexpected growth, queue/Q-mode additive growth, read-check-only behavior, and degraded prompt-drag state.
- [ ] Unit tests proving provider/model route continuity fields are preserved beside the meter.
- [ ] Unit tests proving Aegis/Relay blocker tags survive handoff and cannot be cleared by successful provider output.
- [ ] Snapshot/render tests proving Bifrost displays meter labels, budget percent, growth delta, Q-mode degraded state, provider/model route labels, warnings, blockers, and escaped sentinel strings.
- [ ] Tests use fakes/fixtures only: no live provider calls, credential/account probing, process/session control, branch movement, FileMap edits, shared-main writes, pushes, or Polaris work.

## Explicit Exclusions

- Runtime implementation in Relay, Bifrost, Aegis, Model Harness, provider adapters, FileMap, session lifecycle, process control, or UI files.
- Live provider calls, credential discovery, account probing, billing/quota scraping, provider account mutation, or autonomous routing.
- Raw prompt text, raw source text, raw provider request bodies, raw provider responses, raw model output, credentials, API keys, headers, account ids, process/session-control state, branch/worktree state, shared-main paths, push-to-main data, or Polaris references in the meter surface.
- Bifrost choosing routes, approving trust promotion, clearing external review, mutating Relay/Aegis metadata, or hiding prompt-drag degradation.

## Runtime Enablement Gate

Prompt payload meter work may be marked implemented only after:

- [ ] Relay emits structured prompt meter evidence for every model dispatch and queue/Q-mode prompt.
- [ ] Bifrost displays the meter from structured handoff data without recalculating from raw prompts.
- [ ] Aegis/Relay blockers fail closed for missing, over-budget, degraded, or route-mismatched payload evidence.
- [ ] Deterministic tests cover labels, budgets, growth, Q-mode degradation, route continuity, blockers, escaping, no-leak behavior, and no-live-call behavior.
