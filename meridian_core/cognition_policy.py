"""Deterministic cognition policy before Relay model dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .aegis import ProofTrail
from .relay import RelayRoute, route_from_tier
from .risk import RiskTier, assess_tier


class CognitionActionType(Enum):
    LOCAL_LOGIC = "local_logic"
    BUILD = "build"
    REVIEW = "review"
    VERIFY = "verify"
    RELEASE = "release"
    DESTRUCTIVE = "destructive"


class CognitionLane(Enum):
    LOCAL = "local"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"
    HUMAN = "human"


class CognitionDecision(Enum):
    ALLOW = "allow"
    BLOCKED_BY_PROOF = "blocked_by_proof"
    BLOCKED_BY_HUMAN_GATE = "blocked_by_human_gate"


@dataclass(frozen=True)
class CognitionPolicy:
    action_type: CognitionActionType
    risk_tier: int
    lanes: tuple[CognitionLane, ...]
    requires_proof: bool
    requires_review: bool
    requires_human_gate: bool
    reason: str


@dataclass(frozen=True)
class CognitionPolicyResult:
    policy: CognitionPolicy
    decision: CognitionDecision
    blocking_reasons: tuple[str, ...]
    relay_route: RelayRoute

    @property
    def can_dispatch(self) -> bool:
        return self.decision is CognitionDecision.ALLOW


def cognition_policy_for_tier(
    tier: int | RiskTier,
    action_type: str | CognitionActionType = CognitionActionType.BUILD,
) -> CognitionPolicy:
    tier_num = _coerce_tier(tier)
    action = _coerce_action_type(action_type)
    assessment = assess_tier(tier_num)

    lanes_by_tier: dict[int, tuple[CognitionLane, ...]] = {
        0: (CognitionLane.LOCAL,),
        1: (CognitionLane.BUILDER,),
        2: (CognitionLane.BUILDER, CognitionLane.REVIEWER),
        3: (CognitionLane.BUILDER, CognitionLane.REVIEWER, CognitionLane.VERIFIER),
        4: (
            CognitionLane.BUILDER,
            CognitionLane.REVIEWER,
            CognitionLane.VERIFIER,
            CognitionLane.HUMAN,
        ),
    }

    return CognitionPolicy(
        action_type=action,
        risk_tier=tier_num,
        lanes=lanes_by_tier[tier_num],
        requires_proof=assessment.requires_aegis_proof,
        requires_review=tier_num >= 2,
        requires_human_gate=assessment.requires_human_gate,
        reason=assessment.reason,
    )


def evaluate_cognition_policy(
    tier: int | RiskTier,
    action_type: str | CognitionActionType = CognitionActionType.BUILD,
    proof_trail: ProofTrail | None = None,
    human_gate_approved: bool = False,
) -> CognitionPolicyResult:
    policy = cognition_policy_for_tier(tier, action_type)
    route = route_from_tier(policy.risk_tier, reason=policy.reason)
    blockers: list[str] = []

    if policy.requires_proof:
        if proof_trail is None:
            blockers.append("Aegis proof trail required before Relay dispatch")
        else:
            blockers.extend(
                f"{evidence.id}: {evidence.summary}"
                for evidence in proof_trail.blocking()
            )

    if policy.requires_human_gate and not human_gate_approved:
        blockers.append("human gate approval required")

    decision = CognitionDecision.ALLOW
    if any(reason != "human gate approval required" for reason in blockers):
        decision = CognitionDecision.BLOCKED_BY_PROOF
    elif blockers:
        decision = CognitionDecision.BLOCKED_BY_HUMAN_GATE

    return CognitionPolicyResult(
        policy=policy,
        decision=decision,
        blocking_reasons=tuple(blockers),
        relay_route=route,
    )


def _coerce_tier(tier: int | RiskTier) -> int:
    return tier.value if isinstance(tier, RiskTier) else int(tier)


def _coerce_action_type(
    action_type: str | CognitionActionType,
) -> CognitionActionType:
    if isinstance(action_type, CognitionActionType):
        return action_type
    try:
        return CognitionActionType(action_type)
    except ValueError as exc:
        valid = ", ".join(action.value for action in CognitionActionType)
        raise ValueError(f"Unknown cognition action type: {action_type!r}. Valid: {valid}.") from exc
