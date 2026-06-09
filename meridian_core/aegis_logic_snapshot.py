"""Backend snapshot for Aegis proof and cognition-policy logic.

This module is display-only. It builds a deterministic sample from reviewed
Aegis and CognitionPolicy APIs so UI surfaces can consume backend-owned proof
logic without reimplementing it in bridge code.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from .aegis import (
    AegisEvidence,
    EvidenceSeverity,
    ProofTrail,
    evidence_from_cross_check,
)
from .cognition_policy import (
    CognitionActionType,
    CognitionPolicyResult,
    evaluate_cognition_policy,
)

SNAPSHOT_VERSION = "aegis-domain-v1"


def aegis_logic_snapshot() -> dict[str, Any]:
    """Return a display-safe Aegis proof and policy snapshot."""
    trail = _sample_proof_trail()
    result = evaluate_cognition_policy(
        3,
        CognitionActionType.BUILD,
        proof_trail=trail,
        human_gate_approved=False,
    )
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.aegis_logic_snapshot.aegis_logic_snapshot",
        "runtime_sources": [
            "meridian_core.aegis.ProofTrail",
            "meridian_core.aegis.evidence_from_cross_check",
            "meridian_core.cognition_policy.evaluate_cognition_policy",
        ],
        "harness": "Aegis",
        "summary": "Display-safe Aegis proof trail and cognition-policy gate state.",
        "display_only": True,
        "mutation_authorized": False,
        "dispatch_authorized": False,
        "model_call_authorized": False,
        "raw_evidence_body_visible": False,
        "proof_trail": _proof_trail_snapshot(trail),
        "cognition_policy": _cognition_policy_snapshot(result),
        "capabilitySections": _capability_sections(),
        "guardrails": [
            "display_only",
            "no_model_calls",
            "no_live_dispatch",
            "no_review_response",
            "no_raw_evidence_body",
            "no_branch_or_worktree_movement",
        ],
    }


def _sample_proof_trail() -> ProofTrail:
    trail = ProofTrail()
    trail.add(
        evidence_from_cross_check(
            "aegis-runtime-001",
            "relay_dispatch",
            "prompt_packet",
            "PromptPacket proof metadata present",
            EvidenceSeverity.INFO,
        )
    )
    trail.add(
        evidence_from_cross_check(
            "aegis-runtime-002",
            "review_console",
            "proof_review",
            "Tier-three proof evidence must be resolved before dispatch",
            EvidenceSeverity.ERROR,
        )
    )
    return trail


def _proof_trail_snapshot(trail: ProofTrail) -> dict[str, Any]:
    return {
        "is_clean": trail.is_clean(),
        "evidence_count": len(trail.evidence),
        "blocking_count": len(trail.blocking()),
        "open_count": len(trail.open_findings()),
        "evidence": [_evidence_snapshot(evidence) for evidence in trail.evidence],
    }


def _evidence_snapshot(evidence: AegisEvidence) -> dict[str, Any]:
    return {
        "id": evidence.id,
        "type": evidence.evidence_type.value,
        "severity": evidence.severity.value,
        "status": evidence.status.value,
        "source": evidence.source,
        "target": evidence.target,
        "summary": evidence.summary,
        "proof_blocking": evidence.is_proof_blocking(),
    }


def _cognition_policy_snapshot(result: CognitionPolicyResult) -> dict[str, Any]:
    policy = result.policy
    route = result.relay_route
    return {
        "action_type": policy.action_type.value,
        "risk_tier": policy.risk_tier,
        "lanes": [_value(lane) for lane in policy.lanes],
        "requires_proof": policy.requires_proof,
        "requires_review": policy.requires_review,
        "requires_human_gate": policy.requires_human_gate,
        "reason": policy.reason,
        "decision": result.decision.value,
        "can_dispatch": result.can_dispatch,
        "blocking_reasons": list(result.blocking_reasons),
        "relay_route": {
            "risk_tier": route.risk_tier,
            "mode": _value(route.mode),
            "reason": route.reason,
            "requires_independence": route.requires_independence,
            "requires_human_gate": route.requires_human_gate,
        },
    }


def _capability_sections() -> list[dict[str, Any]]:
    return [
        {
            "title": "Aegis Job",
            "summary": "Aegis decides proof sufficiency, review pressure, human-gate requirements, and dispatch permission boundaries.",
            "rows": [
                {"key": "owns", "value": "proof trails, evidence severity, cognition policy gates, dispatch allow/block decisions"},
                {"key": "does not own", "value": "model selection, provider telemetry, UI review buttons, live session execution"},
                {"key": "display rule", "value": "surface proof summaries and evidence refs only; never raw prompts, responses, or evidence bodies"},
            ],
        },
        {
            "title": "Proof Trail Logic",
            "summary": "Aegis converts findings into ordered proof evidence and identifies proof-blocking records.",
            "rows": [
                {"key": "blocking", "value": "open error/critical evidence and escalated evidence block proof claims"},
                {"key": "non-blocking", "value": "resolved, waived, info, and warning evidence remain visible without blocking dispatch"},
                {"key": "review bridge", "value": "proof-blocking evidence can become Review Console approval gates"},
            ],
        },
        {
            "title": "Cognition Policy Gate",
            "summary": "Risk tier and action type determine proof, review, lane, and human-gate requirements before Relay dispatch.",
            "rows": [
                {"key": "tier 0-1", "value": "local or single-lane work with low proof burden"},
                {"key": "tier 2", "value": "review required without mandatory Aegis proof"},
                {"key": "tier 3", "value": "proof and review required; blocking proof evidence prevents dispatch"},
                {"key": "tier 4", "value": "human lane and explicit approval are required"},
            ],
        },
        {
            "title": "Runtime Boundary",
            "summary": "The snapshot reports Aegis decisions but cannot approve, waive, dispatch, or execute work.",
            "rows": [
                {"key": "display only", "value": "true"},
                {"key": "mutation authorized", "value": "false"},
                {"key": "model call authorized", "value": "false"},
                {"key": "raw evidence body visible", "value": "false"},
            ],
        },
    ]


def _value(item: Any) -> Any:
    if isinstance(item, Enum):
        return item.value
    return item


def main() -> None:
    print(json.dumps(aegis_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
