"""Tests for the Relay Routing slice (meridian_core/relay.py)."""

from __future__ import annotations

import pytest

from meridian_core.council import CouncilPlan, CouncilRole
from meridian_core.prompt_budget import PromptBudgetPlan, PromptBudgetTier
from meridian_core.relay import (
    AccessRouteClass,
    ContextHealth,
    ContextStrategy,
    CostPosture,
    LatencyPosture,
    ModelRole,
    PrivacyLevel,
    RelayLane,
    RelayRoute,
    RelayRouteAudit,
    RouteTrustState,
    RoutingMode,
    SessionAction,
    VendorRouteKind,
    route_from_assessment,
    route_from_tier,
)
from meridian_core.risk import RiskTier, assess_tier


# ---------------------------------------------------------------------------
# Tier 0 -- no model lanes
# ---------------------------------------------------------------------------


class TestTier0Route:
    def test_mode_is_no_model(self):
        assert route_from_tier(0).mode is RoutingMode.NO_MODEL

    def test_no_lanes(self):
        assert route_from_tier(0).lanes == []

    def test_no_human_gate(self):
        assert route_from_tier(0).requires_human_gate is False

    def test_no_independence_required(self):
        assert route_from_tier(0).requires_independence is False

    def test_cost_posture_is_minimal(self):
        assert route_from_tier(0).cost_posture is CostPosture.MINIMAL

    def test_audit_blocks_model_call(self):
        audit = route_from_tier(0).audit
        assert audit.route_kind is VendorRouteKind.NO_MODEL
        assert audit.route_class is None
        assert audit.session_action is SessionAction.NO_SESSION
        assert "model_call_not_needed" in audit.fallback_blockers


# ---------------------------------------------------------------------------
# Tier 1 -- one lane
# ---------------------------------------------------------------------------


class TestTier1Route:
    def test_mode_is_single_lane(self):
        assert route_from_tier(1).mode is RoutingMode.SINGLE_LANE

    def test_exactly_one_lane(self):
        assert len(route_from_tier(1).lanes) == 1

    def test_lane_role_is_builder(self):
        assert route_from_tier(1).lanes[0].role is ModelRole.BUILDER

    def test_lane_is_not_independent(self):
        assert route_from_tier(1).lanes[0].independent is False

    def test_no_human_gate(self):
        assert route_from_tier(1).requires_human_gate is False

    def test_no_independence_required(self):
        assert route_from_tier(1).requires_independence is False

    def test_cost_posture_is_minimal(self):
        assert route_from_tier(1).cost_posture is CostPosture.MINIMAL

    def test_account_session_route_is_first(self):
        audit = route_from_tier(1).audit
        assert audit.route_kind is VendorRouteKind.ACCOUNT_SESSION
        assert audit.route_class is AccessRouteClass.ACCOUNT_SESSION
        assert audit.route_precedence[0] is AccessRouteClass.ACCOUNT_SESSION
        assert audit.route_precedence[-1] is AccessRouteClass.AGGREGATOR_API


# ---------------------------------------------------------------------------
# Tier 2 -- two independent lanes
# ---------------------------------------------------------------------------


class TestTier2Route:
    def test_mode_is_dual_lane(self):
        assert route_from_tier(2).mode is RoutingMode.DUAL_LANE

    def test_exactly_two_lanes(self):
        assert len(route_from_tier(2).lanes) == 2

    def test_has_builder_lane(self):
        roles = [l.role for l in route_from_tier(2).lanes]
        assert ModelRole.BUILDER in roles

    def test_has_reviewer_lane(self):
        roles = [l.role for l in route_from_tier(2).lanes]
        assert ModelRole.REVIEWER in roles

    def test_reviewer_lane_is_independent(self):
        reviewer = next(l for l in route_from_tier(2).lanes if l.role is ModelRole.REVIEWER)
        assert reviewer.independent is True

    def test_requires_independence(self):
        assert route_from_tier(2).requires_independence is True

    def test_no_human_gate(self):
        assert route_from_tier(2).requires_human_gate is False

    def test_cost_posture_is_standard(self):
        assert route_from_tier(2).cost_posture is CostPosture.STANDARD

    def test_audit_requires_meaningful_review_proof(self):
        audit = route_from_tier(2).audit
        assert audit.trust_state is RouteTrustState.CANDIDATE
        assert "independent_review_when_meaningful" in audit.proof_required
        assert "trust_state" in audit.telemetry_required


# ---------------------------------------------------------------------------
# Tier 3 -- two lanes plus proof/review posture
# ---------------------------------------------------------------------------


class TestTier3Route:
    def test_mode_is_dual_lane_proof(self):
        assert route_from_tier(3).mode is RoutingMode.DUAL_LANE_PROOF

    def test_has_builder_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.BUILDER in roles

    def test_has_reviewer_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.REVIEWER in roles

    def test_has_verifier_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.VERIFIER in roles

    def test_verifier_lane_is_independent(self):
        verifier = next(l for l in route_from_tier(3).lanes if l.role is ModelRole.VERIFIER)
        assert verifier.independent is True

    def test_requires_independence(self):
        assert route_from_tier(3).requires_independence is True

    def test_no_human_gate(self):
        assert route_from_tier(3).requires_human_gate is False

    def test_cost_posture_is_thorough(self):
        assert route_from_tier(3).cost_posture is CostPosture.THOROUGH

    def test_tier3_uses_distinct_model_lane_names(self):
        lane_models = [lane.preferred_model for lane in route_from_tier(3).lanes]
        assert len(lane_models) == len(set(lane_models))

    def test_tier3_audit_blocks_authoritative_aggregator_fallback(self):
        audit = route_from_tier(3).audit
        assert "independent_dual_model_lanes" in audit.proof_required
        assert "aggregator_cannot_be_authoritative" in audit.fallback_blockers
        assert any("aggregator_api_rejected" in item for item in audit.alternatives_rejected)


# ---------------------------------------------------------------------------
# Tier 4 -- human gate required before execution
# ---------------------------------------------------------------------------


class TestTier4Route:
    def test_mode_is_human_gate(self):
        assert route_from_tier(4).mode is RoutingMode.HUMAN_GATE

    def test_requires_human_gate(self):
        assert route_from_tier(4).requires_human_gate is True

    def test_has_explainer_lane(self):
        roles = [l.role for l in route_from_tier(4).lanes]
        assert ModelRole.EXPLAINER in roles

    def test_no_builder_lane(self):
        roles = [l.role for l in route_from_tier(4).lanes]
        assert ModelRole.BUILDER not in roles

    def test_risk_tier_is_4(self):
        assert route_from_tier(4).risk_tier == 4

    def test_tier4_audit_requires_human_gate(self):
        audit = route_from_tier(4).audit
        assert audit.trust_state is RouteTrustState.BLOCKED
        assert "human_gate_approval" in audit.proof_required
        assert "human_gate_required" in audit.fallback_blockers


# ---------------------------------------------------------------------------
# Default context strategy is focused packet
# ---------------------------------------------------------------------------


class TestContextStrategy:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_default_is_focused_packet(self, tier):
        assert route_from_tier(tier).context_strategy is ContextStrategy.FOCUSED_PACKET

    def test_context_strategy_override_via_assessment(self):
        assessment = assess_tier(2)
        route = route_from_assessment(assessment, context_strategy=ContextStrategy.REUSE_SESSION)
        assert route.context_strategy is ContextStrategy.REUSE_SESSION
        assert route.audit.session_action is SessionAction.REUSE

    def test_large_context_accepted(self):
        route = route_from_assessment(assess_tier(3), context_strategy=ContextStrategy.LARGE_CONTEXT)
        assert route.context_strategy is ContextStrategy.LARGE_CONTEXT
        assert route.audit.session_action is SessionAction.START_NEW

    def test_summarize_and_reset_maps_to_session_action(self):
        route = route_from_assessment(
            assess_tier(3),
            context_strategy=ContextStrategy.SUMMARIZE_AND_RESET,
        )
        assert route.audit.session_action is SessionAction.SUMMARIZE_AND_RESET


# ---------------------------------------------------------------------------
# route_from_assessment and route_from_tier consistency
# ---------------------------------------------------------------------------


class TestRouteFromAssessment:
    def test_matches_route_from_tier(self):
        for tier_num in range(5):
            assessment = assess_tier(tier_num)
            r1 = route_from_assessment(assessment)
            r2 = route_from_tier(tier_num)
            assert r1.mode == r2.mode
            assert r1.requires_human_gate == r2.requires_human_gate
            assert r1.requires_independence == r2.requires_independence
            assert len(r1.lanes) == len(r2.lanes)

    def test_risk_tier_preserved(self):
        for tier_num in range(5):
            assert route_from_tier(tier_num).risk_tier == tier_num

    def test_enum_tier_accepted(self):
        for tier_enum in RiskTier:
            route = route_from_tier(tier_enum)
            assert route.risk_tier == tier_enum.value

    def test_reason_not_empty(self):
        for tier_num in range(5):
            assert route_from_tier(tier_num).reason

    def test_unknown_assessment_tier_raises_value_error(self):
        assessment = assess_tier(4)
        assessment.tier = 99
        with pytest.raises(ValueError, match="Unknown risk tier 99"):
            route_from_assessment(assessment)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_identical_calls_produce_identical_routes(self, tier):
        r1 = route_from_tier(tier)
        r2 = route_from_tier(tier)
        assert r1.mode == r2.mode
        assert r1.requires_human_gate == r2.requires_human_gate
        assert r1.requires_independence == r2.requires_independence
        assert r1.cost_posture == r2.cost_posture
        assert r1.context_strategy == r2.context_strategy
        assert [(l.role, l.preferred_model, l.independent) for l in r1.lanes] == \
               [(l.role, l.preferred_model, l.independent) for l in r2.lanes]

    def test_lanes_are_independent_copies(self):
        r1 = route_from_tier(2)
        r2 = route_from_tier(2)
        r1.lanes[0].preferred_model = "mutated"
        assert r2.lanes[0].preferred_model != "mutated"


# ---------------------------------------------------------------------------
# Shape checks
# ---------------------------------------------------------------------------


class TestShape:
    def test_result_is_relay_route(self):
        assert isinstance(route_from_tier(2), RelayRoute)

    def test_lanes_are_relay_lane_instances(self):
        for lane in route_from_tier(3).lanes:
            assert isinstance(lane, RelayLane)

    def test_mode_is_routing_mode_enum(self):
        assert isinstance(route_from_tier(1).mode, RoutingMode)

    def test_context_strategy_is_enum(self):
        assert isinstance(route_from_tier(1).context_strategy, ContextStrategy)

    def test_cost_posture_is_enum(self):
        assert isinstance(route_from_tier(1).cost_posture, CostPosture)

    def test_audit_is_relay_route_audit(self):
        assert isinstance(route_from_tier(1).audit, RelayRouteAudit)

    def test_audit_route_precedence_is_immutable_tuple(self):
        audit = route_from_tier(1).audit
        assert isinstance(audit.route_precedence, tuple)
        with pytest.raises((AttributeError, TypeError)):
            audit.route_precedence += (AccessRouteClass.DIRECT_API,)  # type: ignore[misc]

    def test_audit_lists_are_immutable_tuples(self):
        audit = route_from_tier(3).audit
        assert isinstance(audit.proof_required, tuple)
        assert isinstance(audit.telemetry_required, tuple)
        assert isinstance(audit.fallback_blockers, tuple)


# ---------------------------------------------------------------------------
# Council awareness -- RelayRoute exposes council_plan per tier
# ---------------------------------------------------------------------------


class TestCouncilAwareness:
    def test_council_plan_is_council_plan_instance(self):
        for tier in range(5):
            assert isinstance(route_from_tier(tier).council_plan, CouncilPlan)

    def test_tier0_includes_chairman_only(self):
        plan = route_from_tier(0).council_plan
        assert plan.roles == [CouncilRole.CHAIRMAN]

    def test_tier1_includes_pragmatist_and_chairman(self):
        plan = route_from_tier(1).council_plan
        assert CouncilRole.PRAGMATIST in plan.roles
        assert CouncilRole.CHAIRMAN in plan.roles
        assert len(plan.roles) == 2

    def test_tier2_includes_analyst_devils_advocate_pragmatist_chairman(self):
        plan = route_from_tier(2).council_plan
        assert CouncilRole.ANALYST in plan.roles
        assert CouncilRole.DEVILS_ADVOCATE in plan.roles
        assert CouncilRole.PRAGMATIST in plan.roles
        assert CouncilRole.CHAIRMAN in plan.roles
        assert len(plan.roles) == 4

    def test_tier3_requires_full_council(self):
        plan = route_from_tier(3).council_plan
        assert plan.requires_full_council is True
        assert len(plan.roles) == len(CouncilRole)

    def test_tier4_requires_full_council(self):
        plan = route_from_tier(4).council_plan
        assert plan.requires_full_council is True
        assert len(plan.roles) == len(CouncilRole)

    def test_council_risk_tier_matches_route_risk_tier(self):
        for tier in range(5):
            route = route_from_tier(tier)
            assert route.council_plan.risk_tier == route.risk_tier

    def test_council_plan_populated_via_assessment(self):
        from meridian_core.risk import assess_tier
        assessment = assess_tier(2)
        route = route_from_assessment(assessment)
        assert isinstance(route.council_plan, CouncilPlan)
        assert CouncilRole.ANALYST in route.council_plan.roles


# ---------------------------------------------------------------------------
# Prompt Budget integration -- RelayRoute carries a bounded PromptBudgetPlan
# ---------------------------------------------------------------------------


class TestPromptBudgetIntegration:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_every_tier_has_prompt_budget(self, tier):
        assert isinstance(route_from_tier(tier).prompt_budget, PromptBudgetPlan)

    @pytest.mark.parametrize("tier,expected", [
        (0, PromptBudgetTier.MINIMAL),
        (1, PromptBudgetTier.MINIMAL),
        (2, PromptBudgetTier.FOCUSED),
        (3, PromptBudgetTier.BOUNDED),
        (4, PromptBudgetTier.EXPLAINED),
    ])
    def test_budget_tier_matches_risk_tier(self, tier, expected):
        assert route_from_tier(tier).prompt_budget.tier is expected

    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_council_plan_still_present_alongside_budget(self, tier):
        route = route_from_tier(tier)
        assert isinstance(route.council_plan, CouncilPlan)
        assert isinstance(route.prompt_budget, PromptBudgetPlan)

    def test_budget_allowed_sources_are_immutable_tuples(self):
        r1 = route_from_tier(2)
        r2 = route_from_tier(2)
        assert isinstance(r1.prompt_budget.allowed_sources, tuple)
        assert isinstance(r2.prompt_budget.allowed_sources, tuple)
        with pytest.raises(AttributeError):
            r1.prompt_budget.allowed_sources += ("injected",)  # type: ignore[misc]

    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_existing_routing_mode_unchanged(self, tier):
        expected_modes = {
            0: RoutingMode.NO_MODEL,
            1: RoutingMode.SINGLE_LANE,
            2: RoutingMode.DUAL_LANE,
            3: RoutingMode.DUAL_LANE_PROOF,
            4: RoutingMode.HUMAN_GATE,
        }
        assert route_from_tier(tier).mode is expected_modes[tier]

    def test_budget_populated_via_assessment(self):
        assessment = assess_tier(3)
        route = route_from_assessment(assessment)
        assert route.prompt_budget.tier is PromptBudgetTier.BOUNDED
        assert route.prompt_budget.max_context_tokens == 5000


# ---------------------------------------------------------------------------
# Context Health, Latency Posture, Privacy Level -- deepened domain support
# ---------------------------------------------------------------------------


class TestContextHealthLatencyPrivacy:
    def test_tier0_context_health_is_clean(self):
        assert route_from_tier(0).context_health is ContextHealth.CLEAN

    def test_tier1_context_health_is_bounded(self):
        assert route_from_tier(1).context_health is ContextHealth.BOUNDED

    def test_tier2_context_health_is_bounded(self):
        assert route_from_tier(2).context_health is ContextHealth.BOUNDED

    def test_tier3_context_health_is_clean(self):
        assert route_from_tier(3).context_health is ContextHealth.CLEAN

    def test_tier4_context_health_is_clean(self):
        assert route_from_tier(4).context_health is ContextHealth.CLEAN

    def test_tier0_latency_posture_is_fast(self):
        assert route_from_tier(0).latency_posture is LatencyPosture.FAST

    def test_tier1_latency_posture_is_fast(self):
        assert route_from_tier(1).latency_posture is LatencyPosture.FAST

    def test_tier2_latency_posture_is_standard(self):
        assert route_from_tier(2).latency_posture is LatencyPosture.STANDARD

    def test_tier3_latency_posture_is_thorough(self):
        assert route_from_tier(3).latency_posture is LatencyPosture.THOROUGH

    def test_tier4_latency_posture_is_standard(self):
        assert route_from_tier(4).latency_posture is LatencyPosture.STANDARD

    def test_tier0_privacy_level_is_local_only(self):
        assert route_from_tier(0).privacy_level is PrivacyLevel.LOCAL_ONLY

    def test_tier1_privacy_level_is_project_scoped(self):
        assert route_from_tier(1).privacy_level is PrivacyLevel.PROJECT_SCOPED

    def test_tier2_privacy_level_is_project_scoped(self):
        assert route_from_tier(2).privacy_level is PrivacyLevel.PROJECT_SCOPED

    def test_tier3_privacy_level_is_project_scoped(self):
        assert route_from_tier(3).privacy_level is PrivacyLevel.PROJECT_SCOPED

    def test_tier4_privacy_level_is_project_scoped(self):
        assert route_from_tier(4).privacy_level is PrivacyLevel.PROJECT_SCOPED

    def test_audit_includes_context_health(self):
        for tier in range(5):
            audit = route_from_tier(tier).audit
            assert isinstance(audit.context_health, ContextHealth)

    def test_audit_includes_latency_posture(self):
        for tier in range(5):
            audit = route_from_tier(tier).audit
            assert isinstance(audit.latency_posture, LatencyPosture)

    def test_audit_includes_privacy_level(self):
        for tier in range(5):
            audit = route_from_tier(tier).audit
            assert isinstance(audit.privacy_level, PrivacyLevel)

    def test_fields_match_between_route_and_audit(self):
        for tier in range(5):
            route = route_from_tier(tier)
            assert route.context_health is route.audit.context_health
            assert route.latency_posture is route.audit.latency_posture
            assert route.privacy_level is route.audit.privacy_level

    def test_context_health_via_assessment(self):
        assessment = assess_tier(3)
        route = route_from_assessment(assessment)
        assert route.context_health is ContextHealth.CLEAN

    def test_latency_posture_via_assessment(self):
        assessment = assess_tier(3)
        route = route_from_assessment(assessment)
        assert route.latency_posture is LatencyPosture.THOROUGH

    def test_privacy_level_via_assessment(self):
        assessment = assess_tier(3)
        route = route_from_assessment(assessment)
        assert route.privacy_level is PrivacyLevel.PROJECT_SCOPED


# ---------------------------------------------------------------------------
# Dual-Lane Tier 3 Independence and Fallback Blockers
# ---------------------------------------------------------------------------


class TestTier3DualLaneIndependence:
    def test_tier3_requires_dual_lane_independence(self):
        route = route_from_tier(3)
        assert route.requires_independence is True

    def test_tier3_dual_lane_mode(self):
        assert route_from_tier(3).mode is RoutingMode.DUAL_LANE_PROOF

    def test_tier3_lanes_include_independent_reviewer(self):
        route = route_from_tier(3)
        reviewer_lanes = [lane for lane in route.lanes if lane.role is ModelRole.REVIEWER]
        assert len(reviewer_lanes) > 0
        assert any(lane.independent for lane in reviewer_lanes)

    def test_tier3_fallback_blockers_include_dual_lane_independence(self):
        audit = route_from_tier(3).audit
        assert "dual_lane_independence_required" in audit.fallback_blockers

    def test_tier3_fallback_blockers_include_unknown_trust(self):
        audit = route_from_tier(3).audit
        assert "unknown_trust_route" in audit.fallback_blockers

    def test_tier3_proof_required_includes_independent_lanes(self):
        audit = route_from_tier(3).audit
        assert "independent_dual_model_lanes" in audit.proof_required

    def test_tier3_trust_state_is_candidate(self):
        audit = route_from_tier(3).audit
        assert audit.trust_state is RouteTrustState.CANDIDATE

    def test_tier4_human_gate_required(self):
        assert route_from_tier(4).requires_human_gate is True

    def test_tier4_trust_state_is_blocked_until_approval(self):
        audit = route_from_tier(4).audit
        assert audit.trust_state is RouteTrustState.BLOCKED

    def test_tier4_fallback_blockers_include_human_gate(self):
        audit = route_from_tier(4).audit
        assert "human_gate_required" in audit.fallback_blockers

    def test_tier3_aggregator_rejected_for_authority(self):
        audit = route_from_tier(3).audit
        assert "aggregator_cannot_be_authoritative" in audit.fallback_blockers
