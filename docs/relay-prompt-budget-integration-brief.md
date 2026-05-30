# Relay Prompt Budget Integration Brief

**Status:** Planning only — no runtime changes yet  
**Scope:** Architectural integration of PromptBudgetPlan into RelayRoute and Relay dispatch  
**Related:** `meridian_core/prompt_budget.py`, `meridian_core/relay.py`, `meridian_core/council.py`

---

## Problem Statement

Relay routing currently produces `RelayRoute` with model roles, lanes, and cost posture, but no token budget constraint. Worker harnesses dispatch model sessions with uncontrolled context injection, risking:

- Excessive diagnostic overhead riding in every prompt
- Prompt growth without visibility into context sources
- Longer time-to-first-token and higher vendor costs
- Worker experience worse than using vendor tooling directly

**Principle:** *Relay Must Not Become Prompt Drag* — token budgets are tier-locked, non-negotiable, and visible at routing time.

---

## Design: RelayRoute Carries PromptBudgetPlan

### Current RelayRoute (today)

```python
@dataclass
class RelayRoute:
    mode: RoutingMode
    lanes: list[RelayLane]
    context_strategy: ContextStrategy
    reason: str
    cost_posture: CostPosture
    requires_independence: bool
    requires_human_gate: bool
    risk_tier: int
    council_plan: CouncilPlan
```

### Future RelayRoute (with budget)

```python
@dataclass
class RelayRoute:
    mode: RoutingMode
    lanes: list[RelayLane]
    context_strategy: ContextStrategy
    reason: str
    cost_posture: CostPosture
    requires_independence: bool
    requires_human_gate: bool
    risk_tier: int
    council_plan: CouncilPlan
    prompt_budget: PromptBudgetPlan  # ← NEW
```

### Integration point: `route_from_assessment()`

```python
def route_from_assessment(
    assessment: RiskAssessment,
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
) -> RelayRoute:
    # ... existing routing logic ...
    
    # NEW: fetch budget from prompt_budget module
    budget_plan = prompt_budget_for_risk_tier(assessment.tier)
    
    return RelayRoute(
        mode=row["mode"],
        lanes=[...],
        context_strategy=context_strategy,
        reason=row["reason"],
        cost_posture=row["cost_posture"],
        requires_independence=row["requires_independence"],
        requires_human_gate=row["requires_human_gate"],
        risk_tier=assessment.tier,
        council_plan=council_plan_for_tier(assessment),
        prompt_budget=budget_plan,  # ← NEW FIELD
    )
```

---

## Risk Tier → Prompt Budget Mapping

Deterministic, canonical mapping from RiskTier to PromptBudgetTier:

| Risk Tier | Routing Mode | Budget Tier | Max Tokens | Context Sources |
|-----------|--------------|-------------|------------|-----------------|
| **0** | NO_MODEL | MINIMAL | 500 | direct_input |
| **1** | SINGLE_LANE | MINIMAL | 1,000 | direct_input, task_context |
| **2** | DUAL_LANE | FOCUSED | 2,500 | + recent_history |
| **3** | DUAL_LANE_PROOF | BOUNDED | 5,000 | + proof_evidence, review_notes |
| **4** | HUMAN_GATE | EXPLAINED | 8,000 | + human_explanation_draft |

**Key principle:** Tier 0/1 are lean by design (no overhead). Tier 3/4 allow proof and explanation context but remain bounded (no unbounded bloat).

---

## Interaction with CouncilPlan

### Today
`RelayRoute.council_plan` tells Prime which cognitive positions (Analyst, Devil's Advocate, Pragmatist, etc.) to invoke for deliberation inside Prime.

### With PromptBudgetPlan
Council deliberation happens in Prime (orchestration layer), which can be rich. But dispatch to worker harnesses is bounded by `prompt_budget.max_context_tokens`.

**Clear separation:**
- **Prime/Orchestration:** Rich context, full Council, multiple passes (no prompt overhead constraint)
- **Relay/Worker:** Lean context, bounded by budget, tier-locked sources

**Example flow (Tier 3):**
1. Prime gets full CouncilPlan with all 6 Council roles
2. Prime deliberates with full context (Analyst, Devil's Advocate, etc.)
3. RelayRoute is created with `prompt_budget=PromptBudgetPlan(tier=BOUNDED, max_tokens=5000, ...)`
4. Relay dispatches Worker with max 5,000 tokens: direct_input, task_context, recent_history, proof_evidence, review_notes
5. Worker stays lean; Prime stays rich

---

## What Must NOT Ride in Worker Prompts

Blocked (stays in Prime or Aegis, not in worker dispatch):

### 1. Prime Deliberation State
- Council discussion transcripts
- Lane disagreement reasoning
- Alternative candidate paths not chosen
- Evidence Prime weighed but rejected
- Deliberation metadata (confidence scores, debate length)

**Why:** Prime reasoning is internal; Worker needs only decision outcome.

### 2. Diagnostic Metadata
- Session state snapshots
- Performance counters (time spent, tokens consumed so far)
- Harness lifecycle events (startup, shutdown, migration)
- Model introspection (embedding dims, context window, rate limits)
- Debug logs from prior workers in the session

**Why:** Diagnostic overhead grows linearly with session age; Worker should not pay for it.

### 3. Process Instructions
- Workflow step numbers ("You are on step 7 of 12")
- Backtrack history ("We tried X, then Y, now trying Z")
- Retry counters ("This is attempt 3 of 5")
- Fork-choice history ("We branched at step 4")

**Why:** Worker needs current objective, not process archaeology.

### 4. State Bloat
- Full portfolio snapshots
- Initiative lists (Worker only needs its own)
- Global config or constants (pass only what Worker uses)
- Historical mission logs

**Why:** Each lane should be independent; Workers should not share session-wide state.

### 5. Wrapper Instructions Riding in Every Message
- "You are an autonomous coding agent"
- "Your task is to..." (should be in initial dispatch, not every message)
- "Return JSON in this format" (include once, not every prompt)
- "Follow these safety rules" (include once, let Worker remember)

**Why:** Token count explodes if every message includes boilerplate.

---

## Diagnostics and Metrics Stay Outside Prompt Path

### How it works today
Worker harness logs to stdout/file. Prime/Relay read logs post-execution.

### Keep this separation
- **Prompts:** Only context needed for cognition (input, task, proof, explanation)
- **Metrics:** Parallel track—logged outside prompts, analyzed after dispatch
- **Diagnostics:** Captured in session logs, not injected back into prompts

### Future Prompt Metrics Pipeline (sketch)

```
Worker dispatch (tier, context_strategy, budget)
    ↓
Relay creates session with token budget ceiling
    ↓
Worker runs (prompt tokens, response tokens, time)
    ↓
Session logs captured (separate from prompt)
    ↓
Post-dispatch analysis:
  - Token usage vs. budget
  - Time-to-first-token
  - Overhead measurements
  - Lane disagreement, retries
    ↓
Metrics written to metrics store (not back to prompts)
```

**Key:** Diagnostics never flow back into the next Worker prompt. They stay in the metrics pipeline.

---

## Comparing Relay Overhead to Native/Vendor Baseline

### Instrumentation needed

1. **Vendor baseline:** Send minimal prompt (task + input only) to vendor model directly.
   - Measure: time-to-first-token, response tokens, cost

2. **Relay dispatch:** Send same task with budget-constrained context to Worker.
   - Measure: same metrics, plus Worker harness overhead

3. **Diff:** `Relay overhead = Relay metrics - Vendor baseline`

### Example targets

- **Tier 0/1:** Relay overhead should be < 5% (minimal harness tax)
- **Tier 2:** Relay overhead < 10% (context strategy cost acceptable)
- **Tier 3/4:** Overhead < 20% (proof/review context is intentional cost)

### What to measure

- **Per dispatch:** token count, time to first token, total response time, retries
- **Per lane:** Builder vs. Reviewer vs. Verifier overhead
- **Aggregate:** Median, p95, p99 overhead across tiers
- **Trend:** Overhead over session age (should not grow with time)

### Metrics destinations

- Time-series database (Prometheus, CloudWatch, or similar)
- Dashboards for cost tracking (Grafana)
- Alerts for overhead spikes
- Post-review analysis for prompt budget tuning

---

## Tests Required Before Integration

### Unit tests (existing tests should continue)

- `test_prompt_budget.py` — Budget determinism, immutability, tier semantics (22 tests, all passing)
- No changes to existing Relay, Intention, Objectives, Aegis tests

### Integration tests (new, to be added in integration PR)

#### 1. RelayRoute carries budget (no execution)
```python
def test_relay_route_includes_prompt_budget():
    """RelayRoute.prompt_budget is populated from risk tier."""
    assessment = assess_tier(2)
    route = route_from_assessment(assessment)
    assert route.prompt_budget is not None
    assert route.prompt_budget.tier == PromptBudgetTier.FOCUSED
    assert route.prompt_budget.max_context_tokens == 2500

def test_route_budget_tier_matches_risk_tier():
    """Budget tier matches risk tier mapping."""
    for tier in range(5):
        route = route_from_tier(tier)
        assert route.prompt_budget.tier is not None
        # Verify tier 0/1 map to MINIMAL, 2 to FOCUSED, etc.
```

#### 2. Budget consistency with CouncilPlan
```python
def test_council_plan_and_budget_tier_match():
    """Both Council and Budget derive from same risk tier."""
    for tier in range(5):
        route = route_from_tier(tier)
        council_roles = len(route.council_plan.roles)
        budget_sources = len(route.prompt_budget.allowed_sources)
        # Both should increase with tier (higher tiers get richer context)
        assert budget_sources >= 1
        # Tier 3/4 with full Council should have more sources
        if tier >= 3:
            assert council_roles == 6  # full Council
            assert budget_sources >= 5
```

#### 3. Budget immutability across routes
```python
def test_prompt_budget_not_shared_across_routes():
    """Two routes don't share mutable budget state."""
    route_a = route_from_tier(2)
    route_b = route_from_tier(2)
    
    # Mutate route_a's budget sources
    route_a.prompt_budget.allowed_sources.append("injected_garbage")
    
    # route_b should be unaffected
    assert "injected_garbage" not in route_b.prompt_budget.allowed_sources
```

#### 4. Cost posture matches budget tier (semantics)
```python
def test_cost_posture_matches_budget_tier():
    """CostPosture aligns with PromptBudgetTier."""
    # Tier 0/1: MINIMAL budget → MINIMAL cost posture
    assert route_from_tier(0).cost_posture == CostPosture.MINIMAL
    assert route_from_tier(1).cost_posture == CostPosture.MINIMAL
    
    # Tier 2: FOCUSED budget → STANDARD cost posture
    assert route_from_tier(2).cost_posture == CostPosture.STANDARD
    
    # Tier 3/4: BOUNDED/EXPLAINED budget → THOROUGH cost posture
    assert route_from_tier(3).cost_posture == CostPosture.THOROUGH
    assert route_from_tier(4).cost_posture == CostPosture.STANDARD  # human gate, not autonomous
```

#### 5. No regression on existing Relay behavior
```python
def test_relay_routes_unchanged_without_budget():
    """Relay routing logic unaffected by budget addition."""
    for tier in range(5):
        route = route_from_tier(tier)
        # All existing fields should be present and correct
        assert route.mode is not None
        assert route.lanes is not None
        assert route.council_plan is not None
        assert route.reason
        # Only NEW field is prompt_budget
```

### E2E scenario tests (new, post-integration)

#### 6. Budget honored during dispatch (Worker harness integration)
```python
def test_worker_respects_prompt_budget_ceiling():
    """Worker harness enforces max_context_tokens ceiling."""
    # This requires Worker harness changes; test after integration
    # Verify that final prompt tokens ≤ budget.max_context_tokens
```

#### 7. Metrics pipeline (post-dispatch analysis)
```python
def test_dispatch_metrics_logged_outside_prompts():
    """Metrics are captured, not injected back into prompts."""
    # Verify token usage and overhead logged
    # Verify next prompt doesn't include prior metrics
```

---

## Integration Checklist (Future PR)

### Code changes
- [ ] Add `prompt_budget: PromptBudgetPlan` field to `RelayRoute`
- [ ] Update `route_from_assessment()` to call `prompt_budget_for_risk_tier()`
- [ ] Update `route_from_tier()` if needed
- [ ] Export `PromptBudgetPlan` from `__init__.py` if needed

### Tests
- [ ] 5 integration tests above all pass
- [ ] All existing Relay tests still pass (no regression)
- [ ] All existing Intention, Objectives, Aegis tests still pass

### Docs
- [ ] Update `context.md` with new Relay section
- [ ] Update FileMap if RelayRoute signature changes publicly
- [ ] Link this brief from README or MISSION.md

### Future work (not in integration PR)
- [ ] Worker harness reads `RelayRoute.prompt_budget` and enforces ceiling
- [ ] Metrics pipeline captures tokens, time, overhead
- [ ] Dashboards built for cost/overhead tracking
- [ ] Prompt tuning based on budget vs. actual usage

---

## What Is NOT Changed Yet

Explicitly out of scope for integration:

- **Relay.py runtime** — No dispatch logic changes
- **Intention.py** — No progression logic changes
- **Objectives.py** — No objective semantics changes
- **Aegis.py** — No proof logic changes
- **Worker harness** — Still handles its own prompts (future integration)
- **Metrics system** — Not yet built (future work)
- **FileMap.py** — Only updated if we export PromptBudgetPlan

---

## Summary

**RelayRoute** becomes the place where:
- **Cost posture** tells you how thoroughly to deliberate
- **Council plan** tells you which cognitive positions Prime should consider
- **Prompt budget** tells you how lean Worker dispatch must be
- **Context strategy** tells you how to manage session memory

All three (Routing, Cognition, Budget) derive deterministically from risk tier, making Relay dispatch both rich (Prime deliberation) and lean (Worker dispatch).

**Next steps after integration:**
1. Worker harness reads budget and enforces ceiling
2. Metrics pipeline tracks token usage vs. budget
3. Dashboards show Relay overhead vs. vendor baseline
4. Tune budgets based on real usage patterns
