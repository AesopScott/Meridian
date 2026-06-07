# DeepSeek Provider Validation Gate

**Owner:** Relay / Model Harness

**Purpose:** Define how Meridian evaluates DeepSeek before Prime may route autonomous coding or queue work through it.

DeepSeek is a primary provider candidate beside Claude and OpenAI, but it is not trusted as an autonomous coding lane by default. Prime may use DeepSeek only through Relay and Aegis, and only at the capability level that has been validated.

## Rule

DeepSeek starts in **candidate provider** state.

Prime must not assign DeepSeek to autonomous code-writing, review-clearing, branch movement, or queue-orchestration authority until the Model Harness records a passing validation gate.

This keeps DeepSeek useful without pretending the model has already earned the same trust profile as the proven build lanes.

## Initial Allowed Use

- Build-oriented Q-mode prompts with bounded scope.
- Planning, summarization, checklist drafting, and contract drafting.
- Low-risk docs tasks when another provider or Codex can review the result.
- Direct API calls only through Relay / Model Harness.
- Prompt payload metering on every dispatch.

## Initial Disallowed Use

- Independent Codex review replacement.
- Review-clearing authority.
- Autonomous commits without an external review gate.
- Branch movement or worktree mutation authority.
- Any bypass around Relay, Aegis, or prompt payload metering.
- OpenRouter fallback when the task explicitly requires direct DeepSeek API behavior.

## Validation Ladder

### Level 0: Candidate

DeepSeek is available as a configured provider but receives only bounded planning or docs prompts.

Required proof:

- Direct API adapter metadata exists.
- Provider name, model name, endpoint type, and budget metadata are structured.
- Prompt payload size is visible before dispatch.
- No transcript replay or additive queue prompt growth across repeated Q-mode polls.

### Level 1: Assisted Coding

DeepSeek may draft small code patches, but another trusted reviewer must inspect before merge.

Required proof:

- Passes deterministic small-scope coding benchmark tasks.
- Produces patches that pass unit tests without hidden prompt expansion.
- Does not modify files outside the assigned allowlist.
- Produces enough rationale for Prime, Aegis, or Codex to audit the change.

### Level 2: Gated Build Lane

DeepSeek may execute build queue tasks when Aegis risk tier, file allowlist, and review cadence permit it.

Required proof:

- Multiple representative Meridian build slices pass tests and Codex review.
- Failure behavior is understood: retries, refusal, hallucinated APIs, and stale context handling.
- Prime can demote DeepSeek automatically after failed tests, review findings, prompt growth, or scope drift.
- Queue work remains tied to a unique worktree.

### Level 3: Primary Coding Provider

DeepSeek may be treated as a normal primary build provider for selected risk tiers.

Required proof:

- Sustained pass rate across implementation, docs, and repair tasks.
- No material prompt-drag regression versus Claude/OpenAI lanes.
- Cost and latency advantages are visible in the Balance surface.
- Aegis can still require a second cognition lane for higher-risk tasks.

## Routing Metadata

The Model Harness should represent this as provider metadata, not prompt prose:

- `provider`: `deepseek`
- `api_mode`: `direct`
- `trust_state`: `candidate | assisted_coding | gated_build_lane | primary_coding_provider`
- `allowed_task_types`
- `blocked_task_types`
- `requires_external_review`
- `prompt_payload_growth_policy`
- `last_validation_result`
- `last_validation_at`

Prime routes from this metadata. Bifrost displays the trust state and prompt payload pressure, but does not decide whether DeepSeek is trusted.

## Acceptance Criteria

- DeepSeek can be configured without becoming an automatic coding lane.
- A task can require direct DeepSeek API and reject aggregator routing.
- Q-mode dispatch shows prompt payload size, budget pressure, and growth delta.
- Repeated queue polls do not replay the entire prior conversation unless the task explicitly changed.
- A failed validation demotes the provider or blocks the task before code lands.
- Codex/Review lanes can see which DeepSeek validation level was used for a slice.

## V2 Boundary

V2 should build the provider metadata, direct API target, prompt payload visibility, and validation contract. Full trust automation can mature across V2 and V3 as evidence accumulates.

## Validation-Gate Proof and Transport Authority (Backend)

The backend surface that gates DeepSeek transport authority lives in
`meridian_core/model_adapter.py` and is consumed by
`meridian_core/relay_executor.py` through `RelayDispatchMetadataEnvelope`.

### Proof States (`DeepSeekValidationProofState`)

| State | Meaning | Transport |
| --- | --- | --- |
| `none` | No proof submitted. | Blocked. |
| `candidate-metadata-only` | Candidate metadata present; no live-validation proof. | Blocked. |
| `proof-submitted-pending-review` | Proof submitted; review/clearance pending. | Blocked. |
| `proof-stale` | Proof present but past `proof_max_age_seconds`. | Blocked. |
| `proof-partial` | Proof missing required evidence components. | Blocked. |
| `proof-revoked` | Previously verified proof has been revoked. | Blocked. |
| `proof-verified` | Verified, fresh, complete proof on file. | Transport authority requires both authority gates below. |

### Authority Gates

Even with `proof-verified`, transport remains blocked unless both gates are
satisfied:

- `human_gate_satisfied`: human approval recorded.
- `prime_authority_satisfied`: Prime/Beacon authority recorded.

### Transport Authority Status (`DeepSeekTransportAuthorityStatus`)

The evaluation surface returns exactly one of:

- `blocked:no-proof`
- `blocked:candidate-only`
- `blocked:proof-partial`
- `blocked:proof-stale`
- `blocked:proof-revoked`
- `blocked:proof-pending-review`
- `blocked:human-gate-required`
- `blocked:prime-authority-required`
- `authorized:transport-only`

`authorized:transport-only` is the only state where `transport_authorized=True`.
This status authorizes Relay direct-provider transport only. It does **not**
grant autonomous implementation, review clearing, branch movement, live
coding, or Relay bypass — those five autonomy bits are hard-coded `False`
and the `blocked_authority_tags` tuple
(`autonomous_implementation`, `review_clearance`, `branch_movement`,
`live_coding`, `relay_bypass`) is enforced by the dataclass guard.

### Defaults and Invariants

- Default `proof_state` when no proof source is wired up: `none`.
- Default for `bind_deepseek_transport_authority()` against current
  candidate metadata on main: `blocked:candidate-only`.
- Dispatch identity rule preserved: `direct_dispatch_id == "deepseek-chat"`.
- Variant labels (`deepseek-v4-pro`, `deepseek-v4-flash`) remain
  capability/variant labels and never reach the transport authority's
  `direct_dispatch_id` field.
- `serialization_only=True` is enforced — the transport-authority record is
  display/advisory, not an execution capability.
- `transport_authorized` must equal `status == AUTHORIZED_TRANSPORT_ONLY`;
  any mismatch raises at construction.
