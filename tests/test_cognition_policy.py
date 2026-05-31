import pytest

from meridian_core.aegis import EvidenceSeverity, ProofTrail, evidence_from_cross_check
from meridian_core.cognition_policy import (
    CognitionActionType,
    CognitionDecision,
    CognitionLane,
    cognition_policy_for_tier,
    evaluate_cognition_policy,
)
from meridian_core.relay import ModelRole
from meridian_core.risk import RiskTier


def _clean_trail() -> ProofTrail:
    trail = ProofTrail()
    trail.add(
        evidence_from_cross_check(
            id="info",
            source="tests",
            target="policy",
            summary="informational check passed",
            severity=EvidenceSeverity.INFO,
        )
    )
    return trail


def _blocking_trail() -> ProofTrail:
    trail = ProofTrail()
    trail.add(
        evidence_from_cross_check(
            id="blocker",
            source="tests",
            target="policy",
            summary="proof failed",
            severity=EvidenceSeverity.ERROR,
        )
    )
    return trail


def test_tier_1_is_single_lane_without_human_gate():
    policy = cognition_policy_for_tier(1)

    assert policy.lanes == (CognitionLane.BUILDER,)
    assert policy.requires_review is False
    assert policy.requires_proof is False
    assert policy.requires_human_gate is False


def test_tier_2_requires_review_without_human_gate():
    policy = cognition_policy_for_tier(2)

    assert policy.lanes == (CognitionLane.BUILDER, CognitionLane.REVIEWER)
    assert policy.requires_review is True
    assert policy.requires_proof is False
    assert policy.requires_human_gate is False


def test_tier_3_requires_dual_lane_and_proof():
    policy = cognition_policy_for_tier(3)

    assert policy.lanes == (
        CognitionLane.BUILDER,
        CognitionLane.REVIEWER,
        CognitionLane.VERIFIER,
    )
    assert policy.requires_review is True
    assert policy.requires_proof is True
    assert policy.requires_human_gate is False


def test_tier_4_requires_human_gate():
    policy = cognition_policy_for_tier(4)

    assert CognitionLane.HUMAN in policy.lanes
    assert policy.requires_proof is True
    assert policy.requires_review is True
    assert policy.requires_human_gate is True


def test_missing_proof_blocks_when_policy_requires_proof():
    result = evaluate_cognition_policy(3, proof_trail=None)

    assert result.can_dispatch is False
    assert result.decision is CognitionDecision.BLOCKED_BY_PROOF
    assert result.blocking_reasons == (
        "Aegis proof trail required before Relay dispatch",
    )


def test_tier_2_does_not_block_dispatch_without_proof():
    result = evaluate_cognition_policy(2, proof_trail=None)

    assert result.can_dispatch is True
    assert result.decision is CognitionDecision.ALLOW
    assert result.blocking_reasons == ()


def test_blocking_proof_trail_blocks_dispatch():
    result = evaluate_cognition_policy(3, proof_trail=_blocking_trail())

    assert result.can_dispatch is False
    assert result.decision is CognitionDecision.BLOCKED_BY_PROOF
    assert result.blocking_reasons == ("blocker: proof failed",)


def test_clean_proof_allows_tier_3_dispatch():
    result = evaluate_cognition_policy(3, proof_trail=_clean_trail())

    assert result.can_dispatch is True
    assert result.decision is CognitionDecision.ALLOW
    assert result.blocking_reasons == ()


def test_tier_4_blocks_on_human_gate_after_clean_proof():
    result = evaluate_cognition_policy(4, proof_trail=_clean_trail())

    assert result.can_dispatch is False
    assert result.decision is CognitionDecision.BLOCKED_BY_HUMAN_GATE
    assert result.blocking_reasons == ("human gate approval required",)


def test_tier_4_allows_after_clean_proof_and_human_gate():
    result = evaluate_cognition_policy(
        4,
        proof_trail=_clean_trail(),
        human_gate_approved=True,
    )

    assert result.can_dispatch is True
    assert result.decision is CognitionDecision.ALLOW


def test_result_carries_matching_relay_route():
    result = evaluate_cognition_policy(3, proof_trail=_clean_trail())

    assert result.relay_route.risk_tier == 3
    assert result.relay_route.lanes[0].role is ModelRole.BUILDER
    assert result.relay_route.requires_human_gate is False


def test_accepts_risk_tier_enum():
    policy = cognition_policy_for_tier(RiskTier.TIER_1)

    assert policy.risk_tier == 1


def test_accepts_string_action_type():
    policy = cognition_policy_for_tier(1, action_type="verify")

    assert policy.action_type is CognitionActionType.VERIFY


def test_invalid_tier_raises():
    with pytest.raises(ValueError, match="Unknown risk tier"):
        cognition_policy_for_tier(9)


def test_invalid_action_type_raises():
    with pytest.raises(ValueError, match="Unknown cognition action type"):
        cognition_policy_for_tier(1, action_type="invent")
