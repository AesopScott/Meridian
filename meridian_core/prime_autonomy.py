"""Prime Autonomy domain model for next-action decisions.

Frozen dataclasses and helpers for representing Prime's next deterministic action,
independent of UI/runtime integration. Used for decision logging, audit trails,
and deterministic fallback action selection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, FrozenSet


class PrimeActionType(Enum):
    """Type of action Prime can direct."""
    POLL_SESSION = "poll_session"  # Check session state
    ADVANCE_COGNITION = "advance_cognition"  # Run cognition policy evaluation
    RUN_WORKFLOW = "run_workflow"  # Execute workflow sub-agent
    PAUSE_AND_WAIT = "pause_and_wait"  # Wait for human input or external signal
    ESCALATE_ERROR = "escalate_error"  # Report blocker or error state
    NO_OP = "no_op"  # Safe default: do nothing


class PrimeActionConfidence(Enum):
    """Confidence in action selection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"  # Default safe action when uncertain


class PrimeActionRiskTier(Enum):
    """Risk level of the action."""
    SAFE = "safe"  # Read-only, no state changes
    LOW = "low"  # Minor state changes, easily reversible
    MEDIUM = "medium"  # Significant changes, requires audit trail
    HIGH = "high"  # Major changes, human gate required


class PrimeActionSource(Enum):
    """Source of the action decision."""
    COGNITION_POLICY = "cognition_policy"
    WORKFLOW_RESULT = "workflow_result"
    SESSION_STATE = "session_state"
    ERROR_RECOVERY = "error_recovery"
    HUMAN_OVERRIDE = "human_override"


@dataclass(frozen=True)
class PrimeNextAction:
    """Immutable representation of Prime's next deterministic action.

    Fields define the action type, target scope, decision quality, risk level,
    blockers, human-gate requirement, rationale, and evidence references.
    """

    action_type: PrimeActionType
    confidence: PrimeActionConfidence
    risk_tier: PrimeActionRiskTier
    source: PrimeActionSource

    # Target scope: which harness/lane/project this action targets
    target_harness: Optional[str] = None  # e.g., "Echo", "Atlas", "Relay"
    target_lane: Optional[str] = None      # e.g., "cognition", "workflow"
    target_project: Optional[str] = None   # e.g., "Meridian", external

    # Decision context
    rationale: str = ""  # Why this action was chosen
    evidence: FrozenSet[str] = field(default_factory=frozenset)  # References to proof/audit log entries

    # Constraints
    human_gate_required: bool = False  # Must wait for human approval before executing
    blockers: FrozenSet[str] = field(default_factory=frozenset)  # Blocking conditions preventing execution

    def is_blocked(self) -> bool:
        """Return True if any blockers prevent execution."""
        return bool(self.blockers)

    def is_executable(self) -> bool:
        """Return True only when no blocker or pending human gate prevents execution."""
        return not self.is_blocked() and not self.human_gate_required


def select_prime_next_action(
    action_type: Optional[PrimeActionType] = None,
    confidence: Optional[PrimeActionConfidence] = None,
    risk_tier: Optional[PrimeActionRiskTier] = None,
    source: Optional[PrimeActionSource] = None,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Deterministic helper to construct a Prime next-action with fallback defaults.

    Any None input falls back to a safe default, ensuring a valid action always returns.
    Returns a frozen immutable PrimeNextAction ready for decision logging.
    """

    # Safe defaults for each field
    final_action_type = action_type or PrimeActionType.PAUSE_AND_WAIT
    final_confidence = confidence or PrimeActionConfidence.FALLBACK
    final_risk_tier = risk_tier or PrimeActionRiskTier.SAFE
    final_source = source or PrimeActionSource.ERROR_RECOVERY

    # Convert lists to frozen sets
    final_evidence = frozenset(evidence or [])
    final_blockers = frozenset(blockers or [])

    return PrimeNextAction(
        action_type=final_action_type,
        confidence=final_confidence,
        risk_tier=final_risk_tier,
        source=final_source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=final_evidence,
        human_gate_required=human_gate_required,
        blockers=final_blockers,
    )


@dataclass(frozen=True)
class ProjectState:
    """Immutable snapshot of project/lane/queue state for Prime action selection.

    Provides a deterministic input shape for select_prime_project_action()
    without requiring Echo/Atlas/model calls. All fields are plain data;
    no filesystem, network, or session side effects.
    """

    lane_id: str = ""
    active_task: Optional[str] = None
    next_candidate: Optional[str] = None
    cadence_count: int = 0
    cadence_limit: int = 3
    review_gate_blocked: bool = False
    human_gate_required: bool = False
    blockers: FrozenSet[str] = field(default_factory=frozenset)
    queue_state: str = "idle"  # idle, running, blocked, paused
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE
    confidence: PrimeActionConfidence = PrimeActionConfidence.FALLBACK
    target_harness: Optional[str] = None
    target_lane: Optional[str] = None


def select_prime_project_action(state: ProjectState) -> PrimeNextAction:
    """Deterministic project-state → Prime action selector.

    Chooses the next Prime action from project/backlog/lane/tier/review-gate
    state without any model calls. Priority ordering:

    1. Blockers present → ESCALATE_ERROR
    2. Review gate blocked (cadence_count >= cadence_limit) → PAUSE_AND_WAIT
    3. Human gate required → PAUSE_AND_WAIT
    4. No active task AND no next candidate → ESCALATE_ERROR
    5. Lane is blocked or paused → PAUSE_AND_WAIT
    6. Active task present → ADVANCE_COGNITION (work ready)
    7. Next candidate present but no active task → POLL_SESSION
    8. Default safe fallback → PAUSE_AND_WAIT

    Returns a fully-populated PrimeNextAction with rationale, evidence, risk,
    confidence, blockers, and human-gate status reflecting the decision.
    """

    # Build evidence and rationale as we go
    evidence_parts = []
    rationale_parts = []

    # 1. Blockers take absolute priority
    if state.blockers:
        evidence_parts.append(f"blockers:{','.join(sorted(state.blockers))}")
        rationale_parts.append(
            f"Blockers present: {', '.join(sorted(state.blockers))}"
        )
        return PrimeNextAction(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 2. Review gate blocks further work
    if state.review_gate_blocked:
        evidence_parts.append(
            f"review_gate:blocked(cadence={state.cadence_count}/{state.cadence_limit})"
        )
        rationale_parts.append(
            f"Review gate blocked: cadence {state.cadence_count}/{state.cadence_limit}"
        )
        return PrimeNextAction(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.COGNITION_POLICY,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 2b. Cadence count >= limit (explicit check)
    if state.cadence_count >= state.cadence_limit:
        evidence_parts.append(
            f"cadence:limit(cadence={state.cadence_count}/{state.cadence_limit})"
        )
        rationale_parts.append(
            f"Cadence limit reached: {state.cadence_count}/{state.cadence_limit}"
        )
        return PrimeNextAction(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.COGNITION_POLICY,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 3. Human gate
    if state.human_gate_required:
        evidence_parts.append("human_gate:pending")
        rationale_parts.append("Human gate required — awaiting approval")
        return PrimeNextAction(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.HUMAN_OVERRIDE,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=True,
            blockers=state.blockers,
        )

    # 4. No active task and no next candidate → nothing to do
    if not state.active_task and not state.next_candidate:
        evidence_parts.append("queue:empty")
        rationale_parts.append("No active task and no next candidate in queue")
        return PrimeNextAction(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=False,
            blockers=state.blockers,
        )

    # 5. Lane is blocked or paused
    if state.queue_state in ("blocked", "paused"):
        evidence_parts.append(f"queue_state:{state.queue_state}")
        rationale_parts.append(f"Lane is {state.queue_state}")
        return PrimeNextAction(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 6. Active task present — work is ready
    if state.active_task:
        evidence_parts.append(f"active_task:present")
        rationale_parts.append(
            f"Active task ready: {state.active_task[:80]}{'...' if len(state.active_task or '') > 80 else ''}"
        )
        return PrimeNextAction(
            action_type=PrimeActionType.ADVANCE_COGNITION,
            confidence=state.confidence,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.COGNITION_POLICY,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 7. Next candidate present but no active task — poll for promotion
    if state.next_candidate:
        evidence_parts.append("next_candidate:present")
        rationale_parts.append("Next candidate task awaiting promotion")
        return PrimeNextAction(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_harness=state.target_harness,
            target_lane=state.target_lane,
            rationale="; ".join(rationale_parts),
            evidence=frozenset(evidence_parts),
            human_gate_required=state.human_gate_required,
            blockers=state.blockers,
        )

    # 8. Default safe fallback
    evidence_parts.append("fallback:default")
    rationale_parts.append("No matching condition — defaulting to safe pause")
    return PrimeNextAction(
        action_type=PrimeActionType.PAUSE_AND_WAIT,
        confidence=PrimeActionConfidence.FALLBACK,
        risk_tier=PrimeActionRiskTier.SAFE,
        source=PrimeActionSource.ERROR_RECOVERY,
        target_harness=state.target_harness,
        target_lane=state.target_lane,
        rationale="; ".join(rationale_parts),
        evidence=frozenset(evidence_parts),
        human_gate_required=False,
        blockers=state.blockers,
    )


def make_prime_next_action(
    action_type: PrimeActionType,
    confidence: PrimeActionConfidence,
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE,
    source: PrimeActionSource = PrimeActionSource.ERROR_RECOVERY,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Strict constructor for Prime next-action: requires action_type and confidence.

    Falls back only on optional fields. Use this when you have explicit action intent.
    """

    return select_prime_next_action(
        action_type=action_type,
        confidence=confidence,
        risk_tier=risk_tier,
        source=source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=evidence,
        human_gate_required=human_gate_required,
        blockers=blockers,
    )
