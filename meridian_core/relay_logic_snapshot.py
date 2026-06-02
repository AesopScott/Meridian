"""Serializable Relay model-routing logic snapshot for UI harnesses."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from .relay import route_from_tier
from .relay_dispatch import build_relay_dispatch_plan
from .relay_packet import assemble_relay_packet


SNAPSHOT_VERSION = "relay-domain-v1"
SNAPSHOT_SOURCE = "meridian_core.relay.route_from_tier"
DISPATCH_SOURCE = "meridian_core.relay_dispatch.build_relay_dispatch_plan"
SNAPSHOT_PROMPT = "Relay dispatch snapshot placeholder."
PRIME_DIRECTIVES = (
    {
        "name": "Account/session-first, never silent fallback",
        "logic": "Relay tries the safest observable account/session route first, then local CLI, direct API, and aggregator only as explicit fallback or comparison.",
    },
    {
        "name": "Risk tier determines model depth",
        "logic": "Relay maps risk to lane depth: no model, single lane, independent review, dual-model proof, or human gate.",
    },
    {
        "name": "No drift between route, proof, and visible harness",
        "logic": "Relay route decisions, proof burden, blockers, dispatch lanes, prompt budget, and harness evidence come from the same backend snapshot.",
    },
)
PRIME_DIRECTIVE_PROOFS = (
    {
        "question": "What route was tried first, what route was selected, and what alternatives were rejected?",
        "proves": "account/session-first precedence and no silent fallback",
    },
    {
        "question": "What risk tier was assigned, and what model-lane depth did that tier require?",
        "proves": "risk-tier routing depth and autonomy limits",
    },
    {
        "question": "Where is the visible proof in the harness for the route, blockers, dispatch lanes, prompt budget, and audit reason?",
        "proves": "no drift between backend Relay and visible harness evidence",
    },
)


def _value(item: Any) -> Any:
    if isinstance(item, Enum):
        return item.value
    return item


def _tuple_values(items: tuple[Any, ...]) -> list[Any]:
    return [_value(item) for item in items]


def _lane_snapshot(lane: Any) -> dict[str, Any]:
    return {
        "role": _value(lane.role),
        "preferredModel": lane.preferred_model,
        "independent": lane.independent,
    }


def _prompt_budget_snapshot(route: Any) -> dict[str, Any]:
    budget = route.prompt_budget
    return {
        "tier": _value(budget.tier),
        "maxContextTokens": budget.max_context_tokens,
        "allowedSources": list(budget.allowed_sources),
        "reason": budget.reason,
    }


def _audit_snapshot(route: Any) -> dict[str, Any]:
    audit = route.audit
    return {
        "routeKind": _value(audit.route_kind),
        "routeClass": _value(audit.route_class),
        "sessionAction": _value(audit.session_action),
        "trustState": _value(audit.trust_state),
        "routePrecedence": _tuple_values(audit.route_precedence),
        "alternativesRejected": list(audit.alternatives_rejected),
        "fallbackBlockers": list(audit.fallback_blockers),
        "proofRequired": list(audit.proof_required),
        "telemetryRequired": list(audit.telemetry_required),
    }


def _audit_depth_snapshot(route: Any) -> dict[str, Any]:
    audit = route.audit
    fallback_blockers = list(audit.fallback_blockers)
    alternatives_rejected = list(audit.alternatives_rejected)
    proof_required = list(audit.proof_required)
    telemetry_required = list(audit.telemetry_required)
    return {
        "routeClass": _value(audit.route_class),
        "routeKind": _value(audit.route_kind),
        "sessionAction": _value(audit.session_action),
        "trustState": _value(audit.trust_state),
        "contextHealth": _value(audit.context_health),
        "latencyPosture": _value(audit.latency_posture),
        "privacyLevel": _value(audit.privacy_level),
        "alternativesRejectedCount": len(alternatives_rejected),
        "fallbackBlockerCount": len(fallback_blockers),
        "proofRequiredCount": len(proof_required),
        "telemetryRequiredCount": len(telemetry_required),
        "silentFallbackBlocked": bool(
            fallback_blockers
            or any("rejected" in item for item in alternatives_rejected)
            or audit.trust_state.value in {"blocked", "candidate"}
        ),
        "primaryFallbackBlocker": fallback_blockers[0] if fallback_blockers else "none",
        "primaryProofRequirement": proof_required[0] if proof_required else "none",
    }


def _dispatch_snapshot(route: Any) -> dict[str, Any]:
    packet = assemble_relay_packet(
        packet_id=f"relay-logic-tier-{route.risk_tier}",
        serialized_prompt=SNAPSHOT_PROMPT,
        route=route,
    )
    plan = build_relay_dispatch_plan(route, packet)
    lanes = [
        {
            "role": _value(lane.role),
            "preferredModel": lane.preferred_model,
            "independent": lane.independent,
            "payloadSource": "packet.model_payload",
            "payloadTextVisible": False,
            "payloadEqualsModelPayload": lane.payload == packet.model_payload(),
            "payloadIncludesPacketMetadata": packet.packet_id in lane.payload,
        }
        for lane in plan.lanes
    ]
    return {
        "source": DISPATCH_SOURCE,
        "laneCount": len(plan.lanes),
        "laneOrder": [_value(lane.role) for lane in plan.lanes],
        "payloadPolicy": "model_payload_only",
        "payloadTextVisible": False,
        "lanes": lanes,
    }


def _capability_sections(tiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tier3 = tiers[3]
    tier4 = tiers[4]
    tier3_lanes = [
        f"{lane['role']} -> {lane['preferredModel']}"
        f"{' independent' if lane['independent'] else ''}"
        for lane in tier3["lanes"]
    ]
    budgets = [
        (
            f"Tier {tier['tier']}",
            (
                f"{tier['promptBudget']['tier']}, "
                f"{tier['promptBudget']['maxContextTokens']} tokens, "
                f"sources: {', '.join(tier['promptBudget']['allowedSources'])}"
            ),
        )
        for tier in tiers
    ]
    return [
        {
            "title": "Relay Job",
            "summary": "Relay is the model-routing brain: it answers which model route Prime should use, why, with what proof burden, and what must block fallback.",
            "rows": [
                ("owns", "model/vendor/session route selection logic"),
                ("does not own", "non-model cadence, UI liveness, or general chat"),
                ("prime asks", "which route, why, risk, proof, context/session lifecycle, and blockers"),
                ("no drift point", "the harness reads this backend snapshot instead of a separate static UI list"),
            ],
        },
        {
            "title": "Risk Tier Routing",
            "summary": "Relay maps task risk to deterministic model-use posture from no model through human gate.",
            "rows": [(f"Tier {tier['tier']}: {tier['mode']}", tier["reason"]) for tier in tiers],
        },
        {
            "title": "Model Lane Logic",
            "summary": "Relay thinks in model roles and lane independence before vendor names.",
            "rows": [
                ("builder", "primary work producer"),
                ("reviewer", "independent critique/comparison lane"),
                ("verifier", "proof/validation lane"),
                ("explainer", "human-gate explanation lane"),
                ("tier 3 lanes", " | ".join(tier3_lanes)),
            ],
        },
        {
            "title": "Access Route Precedence",
            "summary": "Relay is account/session-first: it does not silently jump to APIs or aggregators.",
            "rows": [
                (str(index + 1), route)
                for index, route in enumerate(tiers[1]["audit"]["routePrecedence"])
            ],
            "bullets": [
                "account/session routes come first when observable and safe",
                "local CLI routes follow when cwd/auth/model identity are clear",
                "direct API routes matter for pinned model id, clean payload control, cost tracking, and auditability",
                "aggregator API is fallback/comparison only, never hidden authority for Tier 3+",
            ],
        },
        {
            "title": "Session Lifecycle Logic",
            "summary": "Session action is part of routing, not cleanup after the fact.",
            "rows": [
                ("actions", "no_session | reuse | start_new | summarize_and_reset | transfer"),
                ("default strategy", "focused_packet"),
                ("tier 3 action", tier3["audit"]["sessionAction"]),
                ("why", "prevents prompt drag, stale session bleed, polluted context reuse, and wrong-role routing"),
            ],
        },
        {
            "title": "Context Latency Privacy",
            "summary": "Relay tags each route with context health, latency posture, and privacy level for Prime/Bifrost visibility.",
            "rows": [
                ("tier 3 context", tier3["contextHealth"]),
                ("tier 3 latency", tier3["latencyPosture"]),
                ("tier 3 privacy", tier3["privacyLevel"]),
                ("tier 4 trust", tier4["audit"]["trustState"]),
            ],
        },
        {
            "title": "Prompt Budget Logic",
            "summary": "Budgets are tier-locked so model prompts cannot grow by hidden UI or diagnostic drag.",
            "rows": budgets,
        },
        {
            "title": "Audit Logic",
            "summary": "Relay records route class, session action, trust state, alternatives rejected, blockers, proof, and telemetry.",
            "rows": [
                ("tier 3 trust", tier3["auditDepth"]["trustState"]),
                ("tier 3 silent fallback", "blocked" if tier3["auditDepth"]["silentFallbackBlocked"] else "allowed"),
                ("tier 3 primary blocker", tier3["auditDepth"]["primaryFallbackBlocker"]),
                ("tier 3 primary proof", tier3["auditDepth"]["primaryProofRequirement"]),
                ("tier 4 gate", tier4["auditDepth"]["primaryFallbackBlocker"]),
            ],
        },
        {
            "title": "Dispatch Logic",
            "summary": "Relay builds an immutable dispatch plan without calling a model.",
            "rows": [
                ("source", DISPATCH_SOURCE),
                ("tier 3 lane count", str(tier3["dispatch"]["laneCount"])),
                ("tier 3 lane order", " | ".join(tier3["dispatch"]["laneOrder"])),
                ("payload policy", tier3["dispatch"]["payloadPolicy"]),
                ("payload text visible", "no" if not tier3["dispatch"]["payloadTextVisible"] else "yes"),
            ],
        },
        {
            "title": "Current Limits",
            "summary": "Relay is domain-complete enough for Prime integration, but Auto routing is intentionally still gated.",
            "rows": [
                ("not yet live", "Prime is not yet asking Relay for production Auto routing decisions"),
                ("not yet bound", "real provider availability, cost, quota, and trust telemetry are not fully wired"),
                ("still blocked", "Auto stays disabled until Prime consumes this route contract end to end"),
            ],
        },
    ]


def _tier_snapshot(tier: int) -> dict[str, Any]:
    route = route_from_tier(tier)
    return {
        "tier": route.risk_tier,
        "mode": _value(route.mode),
        "reason": route.reason,
        "costPosture": _value(route.cost_posture),
        "requiresIndependence": route.requires_independence,
        "requiresHumanGate": route.requires_human_gate,
        "lanes": [_lane_snapshot(lane) for lane in route.lanes],
        "contextStrategy": _value(route.context_strategy),
        "contextHealth": _value(route.context_health),
        "latencyPosture": _value(route.latency_posture),
        "privacyLevel": _value(route.privacy_level),
        "promptBudget": _prompt_budget_snapshot(route),
        "audit": _audit_snapshot(route),
        "auditDepth": _audit_depth_snapshot(route),
        "dispatch": _dispatch_snapshot(route),
    }


def relay_logic_snapshot() -> dict[str, Any]:
    """Return the canonical Relay logic that visible harnesses should render."""
    tiers = [_tier_snapshot(tier) for tier in range(5)]
    return {
        "ok": True,
        "service": "meridian-relay-logic",
        "version": SNAPSHOT_VERSION,
        "source": SNAPSHOT_SOURCE,
        "dispatchSource": DISPATCH_SOURCE,
        "autoRouting": "disabled_until_prime_relay_contract",
        "primeDirectives": list(PRIME_DIRECTIVES),
        "primeDirectiveProofs": list(PRIME_DIRECTIVE_PROOFS),
        "routePrecedence": tiers[1]["audit"]["routePrecedence"],
        "capabilitySections": _capability_sections(tiers),
        "tiers": tiers,
    }


def main() -> None:
    print(json.dumps(relay_logic_snapshot(), sort_keys=True))


if __name__ == "__main__":
    main()
