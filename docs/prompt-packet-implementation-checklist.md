# Prompt Packet Implementation Checklist

**Status:** Implementation planning checklist — ready for future build lane  
**Purpose:** Concrete checklist for implementing Prompt Packet domain model  
**Reference:** `docs/prompt-packet-design-brief.md`

---

## Files to Touch

Create (new):
- `meridian_core/prompt_packet.py` — Domain model, validation, creation
- `tests/test_prompt_packet.py` — Unit tests for all validations

Update (if needed):
- `meridian_core/__init__.py` — Export PromptPacket, PromptPacketError (optional, defer to end)
- May touch `meridian_core/relay.py` later (Phase 2 integration), NOT in this slice

---

## Files NOT to Touch

Do NOT edit:
- `meridian_core/prompt_budget.py` — Keep as-is (Budget sets rules)
- `meridian_core/prompt_metrics.py` — Keep as-is (Metrics measure)
- `meridian_core/relay.py` — Don't integrate yet (Phase 2 work)
- `docs/FileMap.md` — Don't update (Build 1 owns this)
- Package API exports — Don't add until design is proven
- `tests/test_prompt_budget.py` — Don't change (locked by Build 3 polling)

---

## First Tests to Write (in order)

### 1. Creation and Immutability
```python
def test_prompt_packet_creation():
    """Can create a valid PromptPacket."""
    packet = PromptPacket(
        packet_id="test_1",
        serialized_prompt="Test prompt",
        prompt_tokens=2,
        max_context_tokens=100,
        allowed_sources=["direct_input"],
        construction_time_ms=10.5,
        source_lineage={"direct_input": 2},
        tier=2,
        lane_role="builder",
    )
    assert packet.packet_id == "test_1"
    assert packet.is_valid  # Should start valid if no errors

def test_prompt_packet_immutable():
    """PromptPacket is immutable (frozen)."""
    packet = PromptPacket(...)
    with pytest.raises((AttributeError, TypeError)):
        packet.prompt_tokens = 999  # Can't mutate
```

### 2. Budget Compliance Validation
```python
def test_budget_compliance_pass():
    """Packet with tokens <= max passes validation."""
    packet = PromptPacket(..., prompt_tokens=100, max_context_tokens=500, ...)
    assert packet.is_valid
    assert len(packet.validation_errors) == 0

def test_budget_compliance_fail():
    """Packet with tokens > max fails validation."""
    packet = PromptPacket(..., prompt_tokens=501, max_context_tokens=500, ...)
    assert not packet.is_valid
    assert "budget" in " ".join(packet.validation_errors).lower()
```

### 3. Source Compliance Validation
```python
def test_source_compliance_pass():
    """Packet with all sources in allowed list passes."""
    packet = PromptPacket(
        ...,
        source_lineage={"direct_input": 50, "task_context": 50},
        allowed_sources=["direct_input", "task_context"],
        ...
    )
    assert packet.is_valid

def test_source_compliance_fail():
    """Packet with source not in allowed list fails."""
    packet = PromptPacket(
        ...,
        source_lineage={"direct_input": 80, "debug_logs": 20},
        allowed_sources=["direct_input"],
        ...
    )
    assert not packet.is_valid
    assert "source" in " ".join(packet.validation_errors).lower()
```

### 4. Serialization Integrity
```python
def test_serialization_non_empty():
    """Packet requires non-empty prompt."""
    packet = PromptPacket(..., serialized_prompt="", ...)
    assert not packet.is_valid
    assert "empty" in " ".join(packet.validation_errors).lower()

def test_serialization_is_string():
    """Packet requires prompt to be string."""
    # Can't construct with wrong type if using type hints, but test the intent
    assert isinstance(packet.serialized_prompt, str)
```

### 5. Lineage Integrity
```python
def test_lineage_totals_match():
    """Lineage tokens should sum to or be less than packet tokens."""
    packet = PromptPacket(
        ...,
        prompt_tokens=100,
        source_lineage={"direct_input": 60, "task_context": 40},  # 100 total
        ...
    )
    assert packet.is_valid

def test_lineage_totals_exceed():
    """Lineage tokens exceeding packet tokens fails."""
    packet = PromptPacket(
        ...,
        prompt_tokens=100,
        source_lineage={"direct_input": 80, "task_context": 40},  # 120 > 100
        ...
    )
    assert not packet.is_valid
    assert "lineage" in " ".join(packet.validation_errors).lower()
```

### 6. Construction Time Sanity
```python
def test_construction_time_valid():
    """Construction time within bounds passes."""
    packet = PromptPacket(..., construction_time_ms=50.5, ...)
    assert packet.is_valid

def test_construction_time_negative():
    """Negative construction time fails."""
    packet = PromptPacket(..., construction_time_ms=-10.0, ...)
    assert not packet.is_valid

def test_construction_time_unrealistic():
    """Construction time > 30 seconds fails (sanity check)."""
    packet = PromptPacket(..., construction_time_ms=30001.0, ...)
    assert not packet.is_valid
```

### 7. No Mutations Across Instances
```python
def test_source_lineage_isolated():
    """Modifying lineage dict doesn't affect next packet."""
    lineage1 = {"direct_input": 100}
    packet1 = PromptPacket(..., source_lineage=lineage1, ...)
    
    # Mutate original dict
    lineage1["injected"] = 50
    
    # Create second packet with same lineage
    lineage2 = {"direct_input": 100}
    packet2 = PromptPacket(..., source_lineage=lineage2, ...)
    
    assert packet1.source_lineage == packet2.source_lineage
    assert "injected" not in packet2.source_lineage
```

---

## Smallest Domain Model Shape

### Core Class
```python
@dataclass(frozen=True)
class PromptPacket:
    # Required
    packet_id: str
    serialized_prompt: str
    prompt_tokens: int
    max_context_tokens: int
    allowed_sources: tuple[str, ...]  # Or frozenset
    construction_time_ms: float
    source_lineage: dict[str, int]  # Frozen copy
    tier: int
    lane_role: str
    
    # Computed on creation
    is_valid: bool = field(init=False)
    validation_errors: tuple[str, ...] = field(init=False)
    created_at: datetime = field(init=False, default_factory=now)
    
    def __post_init__(self):
        # Validation logic here
        # Set is_valid and validation_errors via object.__setattr__
```

### Error Handling
```python
class PromptPacketError(ValueError):
    """Base exception for Prompt Packet validation."""
    pass

class BudgetExceededError(PromptPacketError):
    """Packet tokens exceed max budget."""
    pass

# Use is_valid flag, not exceptions
# Exceptions only for programming errors (wrong type, missing field)
```

---

## Validation Rules (Ordered)

1. **Budget compliance** — `prompt_tokens <= max_context_tokens`
2. **Source compliance** — all sources in `source_lineage` must be in `allowed_sources`
3. **Serialization integrity** — `serialized_prompt` non-empty and string type
4. **Construction time sanity** — `0 <= construction_time_ms < 30000`
5. **Lineage integrity** — `sum(source_lineage.values()) <= prompt_tokens`

If ANY check fails, set `is_valid = False` and populate `validation_errors` with messages.

---

## Connection to Prompt Budget

### What PromptBudget Provides
- `max_context_tokens` — ceiling for Packet to enforce
- `allowed_sources` — list of sources Packet can use
- Reason (passed through for logging, not validation)

### Packet's Job
- Receive Budget rules at creation time
- Enforce: prompt_tokens ≤ max, sources ⊆ allowed
- Report: is_valid and validation_errors
- Track: which sources contributed how many tokens (source_lineage)

### Flow
```
PromptBudgetPlan (rules)
    ↓
PromptPacket creation (receive budget rules, validate)
    ├─ If valid → can proceed to dispatch
    └─ If invalid → escalate to Prime
```

---

## Later Feed to Prompt Metrics

### What Packet Provides to Metrics
- `prompt_tokens` — already measured
- `construction_time_ms` — already measured
- `packet_id` — for correlation

### Metrics Sample Creation (Phase 2)
```python
# After Packet is created and valid, dispatch it
sample = PromptMetricSample(
    sample_id=packet.packet_id,
    prompt_tokens=packet.prompt_tokens,
    construction_time_ms=packet.construction_time_ms,
    total_response_time_ms=...,  # Measured post-dispatch
    time_to_first_token_ms=...,   # Optional
    native_baseline_ms=...,       # Optional
)
```

No changes to Prompt Packet needed for this integration — just provide fields to consume.

---

## What Remains Out of Worker Prompts

Explicitly NOT serialized or sent:
- `packet_id` (internal correlation only)
- `construction_time_ms` (Relay metric, not worker's concern)
- `source_lineage` (internal accounting)
- `max_context_tokens` (boundary-checked, not for worker)
- `allowed_sources` (used to build packet, not for worker)
- `tier`, `lane_role` (metadata for routing/tracing)
- `is_valid`, `validation_errors` (if invalid, packet never sent)
- `created_at` (timestamp for logging)

Only `serialized_prompt` is sent. Everything else is metadata.

---

## Open Questions for Codex Review

1. **Frozen dataclass vs named tuple?**
   - Frozen dataclass more Pythonic for this codebase
   - Named tuple slightly more lightweight
   - Recommendation: frozen dataclass (matches PromptBudgetPlan style)

2. **Where should PromptPacket live?**
   - New module `meridian_core/prompt_packet.py` (recommended, keep concern separate)
   - In `relay.py` as nested class (too coupled, defer)
   - In `prompt_budget.py` (mixes concerns, don't do this)

3. **Should validation errors be exceptions or flags?**
   - Current design: `is_valid` flag + `validation_errors` list (non-throwing)
   - Alternative: raise on invalid (fails fast)
   - Recommendation: flags (allows Prime to see all errors, decide response)

4. **Should source_lineage be dict or frozenset?**
   - Dict recommended: tracks token count per source (useful for tuning)
   - Frozenset alternative: just presence/absence (simpler)
   - Recommendation: dict (more information for metrics/tuning)

5. **When to call Packet creation: during Relay dispatch or before?**
   - This checklist doesn't implement integration, just domain model
   - Deferred to Phase 2 (Relay instrumentation design)
   - Packet can be built standalone or integrated into route logic

6. **Should Packet store the full PromptBudgetPlan or just the values it needs?**
   - Current design: individual fields (max_context_tokens, allowed_sources)
   - Alternative: store reference to PromptBudgetPlan object
   - Recommendation: individual fields (decouples, prevents circular reference)

---

## Implementation Readiness

✅ Design brief complete (`prompt-packet-design-brief.md`)  
✅ Validation rules concrete and testable  
✅ Test checklist specific and implementable  
✅ Open questions identified for design review  
⏳ Ready for implementation when Codex approves  

---

## Summary

Simple, bounded implementation:
- One domain class: PromptPacket
- One error type: PromptPacketError
- Seven test groups covering all validations
- Clear connection to Budget (rules) and Metrics (data)
- No worker prompt leakage
- Open questions for Codex review before build

Ready for implementation in a focused, Haiku-sized build lane.
