# Relay/Aegis PromptPacket Policy Integration Checklist

**Status:** Build-ready checklist; runtime implementation not authorized by this doc
**Date:** 2026-06-02
**Owner harnesses:** Relay (dispatch/decision records), Aegis (policy evaluator), Bifrost (display consumer), Build 3 (future FileMap routing)
**Scope:** Wiring `evaluate_prompt_packet_proof_policy()` into Relay dispatch without mutating the Aegis evaluator

---

## Purpose

Define the implementation checklist for integrating the pure Aegis PromptPacket proof policy evaluator with Relay dispatch. The runtime work that follows this checklist should construct `PromptPacketProofMetadata` from Relay's sealed PromptPacket and dispatch-envelope proof fields, call `evaluate_prompt_packet_proof_policy()` before provider transport, and map the result into Relay decision/audit records and Bifrost-visible proof summaries.

This slice is docs-only. It must not edit runtime code, tests, FileMap, Bifrost UI, model/account/process code, branches, shared main, or Polaris.

---

## Integration Boundary

- Relay owns PromptPacket assembly, dispatch-envelope construction, decision records, adapter calls, retries, and Bifrost handoff payloads.
- Aegis owns `PromptPacketProofMetadata`, `PromptPacketProofPolicyResult`, `PromptPacketProofDecision`, and `evaluate_prompt_packet_proof_policy()`.
- Relay must not duplicate or fork Aegis policy rules; it should translate Relay metadata into the Aegis input object and then obey the returned result.
- Aegis must stay pure: no Relay mutation, no model call, no account inspection, no Bifrost rendering, no FileMap edit, no process control.
- `PromptPacket.model_payload()` remains the only model-facing prompt string.
- Provider adapters must not be called until the Aegis PromptPacket policy result allows or explicitly permits the selected non-blocking path.

---

## Source Data Relay Must Use

Build `PromptPacketProofMetadata` from already-sealed, structured Relay data:

- `PromptPacket.packet_id` -> `packet_id`.
- `PromptPacket.proof_metadata.packet_hash` -> `packet_hash`.
- Hash availability from Relay proof metadata and adapter snapshot requirements -> `packet_hash_status`.
- `PromptPacket.prompt_tokens` -> `prompt_tokens`.
- `PromptPacket.budget.max_context_tokens` -> `max_context_tokens`.
- `PromptPacket.proof_metadata.prompt_budget_ref` -> `budget_ref`.
- `PromptPacket.source_lineage` -> `source_lineage`.
- `PromptPacket.budget.allowed_sources` -> `allowed_sources`.
- `PromptPacket.proof_required` or route audit proof requirements -> `proof_requirement`.
- `PromptPacket.aegis_evidence_ids` and any Relay gate evidence ids -> `aegis_evidence_ids`.
- Relay route risk tier -> `risk_tier`.
- Exact selected model id from Model Harness/Relay route -> `selected_model_id`.
- Model Harness trust state -> `model_trust_state`.
- Dispatch hardening snapshot requirement -> `snapshot_requirement`.
- Prompt payload/adapter snapshot state -> `snapshot_status`.
- Cognition policy or route gate result -> `human_gate_required`.
- Review Console approval state -> `human_approval_present`.
- Tier/lane policy -> `dual_lane_required` and `dual_lane_proof_present`.
- Relay's safe lower-tier route target -> `demotion_target_tier`.

Do not rebuild these fields from raw prompt text inside Aegis. Relay may compute the packet hash before the call, but the hash must be derived from the same sealed prompt returned by `model_payload()`.

---

## Metadata Translation Rules

- Map missing proof metadata to explicit status values such as `missing` or `unavailable`; do not pass optimistic defaults.
- Map no-hash-needed Tier 0/1 cases to `packet_hash_status="not_required"` only when no snapshot, human-gate, dual-lane, external-review, or proof-critical route requirement applies.
- Map missing/failed hash computation to `packet_hash_status="missing"` when Relay expected to compute it.
- Map adapter snapshot capability gaps to `snapshot_status="unavailable"`, not `present`.
- Map stale or mismatched snapshot evidence to `snapshot_status="stale"` or blocker-facing metadata.
- Convert source lineage to a regular immutable-equivalent mapping for the Aegis input without changing counts or keys.
- Convert allowed sources and evidence ids to tuples in deterministic order.
- Preserve exact model id as the dispatch key, not a UI label or route-family alias.
- Preserve Model Harness trust state without promoting candidate or aggregator authority based only on packet validity.
- Preserve demotion target only when Relay has an already-authorized lower-tier route; otherwise leave it absent and let Aegis block or warn as policy requires.

---

## Fail-Closed Preconditions

Relay must fail closed before adapter transport when any precondition prevents a trustworthy Aegis call:

- PromptPacket construction failed validation.
- `proof_metadata` is absent from a PromptPacket that is being dispatched through the policy path.
- Packet id, prompt token count, budget, source lineage, or allowed source data is unavailable.
- Relay cannot determine risk tier or proof requirement.
- Relay cannot determine whether hash or snapshot proof is required.
- Relay cannot determine human-gate or dual-lane state for a route that might need it.
- Relay cannot serialize evidence IDs safely.
- Any metadata field contains raw prompt text, credentials, provider request bodies, raw provider responses, account secrets, process handles, or branch/worktree data.

The fail-closed decision should create a Relay decision record with a block outcome and reviewable explanation. It must not call the provider adapter.

---

## Aegis Call Site

- Call `evaluate_prompt_packet_proof_policy(metadata)` after PromptPacket proof metadata is sealed and before any provider adapter transport.
- Call once per dispatch lane that can independently reach model transport.
- For dual-lane routes, evaluate each lane's PromptPacket proof metadata independently before aggregating dispatch readiness.
- For retries or fallbacks, call again whenever prompt text, packet id, source lineage, budget, provider, model id, risk tier, proof requirement, snapshot requirement, or human-gate state changes.
- Treat the Aegis result as immutable decision evidence for the decision record.
- Do not mutate `PromptPacketProofMetadata` after evaluation.
- Do not let provider output retroactively satisfy missing packet proof metadata.

---

## Outcome Mapping

Relay should map Aegis outcomes deterministically:

| Aegis decision | Relay dispatch behavior | Decision-record behavior | Bifrost-visible behavior |
|---|---|---|---|
| `allow` | Continue to dispatch if other Relay/Model gates pass. | Store `aegis_gate_decision="allow"`, severity, evidence ids, and explanation. | Show policy allowed or omit only if the surface is configured to hide clean proof. |
| `warn` | Continue only when warning is non-blocking and all other gates pass. | Store warning severity, evidence ids, warning tags, and explanation. | Show warning state; do not hide degraded proof. |
| `demote` | Route only to the returned authorized demotion target; otherwise block. | Store demote decision, target tier when available, evidence ids, and explanation. | Show demotion reason and target. |
| `block` | Do not call provider adapter. | Store block decision and add `aegis_gate_blocked` plus result blockers to fallback blockers/error tags. | Show blocked policy state and evidence ids. |
| `human_gate` | Pause dispatch and require Review Console approval. | Store human-gate decision and add `aegis_human_gate_required`. | Show escalation required and missing approval evidence. |

`block` outranks `human_gate`, `human_gate` outranks `demote`, `demote` outranks `warn`, and `warn` outranks `allow` for a single lane. Multi-lane aggregation must not let one allowed lane hide another lane's block or human gate.

---

## Decision Record Requirements

Relay decision records should preserve the Aegis result using existing Aegis-friendly fields where possible:

- `aegis_gate_decision`: Aegis decision value.
- `aegis_gate_severity`: Aegis severity value.
- `aegis_evidence_ids`: ordered immutable evidence IDs.
- `aegis_explanation`: Aegis reason text.
- `aegis_waiver_present`: true only when a scoped waiver was applied.
- `fallback_blockers`: include `aegis_gate_blocked` for block and `aegis_human_gate_required` for human gate.
- Dispatch error tags: include result blockers and policy-warning tags in deterministic order.
- Demotion fields: include target tier/route when Relay accepts an Aegis demotion.
- Packet proof summary: packet id, packet hash status, budget status, source-lineage status, snapshot status, human-gate state, and dual-lane state.

Decision records must stay serializable, deterministic, and display-safe. They must not contain raw prompt text, raw source content, credentials, transport request bodies, raw provider responses, account ids, or process handles.

---

## Raw Prompt And Credential Exclusions

- Do not pass `serialized_prompt` into `PromptPacketProofMetadata`.
- Do not store `model_payload()` in decision records, Bifrost proof summaries, or Aegis evidence IDs.
- Do not include raw source snippets, retrieval excerpts, review logs, or file contents in the policy handoff.
- Do not include API keys, bearer tokens, OAuth material, cookies, account identifiers, billing details, request headers, environment values, provider request JSON, raw provider responses, local paths outside safe project references, process ids, or branch-control data.
- Treat unsafe metadata detection as a pre-dispatch block, not a warning.
- Tests should include a sentinel secret/raw-prompt string and prove it is absent from decision records and Bifrost handoff payloads.

---

## Bifrost Handoff Expectations

Relay should expose a display-safe Aegis PromptPacket policy summary for Bifrost after evaluation:

- Decision: `allow`, `warn`, `demote`, `block`, or `human_gate`.
- Severity: `info`, `warning`, or `error`.
- Evidence IDs: ordered references only.
- Explanation: plain text reason without raw prompt content.
- Blockers and warnings: deterministic tags from Aegis result.
- Packet id reference.
- Packet hash status, not raw prompt content.
- Budget status and prompt token count.
- Source-lineage compliance status and source names/counts only when safe.
- Snapshot status.
- Human-gate state.
- Dual-lane proof state.
- Demotion target when applicable.

Bifrost must not call `evaluate_prompt_packet_proof_policy()`, call Relay packet assembly, inspect PromptPacket raw prompt content, create waivers, approve human gates, mutate proof payloads, or hide degraded policy state.

---

## Retry, Fallback, And Demotion Rules

- Never retry with stale PromptPacket policy results after prompt, packet, route, provider, model, budget, source lineage, or proof requirement changes.
- Never silently fallback from a blocked Aegis result to a different provider/model.
- A `warn` result may continue only on the same approved route and only when other gates pass.
- A `demote` result may continue only through an explicit lower-tier route that preserves proof requirements and has its own fresh PromptPacket policy evaluation.
- A `human_gate` result may resume only after approval state changes and Relay reruns the evaluator.
- A `block` result may resume only after the underlying proof metadata changes and Relay reruns the evaluator.

---

## Deterministic Test Expectations

Future runtime integration should add tests covering:

- Relay builds `PromptPacketProofMetadata` from sealed PromptPacket proof metadata and route/dispatch envelope fields.
- Valid policy metadata calls Aegis before provider transport and records `allow`.
- `warn` continues dispatch while recording warning severity/tags and Bifrost-visible degraded state.
- `demote` routes only to an explicit lower-tier target and records demotion evidence.
- `demote` without an authorized target blocks.
- `block` prevents adapter calls and records `aegis_gate_blocked`.
- `human_gate` prevents adapter calls and records `aegis_human_gate_required`.
- Missing PromptPacket proof metadata fails closed before adapter calls.
- Missing packet id, hash, budget ref, allowed sources, evidence ids, snapshot state, or human/dual-lane state maps to explicit Aegis input statuses or pre-call blocks.
- Dual-lane routes evaluate each lane independently and block/human-gate if either lane requires it.
- Retry/fallback builds fresh metadata and reruns Aegis when route inputs change.
- Decision records preserve Aegis decision, severity, evidence ids, explanation, blockers, warnings, and packet proof summary.
- Bifrost handoff contains display-safe policy summary fields only.
- Raw prompt text, credentials, account data, raw provider request/response, and process/branch data are excluded from serialized audit and Bifrost payloads.
- Same Relay input metadata produces the same Aegis call input, result mapping, error tags, and decision-record fields.

---

## FileMap Routing

After Codex review clears this checklist, Build 3 should register:

| File | Area | Purpose | Related Tests | Notes |
|---|---|---|---|---|
| `docs/relay-aegis-promptpacket-policy-integration-checklist.md` | Relay / Aegis | Checklist for wiring Aegis PromptPacket proof policy results into Relay dispatch, decision records, and Bifrost-safe handoff. | Future Relay/Aegis PromptPacket policy integration tests. | Build 4 docs-only checklist; FileMap routing belongs to Build 3 after review. |

Do not edit `docs/FileMap.md` in this Build 4 slice.

---

## Runtime Enablement Gate

Relay/Aegis PromptPacket policy integration is runtime-ready only after:

- Relay constructs `PromptPacketProofMetadata` from sealed packet/envelope fields.
- Aegis is called before provider adapter transport.
- Allow/warn/demote/block/human-gate outcomes are mapped into dispatch behavior and decision records.
- Fail-closed missing metadata behavior is tested.
- Retry/fallback/demotion reruns are tested.
- Raw prompt and credential exclusions are tested.
- Bifrost receives structured display-safe summaries only.
- Required runtime tests pass in the owning Relay/Aegis/Bifrost lanes.
- FileMap registration is routed after review.
- Codex review clears this checklist and the future runtime integration.
