"""
Relay Routing -- deterministic model/session routing plan from risk tier.

Relay is the Agent / Model Harness. This slice produces a structured
RelayRoute from a RiskAssessment without calling real models or APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import cast

from .council import CouncilPlan, council_plan_for_tier
from .prompt_budget import PromptBudgetPlan, prompt_budget_for_risk_tier
from .risk import RiskAssessment, RiskTier, assess_tier


class RoutingMode(Enum):
    NO_MODEL = "no-model"
    SINGLE_LANE = "single-lane"
    DUAL_LANE = "dual-lane"
    DUAL_LANE_PROOF = "dual-lane-proof"
    HUMAN_GATE = "human-gate"


class ModelRole(Enum):
    BUILDER = "builder"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"
    EXPLAINER = "explainer"


class ContextStrategy(Enum):
    FOCUSED_PACKET = "focused_packet"
    REUSE_SESSION = "reuse_session"
    SUMMARIZE_AND_RESET = "summarize_and_reset"
    LARGE_CONTEXT = "large_context"


class CostPosture(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    THOROUGH = "thorough"


class VendorRouteKind(Enum):
    NO_MODEL = "no_model"
    ACCOUNT_SESSION = "account_session"
    LOCAL_CLI = "local_cli"
    DIRECT = "direct"
    AGGREGATOR = "aggregator"


class AccessRouteClass(Enum):
    ACCOUNT_SESSION = "account_session"
    LOCAL_CLI = "local_cli"
    DIRECT_API = "direct_api"
    AGGREGATOR_API = "aggregator_api"


class SessionAction(Enum):
    NO_SESSION = "no_session"
    REUSE = "reuse"
    START_NEW = "start_new"
    SUMMARIZE_AND_RESET = "summarize_and_reset"
    TRANSFER = "transfer"


class RouteTrustState(Enum):
    LOCAL_ONLY = "local_only"
    CANDIDATE = "candidate"
    TRUSTED = "trusted"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class ContextHealth(Enum):
    CLEAN = "clean"
    BOUNDED = "bounded"
    APPROACHING_LIMIT = "approaching_limit"
    POLLUTED = "polluted"
    UNKNOWN = "unknown"


class LatencyPosture(Enum):
    FAST = "fast"
    STANDARD = "standard"
    THOROUGH = "thorough"
    UNKNOWN = "unknown"


class PrivacyLevel(Enum):
    LOCAL_ONLY = "local_only"
    PROJECT_SCOPED = "project_scoped"
    EXTERNAL_VENDOR = "external_vendor"
    UNKNOWN = "unknown"


@dataclass
class RelayLane:
    role: ModelRole
    preferred_model: str
    independent: bool = False
    independence_reason: str = ""


@dataclass(frozen=True)
class RelayRouteAudit:
    route_kind: VendorRouteKind
    route_class: AccessRouteClass | None
    session_action: SessionAction
    trust_state: RouteTrustState
    context_health: ContextHealth
    latency_posture: LatencyPosture
    privacy_level: PrivacyLevel
    route_precedence: tuple[AccessRouteClass, ...]
    alternatives_rejected: tuple[str, ...]
    fallback_blockers: tuple[str, ...]
    proof_required: tuple[str, ...]
    telemetry_required: tuple[str, ...]


@dataclass
class RelayRoute:
    mode: RoutingMode
    lanes: list[RelayLane]
    context_strategy: ContextStrategy
    context_health: ContextHealth
    latency_posture: LatencyPosture
    privacy_level: PrivacyLevel
    reason: str
    cost_posture: CostPosture
    requires_independence: bool
    requires_human_gate: bool
    risk_tier: int
    council_plan: CouncilPlan
    prompt_budget: PromptBudgetPlan
    audit: RelayRouteAudit


# ---------------------------------------------------------------------------
# Routing table -- deterministic defaults per tier
# ---------------------------------------------------------------------------

_ROUTING_TABLE: dict[int, dict] = {
    0: {
        "mode": RoutingMode.NO_MODEL,
        "lanes": [],
        "reason": "deterministic local logic; no model lanes needed",
        "cost_posture": CostPosture.MINIMAL,
        "requires_independence": False,
        "requires_human_gate": False,
    },
    1: {
        "mode": RoutingMode.SINGLE_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="fast-default", independent=False),
        ],
        "reason": "low-risk reversible action; one fast/cheap lane is sufficient",
        "cost_posture": CostPosture.MINIMAL,
        "requires_independence": False,
        "requires_human_gate": False,
    },
    2: {
        "mode": RoutingMode.DUAL_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="primary-default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, preferred_model="independent-reviewer", independent=True),
        ],
        "reason": "meaningful Prime decision; two independent lanes required for disagreement detection",
        "cost_posture": CostPosture.STANDARD,
        "requires_independence": True,
        "requires_human_gate": False,
    },
    3: {
        "mode": RoutingMode.DUAL_LANE_PROOF,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="primary-default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, preferred_model="independent-reviewer", independent=True),
            RelayLane(role=ModelRole.VERIFIER, preferred_model="proof-verifier", independent=True),
        ],
        "reason": "completion or proof claim; dual-lane plus Aegis verification posture",
        "cost_posture": CostPosture.THOROUGH,
        "requires_independence": True,
        "requires_human_gate": False,
    },
    4: {
        "mode": RoutingMode.HUMAN_GATE,
        "lanes": [
            RelayLane(role=ModelRole.EXPLAINER, preferred_model="primary-default", independent=False),
        ],
        "reason": (
            "irreversible, public, financial, destructive, or strategic action; "
            "no autonomous execution until human gate is cleared"
        ),
        "cost_posture": CostPosture.STANDARD,
        "requires_independence": False,
        "requires_human_gate": True,
    },
}


_ROUTE_PRECEDENCE: tuple[AccessRouteClass, ...] = (
    AccessRouteClass.ACCOUNT_SESSION,
    AccessRouteClass.LOCAL_CLI,
    AccessRouteClass.DIRECT_API,
    AccessRouteClass.AGGREGATOR_API,
)


_TIER_AUDIT_DEFAULTS: dict[int, dict] = {
    0: {
        "route_kind": VendorRouteKind.NO_MODEL,
        "route_class": None,
        "trust_state": RouteTrustState.LOCAL_ONLY,
        "context_health": ContextHealth.CLEAN,
        "latency_posture": LatencyPosture.FAST,
        "privacy_level": PrivacyLevel.LOCAL_ONLY,
        "alternatives_rejected": (
            "model_call_rejected: deterministic local logic is sufficient",
        ),
        "fallback_blockers": ("model_call_not_needed",),
        "proof_required": (),
        "telemetry_required": (),
    },
    1: {
        "route_kind": VendorRouteKind.ACCOUNT_SESSION,
        "route_class": AccessRouteClass.ACCOUNT_SESSION,
        "trust_state": RouteTrustState.CANDIDATE,
        "context_health": ContextHealth.BOUNDED,
        "latency_posture": LatencyPosture.FAST,
        "privacy_level": PrivacyLevel.PROJECT_SCOPED,
        "alternatives_rejected": (
            "direct_api_deferred: account/session or local CLI route can satisfy low-risk work first",
        ),
        "fallback_blockers": (
            "missing_route_metadata",
            "missing_prompt_payload_snapshot",
        ),
        "proof_required": ("prompt_payload_snapshot",),
        "telemetry_required": (
            "route_class",
            "selected_model",
            "prompt_payload_budget",
        ),
    },
    2: {
        "route_kind": VendorRouteKind.ACCOUNT_SESSION,
        "route_class": AccessRouteClass.ACCOUNT_SESSION,
        "trust_state": RouteTrustState.CANDIDATE,
        "context_health": ContextHealth.BOUNDED,
        "latency_posture": LatencyPosture.STANDARD,
        "privacy_level": PrivacyLevel.PROJECT_SCOPED,
        "alternatives_rejected": (
            "direct_api_deferred: account/session route remains first if observable",
            "single_lane_limited: independent review lane may be required for meaningful work",
        ),
        "fallback_blockers": (
            "unknown_trust_route",
            "risk_tier_exceeded",
            "missing_prompt_payload_snapshot",
        ),
        "proof_required": (
            "prompt_payload_snapshot",
            "independent_review_when_meaningful",
        ),
        "telemetry_required": (
            "route_class",
            "selected_model",
            "trust_state",
            "prompt_payload_budget",
            "cost_posture",
        ),
    },
    3: {
        "route_kind": VendorRouteKind.ACCOUNT_SESSION,
        "route_class": AccessRouteClass.ACCOUNT_SESSION,
        "trust_state": RouteTrustState.CANDIDATE,
        "context_health": ContextHealth.CLEAN,
        "latency_posture": LatencyPosture.THOROUGH,
        "privacy_level": PrivacyLevel.PROJECT_SCOPED,
        "alternatives_rejected": (
            "single_lane_rejected: Tier 3 requires independent dual-model lanes",
            "aggregator_api_rejected: aggregator cannot be authoritative for Tier 3",
        ),
        "fallback_blockers": (
            "unknown_trust_route",
            "missing_prompt_payload_snapshot",
            "external_review_required",
            "aggregator_cannot_be_authoritative",
            "dual_lane_independence_required",
        ),
        "proof_required": (
            "aegis_clean_proof_trail",
            "independent_dual_model_lanes",
            "prompt_payload_snapshot",
        ),
        "telemetry_required": (
            "route_class",
            "selected_model",
            "selected_vendor",
            "trust_state",
            "prompt_payload_budget",
            "cost_posture",
            "alternatives_rejected",
        ),
    },
    4: {
        "route_kind": VendorRouteKind.ACCOUNT_SESSION,
        "route_class": AccessRouteClass.ACCOUNT_SESSION,
        "trust_state": RouteTrustState.BLOCKED,
        "context_health": ContextHealth.CLEAN,
        "latency_posture": LatencyPosture.STANDARD,
        "privacy_level": PrivacyLevel.PROJECT_SCOPED,
        "alternatives_rejected": (
            "autonomous_execution_rejected: human gate required",
            "aggregator_api_rejected: high-risk work requires direct or account/session proof",
        ),
        "fallback_blockers": (
            "human_gate_required",
            "unknown_trust_route",
            "missing_prompt_payload_snapshot",
        ),
        "proof_required": (
            "human_gate_approval",
            "aegis_clean_proof_trail",
            "prompt_payload_snapshot",
        ),
        "telemetry_required": (
            "route_class",
            "selected_model",
            "selected_vendor",
            "trust_state",
            "human_gate_required",
            "proof_required",
        ),
    },
}


def _session_action_for_context(context_strategy: ContextStrategy) -> SessionAction:
    if context_strategy is ContextStrategy.REUSE_SESSION:
        return SessionAction.REUSE
    if context_strategy is ContextStrategy.SUMMARIZE_AND_RESET:
        return SessionAction.SUMMARIZE_AND_RESET
    return SessionAction.START_NEW


def _audit_for_tier(tier: int, context_strategy: ContextStrategy) -> RelayRouteAudit:
    row = cast(dict, _TIER_AUDIT_DEFAULTS[tier])
    session_action = (
        SessionAction.NO_SESSION
        if tier == 0
        else _session_action_for_context(context_strategy)
    )
    return RelayRouteAudit(
        route_kind=row["route_kind"],
        route_class=row["route_class"],
        session_action=session_action,
        trust_state=row["trust_state"],
        context_health=row["context_health"],
        latency_posture=row["latency_posture"],
        privacy_level=row["privacy_level"],
        route_precedence=_ROUTE_PRECEDENCE,
        alternatives_rejected=row["alternatives_rejected"],
        fallback_blockers=row["fallback_blockers"],
        proof_required=row["proof_required"],
        telemetry_required=row["telemetry_required"],
    )


def route_from_assessment(
    assessment: RiskAssessment,
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
) -> RelayRoute:
    """
    Produce a deterministic RelayRoute from a RiskAssessment.

    context_strategy defaults to FOCUSED_PACKET. Pass an explicit strategy
    when the caller has already decided (e.g. reuse_session after a healthy
    context check).
    """
    if assessment.tier not in _ROUTING_TABLE:
        raise ValueError(
            f"Unknown risk tier {assessment.tier!r}; valid tiers are {sorted(_ROUTING_TABLE)}"
        )
    row = cast(dict, _ROUTING_TABLE[assessment.tier])
    audit = _audit_for_tier(assessment.tier, context_strategy)
    return RelayRoute(
        mode=row["mode"],
        lanes=[RelayLane(l.role, l.preferred_model, l.independent) for l in row["lanes"]],
        context_strategy=context_strategy,
        context_health=audit.context_health,
        latency_posture=audit.latency_posture,
        privacy_level=audit.privacy_level,
        reason=row["reason"],
        cost_posture=row["cost_posture"],
        requires_independence=row["requires_independence"],
        requires_human_gate=row["requires_human_gate"],
        risk_tier=assessment.tier,
        council_plan=council_plan_for_tier(assessment),
        prompt_budget=prompt_budget_for_risk_tier(assessment.tier),
        audit=audit,
    )


def route_from_tier(
    tier: int | RiskTier,
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
    reason: str | None = None,
) -> RelayRoute:
    """
    Convenience: produce a RelayRoute directly from a tier number or RiskTier enum.
    """
    assessment = assess_tier(tier, reason=reason)
    return route_from_assessment(assessment, context_strategy=context_strategy)
