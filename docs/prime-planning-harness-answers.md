# Prime Planning Harness Answers - V0 Relay Dispatch

**Created:** 2026-05-30
**Owner:** Prime + Planning Harness
**Purpose:** Run the Planning Harness questions against Meridian's current V0 objective and record the recommended answers before the next build/restart cycle.

## Objective

Complete Meridian V0's remaining core gate: real Relay model/API dispatch through the existing Relay executor skeleton, without violating the Prime directives around lean dispatch, proof gating, worktree sovereignty, or public/private adapter boundaries.

## Source Corpus

- `meridian_core/planning.py` - deterministic Planning Harness questions and recommendation model.
- `docs/planning-harness-council-brief.md` - Council + grill-with-docs planning rule.
- `docs/meridian-pillars.md` - Prime directives, especially Dynamic Risk-Tiered Dual-Structured Gated Cognition, Relay prompt efficiency, worktree sovereignty, and grill-with-docs.
- `docs/v0-v1-progress-tracker.md` - V0 is 5/6 core gates built; the remaining gate is real Relay model/API dispatch.
- `docs/v0-build-readiness-map.md` - V0 definition and dependency chain.
- `meridian_core/relay_executor.py` - current provider-neutral injected model-call boundary and Aegis pre-dispatch gate.
- `docs/live-codex-reviews.md` - review cadence, proof, and clearance expectations.

## Planning Run

This is a tier-3 planning run because the next slice changes the model-dispatch boundary, affects cost/latency, and touches proof-sensitive execution behavior. Tier 3 invokes the full Council:

- Analyst
- Devil's Advocate
- Pragmatist
- Contrarian
- Expansionist
- Chairman

## Council Answers

### Analyst

**Question:** What evidence or existing docs constrain this objective?

**Recommended answer:** Meridian is already past the pure planning stage for V0. The tracker records 5/6 core V0 gates built, with only `Relay Harness: real model/API dispatch through the existing Relay executor skeleton` still open. The existing executor is deliberately provider-neutral: it accepts a callable that receives only the lane payload and returns text. That boundary is not accidental; it protects Relay from prompt drag, metadata leakage, and premature vendor coupling. Aegis proof-gate enforcement is already wired before dispatch for tier-3/4 lanes. Any next implementation must preserve those constraints.

**Source classification:** documented + inspected code.

**Confidence:** high.

### Devil's Advocate

**Question:** What assumption would make this plan fail?

**Recommended answer:** The dangerous assumption is that "real model/API dispatch" means "put a vendor SDK directly inside Relay core." That would weaken the architecture by mixing provider credentials, public/private terms-of-service decisions, and model transport details into the local orchestrator boundary. It could also recreate Polaris prompt drag if Relay starts shipping metadata, Council context, queue history, or proof records into every worker call.

The second dangerous assumption is that dispatch can proceed without proof and review discipline. Current Prime directives require proof-sensitive work to pass through Aegis and review cadence. The existing proof gate must remain before any model call.

**Source classification:** documented + inferred from architecture constraints.

**Confidence:** high.

### Pragmatist

**Question:** What is the next useful planning action?

**Recommended answer:** Build the smallest adapter-backed dispatch slice:

1. Keep `meridian_core/relay_executor.py` provider-neutral.
2. Add a model adapter protocol/module that can wrap official API clients without exposing vendor details to Relay core.
3. Provide a deterministic fake/test adapter for tests.
4. Add environment-safe configuration behavior: if API credentials are absent, dispatch fails clearly before trying a network call.
5. Prove that only `lane.payload` crosses into the adapter and that Aegis blocking evidence prevents the adapter call.

This makes V0 meaningfully closer to real dispatch without hardcoding Claude, OpenAI, OpenRouter, or account-based desktop automation into Prime.

**Source classification:** recommendation from documented constraints.

**Confidence:** high.

### Contrarian

**Question:** What if the obvious implementation path is too rigid?

**Recommended answer:** The obvious path is to choose one provider immediately and wire it directly. The better path is to separate "Relay can dispatch to a model" from "which provider is active today." Meridian's public version will need official API adapters, while Scott's private build may also use account-based/session automation. Those are different adapter families. Treating them as the same thing now would create cleanup work later.

The next slice should prove the adapter seam before blessing a specific provider as the default.

**Source classification:** inferred from public/private adapter discussions and Relay architecture.

**Confidence:** medium-high.

### Expansionist

**Question:** What upside is missing from the current framing?

**Recommended answer:** This slice can become more than a model call. It can become Prime's first durable dispatch contract:

- Relay owns prompt payload construction and model-role routing.
- Model Harness owns provider/session adapters.
- Aegis owns proof gates before and after dispatch.
- Review Console owns visible results, failures, and approval gates.
- Beacon can later observe whether the adapter/session is alive.

If this is shaped cleanly, V1 Bifrost can visualize the whole dispatch path without needing to redesign the core.

**Source classification:** inferred architecture synthesis.

**Confidence:** medium-high.

### Chairman

**Question:** Which Council voice should decide what Prime presents next?

**Recommended answer:** The Pragmatist should lead the next build instruction, constrained by the Analyst and Devil's Advocate. Prime should present the next slice as a provider-neutral Model Harness adapter contract, not as a vendor-specific Claude/OpenAI integration. The actual provider can be selected after the contract exists and after Scott confirms which official API should be first.

**Recommended next action:** Draft and dispatch a build slice for `Model Harness + Relay Harness: provider-neutral adapter contract and env-safe dispatch path`.

**Source classification:** Council synthesis.

**Confidence:** high.

## Unresolved Scott Judgment

Only these questions should come back to Scott before a provider-specific implementation:

- Which official API provider should be first for V0 live dispatch: Claude, OpenAI, OpenRouter, or another provider?
- Should V0 require real credentials on the machine, or is an adapter contract plus deterministic fake adapter enough until the cockpit is visible?
- Should private account-based automation remain completely separate from official API adapter work until after V0?

Prime can continue without those answers by building the adapter contract, fake adapter, tests, and env-safe failure behavior first.

## Terms To Capture

- **Model Adapter:** Provider/session-specific implementation behind the Model Harness. It receives an approved payload and returns model text or a structured failure.
- **Relay Dispatch Boundary:** The line where Relay hands only `lane.payload` to the model adapter. Metadata stays outside the model call.
- **Env-Safe Dispatch:** Runtime behavior that refuses live provider calls when required credentials/configuration are absent.
- **Adapter Family:** A group of compatible model adapters, such as official API adapters, local model adapters, or private account/session adapters.

## ADR Candidates

- Relay core remains provider-neutral; vendor and account-specific behavior belongs behind Model Harness adapters.
- The model-call payload must remain lean: only the approved serialized prompt crosses the dispatch boundary by default.
- Tier-3/4 dispatch must check Aegis proof gates before calling any adapter.
- Public-safe official API adapters and private account/session adapters are separate adapter families.

## Next Build Slice

**Owner:** Relay Harness + Model Harness

**Goal:** Add a provider-neutral adapter contract and env-safe dispatch path for real model/API dispatch, while preserving the existing Relay executor boundary.

**Expected implementation shape:**

- Add a small model adapter module or type that accepts the existing payload-only callable contract.
- Keep `execute_relay_dispatch_plan()` callable with the current injected `model_call` path.
- Add tests proving:
  - only lane payload is passed into the adapter;
  - Aegis blocking evidence prevents the adapter call;
  - missing live credentials/configuration fails clearly;
  - fake adapter dispatch returns deterministic output.
- Do not add account-based desktop automation to public/core dispatch.
- Do not expand worker prompts with queue history, Council notes, proof trails, or other Prime metadata unless a later risk-tier-specific injection explicitly asks for it.

**Review expectation:** Codex review should inspect the adapter boundary, payload leakage, Aegis order of operations, and env-safe failure behavior.

## Chairman Recommendation

Proceed with the adapter-contract slice before choosing a default provider. This keeps V0 moving, protects Meridian's architecture, and gives Scott a clean decision point later: which official provider should be activated first.
