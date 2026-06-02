# Relay Proof Payload Consumer Checklist

**Status:** V0 downstream consumer guidance  
**Date:** 2026-06-12  
**Owner:** Build 1 (Relay proof payload serialization), Bifrost/Prime (consumption)  
**Audience:** Bifrost UI engineers, Prime routing, Build 3 (FileMap registration)  
**Related:** `docs/relay-bifrost-proof-payload-contract.md`, `docs/bifrost-right-panel-mode-contract.md`

---

## Purpose

This checklist guides downstream consumers (Bifrost, Prime, UI) on integrating and displaying the Relay proof payload. The proof payload is pre-serialized by Relay and contains Aegis gate evidence (decision, severity, evidence IDs, waiver status, explanation, fallback blockers). This document covers safe consumption patterns without calling Relay internals or making Aegis decisions at display time.

---

## Field Consumption Guide

### Gate Decision (`gate_decision: str | None`)

**Type:** Human-facing field  
**Values:** `"allow"`, `"demote"`, `"block"`, `"human_gate"`, or `None`  
**How to consume:**
- Map to user-readable label: "Allowed", "Demoted", "Blocked", "Escalation Required"
- Display as a status badge or text indicator in the right panel (Bifrost User Session mode)
- Use neutral tone; do not interpret as success/failure unless severity warrants it
- If `None`, omit or display as "no decision"

**Bifrost Right Panel Rendering:**
- `allow` → Green/informational badge: "Allowed"
- `demote` → Yellow/caution badge: "Demoted"
- `block` → Red/error badge: "Blocked"
- `human_gate` → Orange/escalation badge: "Escalation Required"

### Severity (`severity: str | None`)

**Type:** Human-facing field  
**Values:** `"INFO"`, `"WARNING"`, `"ERROR"`, or `None`  
**How to consume:**
- Display as visual indicator (icon/color) paired with gate decision
- Use standard severity color scheme: INFO = gray, WARNING = yellow, ERROR = red
- Severity reflects the Aegis evidence level, not a judgment of Relay's decision
- If `None`, omit or render as "no severity"

**Bifrost Right Panel Rendering:**
- `INFO` → Gray icon/text: low urgency, informational context
- `WARNING` → Yellow icon/text: attention needed, review evidence
- `ERROR` → Red icon/text: critical, blocking, or high-risk condition

### Evidence IDs (`evidence_ids: tuple[str, ...]`)

**Type:** Audit field  
**Values:** Ordered tuple of evidence ID strings (e.g., `("ev-1", "ev-2", "ev-3")`)  
**How to consume:**
- Display as ordered list of evidence references
- Preserve order; do not sort or reorder
- If Bifrost has Aegis surface integration, make IDs clickable links to evidence proof review
- If tuple is empty, display as "no evidence" or omit field
- Do not call Aegis validators to resolve IDs; display IDs only

**Bifrost Right Panel Rendering:**
- List evidence IDs in order: "Evidence: ev-1, ev-2, ev-3"
- Optional: link each ID to Aegis proof surface if available (read-only)
- If empty: omit or show "(no evidence)"

### Waiver Present (`waiver_present: bool`)

**Type:** Audit field  
**Values:** `True` or `False`  
**How to consume:**
- Display only if `True`; omit if `False`
- Neutral tone; acknowledges waiver was recorded
- Do not allow Bifrost to create, modify, or delete waivers
- Do not use waiver presence to override gate decision display

**Bifrost Right Panel Rendering:**
- If `True`: "✓ Waiver applied" or similar neutral indicator
- If `False`: omit field entirely

### Explanation Text (`explanation: str`)

**Type:** Human-facing field  
**Values:** Raw explanation string from Aegis gate evaluation (may be empty)  
**How to consume:**
- Display as plain text; no markup, no interpretation by Bifrost
- If empty string, display as "(no explanation)" or omit field
- Do not edit, truncate, or reformat explanation text
- Explanation is informational only; never use it to override gate decision

**Bifrost Right Panel Rendering:**
- Display in full beneath gate decision and severity
- Example: "Gate Decision: Demoted | Severity: WARNING | Explanation: Cost constraint applied"
- If empty: omit or show "(no explanation)"

### Fallback Blockers from Aegis (`fallback_blockers_from_aegis: tuple[str, ...]`)

**Type:** Audit/debugging field  
**Values:** Ordered tuple of blocker strings (e.g., `("aegis_gate_blocked", "aegis_other")`)  
**How to consume:**
- Display only to Relay operators and developers; not to end users
- Ordered tuple; preserve order
- Blockers are technical references; use for debugging Relay fallback state
- If tuple is empty, omit field
- Do not expose blockersas user-facing messaging

**Bifrost Right Panel Rendering:**
- Hidden from end-user view
- Available in Harness mode (debug/operator view only)
- Display as ordered list: "Fallback Blockers: aegis_gate_blocked, aegis_other"
- If empty: omit field

---

## Handling Absent or Empty Fields

### Empty Evidence IDs

**Scenario:** `evidence_ids = ()`

**Action:**
- Display "no evidence" or omit field
- Do not call Aegis to fetch evidence
- Continue displaying gate decision and severity normally

### Empty Explanation

**Scenario:** `explanation = ""`

**Action:**
- Display "(no explanation)" or omit field
- Do not suppress gate decision or severity
- Continue showing gate decision and waiver status

### No Gate Decision

**Scenario:** `gate_decision = None`

**Action:**
- Display "no decision" or omit field
- Still show severity if present
- Show evidence IDs and waiver status if present
- Do not hide the entire proof payload section

### Missing Severity

**Scenario:** `severity = None`

**Action:**
- Omit severity icon/indicator
- Display gate decision normally
- Use neutral/gray coloring for associated elements

### Partial Evidence

**Scenario:** `evidence_ids = ("ev-1",)` with only one ID

**Action:**
- Display single ID in order
- Do not assume more IDs will be added
- Preserve as tuple (even if it appears as a list after JSON deserialization)

---

## Display Examples

### Example 1: Full Evidence with Waiver

```
Gate Decision: Blocked
Severity: ERROR
Evidence: ev-block-1, ev-cost-violation-2
Waiver Applied: Yes
Explanation: Security validation failed; waiver recorded for cost exception
Fallback Blockers (debug): aegis_gate_blocked
```

### Example 2: Demote with Partial Evidence

```
Gate Decision: Demoted
Severity: WARNING
Evidence: ev-cost-1
Explanation: Cost constraint applied; upgrade available under different vendor
```

### Example 3: Allow with No Evidence

```
Gate Decision: Allowed
Severity: INFO
(no evidence)
```

### Example 4: No Decision (Incomplete Audit)

```
(no decision)
Severity: ERROR
Evidence: ev-audit-1, ev-audit-2
Explanation: Audit incomplete; decision pending
```

---

## JSON Deserialization and Type Handling

### Tuple-to-List Conversion

**Scenario:** When proof payload is serialized to JSON and deserialized back to Python:
- `evidence_ids: tuple[str, ...]` serializes as JSON array `["ev-1", "ev-2"]`
- Upon JSON deserialization, becomes Python `list` (not `tuple`)

**Action:**
- Treat deserialized lists as equivalent to tuples for display/comparison
- Do not assume `isinstance(evidence_ids, tuple)` after JSON round-trip
- If tuple-on-read is required, document explicitly in deserialization contract

### String Fields Preservation

**Scenario:** `explanation` and `gate_decision` are strings

**Action:**
- Preserve as-is; do not escape, encode, or interpret
- Safe to display in HTML/UI: no markup is expected in these fields
- Do not apply string formatting or truncation

---

## Caching and Comparison

### Safe Caching

**Why:** Multiple calls to `to_dict()` on the same `AegisGateEvidenceSummary` instance return identical output (deterministic).

**How:**
- Cache proof payload dictionaries by a session ID or decision record ID
- Compare cached vs. fresh payloads field-by-field for audit trails
- Invalidate cache if decision record changes or session ends

### Safe Comparison

**Operation:** Comparing two proof payloads for equivalence

**Pattern:**
```python
# Safe: all values are immutable
payload_a = {"gate_decision": "block", "evidence_ids": ("ev-1",), ...}
payload_b = {"gate_decision": "block", "evidence_ids": ("ev-1",), ...}

if payload_a == payload_b:
    # Payloads are identical
    pass
```

**Note:** Do not mutate payload values; treat dictionaries as read-only after deserialization.

---

## Out-of-Scope (DO NOT DO)

The following must NOT be done by downstream consumers:

### ✗ No Relay Runtime Calls

- Do not call `RelayExecutionSummary.aegis_gate_evidence_summary()`
- Do not call any Relay executor methods
- The proof payload is pre-serialized and passed to Bifrost; do not compute it at display time

### ✗ No Aegis Calls

- Do not call Aegis validators, proof checkers, or gate evaluators
- Do not fetch additional evidence using evidence IDs from Aegis
- Decisions are already made by Relay and Aegis before display

### ✗ No Payload Mutations

- Do not modify, store-cache-and-mutate, or locally alter proof payload fields
- Treat all fields as read-only
- Do not attempt to create, update, or delete gate decisions from the UI

### ✗ No UI Overrides

- Do not expose gate decision override, waiver creation, or evidence re-evaluation buttons in Bifrost
- These belong to the Review Console, not the cockpit
- Bifrost is display-only; Relay and Aegis own decision authority

### ✗ No FileMap or Contract Changes

- Build 1 provides the proof payload serialization
- Build 3 registers the contract in FileMap
- Bifrost does not register new proof payload entries or contract variations

### ✗ No Model Calls or Decisions

- Do not use proof payload fields to make routing decisions
- Do not call models based on gate decision or evidence
- Relay and Aegis make all model routing and gating decisions before proof is generated

---

## Integration Verification Checklist

Use this checklist to verify correct consumption and display of the Relay proof payload:

### Data Handling
- [ ] Proof payload is received pre-serialized from Relay (not computed by Bifrost)
- [ ] All fields are read-only; no mutations attempted
- [ ] Tuple fields (evidence_ids, fallback_blockers_from_aegis) are treated as ordered sequences
- [ ] JSON deserialization: tuples converted to lists are handled safely
- [ ] Caching strategy respects deterministic output guarantees

### Display Rendering
- [ ] Gate decision is displayed with color/badge mapping (green/yellow/red/orange)
- [ ] Severity is displayed as visual indicator (icon/color) alongside gate decision
- [ ] Evidence IDs are displayed in order as comma-separated list or linked items
- [ ] Waiver status is shown only if `waiver_present == True`
- [ ] Explanation text is displayed as plain text (no markup, no truncation)
- [ ] Empty/None fields are handled gracefully (omitted or marked as "none")

### Field-Specific Handling
- [ ] `gate_decision`: Maps to user-readable label and display color
- [ ] `severity`: Renders as visual indicator (gray/yellow/red)
- [ ] `evidence_ids`: Displayed in order; may be linked to Aegis proof surface if available
- [ ] `waiver_present`: Shown only if `True`; neutral tone
- [ ] `explanation`: Rendered as plain text; not edited or truncated
- [ ] `fallback_blockers_from_aegis`: Hidden from end-user view; debug-only in Harness mode

### Bifrost Right Panel Integration
- [ ] Proof payload section appears in User Session mode (when routing decisions exist)
- [ ] Gate decision and severity are prominently displayed
- [ ] Evidence, waiver, and explanation are displayed below gate decision
- [ ] Fallback blockers are hidden from end-user view (debug-only)
- [ ] Proof payload display respects right-panel text-size slider
- [ ] Display uses consistent color coding: user text yellow, paths orange, labels standard

### Out-of-Scope Compliance
- [ ] No Relay runtime calls in proof payload consumption
- [ ] No Aegis validator calls or evidence resolution
- [ ] No payload mutations or local alterations
- [ ] No gate decision override, waiver creation, or evidence re-evaluation UI in Bifrost
- [ ] No model calls or routing decisions based on proof payload
- [ ] No FileMap edits or contract modifications by Bifrost

### Testing and Validation
- [ ] Text review: proof payload display matches contract examples
- [ ] Empty payload: all fields are `None`/empty; display remains readable
- [ ] Full payload: all fields populated; display is clear and consistent
- [ ] Multiple payloads: caching and comparison work correctly
- [ ] UI regression: no layout or visual changes when proof payload is added
- [ ] Keyboard accessibility: proof payload display is keyboard-navigable

---

## Related Documents

- `docs/relay-bifrost-proof-payload-contract.md` — Stable proof payload keys, immutability, determinism, and display intent (Build 1)
- `docs/bifrost-right-panel-mode-contract.md` — Bifrost right-panel surface modes, interaction rules, and verification checklist (Bifrost)
- `docs/FileMap.md` — Living knowledge tracker for documentation registration (Build 3)
- `meridian_core/relay_executor.py` — Implementation of `AegisGateEvidenceSummary.to_dict()` and proof payload serialization (Build 1)
- `tests/test_relay_executor.py` — Test suite proving payload immutability, determinism, and correct field handling (Build 1)

---

## Handoff Note for Build 3

Once this checklist and the proof payload contract clear Codex review:

1. **Build 3 action:** Register both `docs/relay-bifrost-proof-payload-contract.md` and `docs/relay-bifrost-proof-payload-consumer-checklist.md` in `docs/FileMap.md` under the Aegis/Proof Harness section.

2. **Bifrost action:** Use this checklist to integrate proof payload display into the right-panel User Session mode. Follow the field consumption guide and display examples.

3. **Testing:** Before marking integration complete, verify against the integration verification checklist above.

4. **No runtime changes:** Build 1 delivers serialization; Bifrost displays. Relay, Aegis, and decision authority remain unchanged.
