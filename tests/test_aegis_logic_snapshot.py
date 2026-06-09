"""Tests for the backend-owned Aegis runtime logic snapshot."""

from __future__ import annotations

import json

from meridian_core.aegis_logic_snapshot import (
    SNAPSHOT_VERSION,
    aegis_logic_snapshot,
)


def test_aegis_logic_snapshot_is_display_safe_backend_contract():
    snapshot = aegis_logic_snapshot()
    serialized = json.dumps(snapshot, sort_keys=True)

    assert snapshot["ok"] is True
    assert snapshot["version"] == SNAPSHOT_VERSION
    assert snapshot["source"] == "meridian_core.aegis_logic_snapshot.aegis_logic_snapshot"
    assert snapshot["harness"] == "Aegis"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert snapshot["dispatch_authorized"] is False
    assert snapshot["model_call_authorized"] is False
    assert snapshot["raw_evidence_body_visible"] is False
    assert "RAW_EVIDENCE_BODY_SENTINEL" not in serialized
    assert "full evidence body" not in serialized
    assert "serialized_prompt" not in serialized
    assert "provider_response" not in serialized


def test_aegis_logic_snapshot_uses_reviewed_runtime_sources():
    snapshot = aegis_logic_snapshot()

    assert snapshot["runtime_sources"] == [
        "meridian_core.aegis.ProofTrail",
        "meridian_core.aegis.evidence_from_cross_check",
        "meridian_core.cognition_policy.evaluate_cognition_policy",
    ]
    assert any(
        section["title"] == "Proof Trail Logic"
        for section in snapshot["capabilitySections"]
    )
    assert any(
        section["title"] == "Cognition Policy Gate"
        for section in snapshot["capabilitySections"]
    )


def test_aegis_logic_snapshot_summarizes_proof_trail():
    trail = aegis_logic_snapshot()["proof_trail"]

    assert trail["is_clean"] is False
    assert trail["evidence_count"] == 2
    assert trail["blocking_count"] == 1
    assert trail["open_count"] == 2
    assert trail["evidence"] == [
        {
            "id": "aegis-runtime-001",
            "type": "cross_check",
            "severity": "info",
            "status": "open",
            "source": "relay_dispatch",
            "target": "prompt_packet",
            "summary": "PromptPacket proof metadata present",
            "proof_blocking": False,
        },
        {
            "id": "aegis-runtime-002",
            "type": "cross_check",
            "severity": "error",
            "status": "open",
            "source": "review_console",
            "target": "proof_review",
            "summary": "Tier-three proof evidence must be resolved before dispatch",
            "proof_blocking": True,
        },
    ]


def test_aegis_logic_snapshot_blocks_dispatch_on_proof_failure():
    policy = aegis_logic_snapshot()["cognition_policy"]

    assert policy["action_type"] == "build"
    assert policy["risk_tier"] == 3
    assert policy["lanes"] == ["builder", "reviewer", "verifier"]
    assert policy["requires_proof"] is True
    assert policy["requires_review"] is True
    assert policy["requires_human_gate"] is False
    assert policy["decision"] == "blocked_by_proof"
    assert policy["can_dispatch"] is False
    assert policy["blocking_reasons"] == [
        "aegis-runtime-002: Tier-three proof evidence must be resolved before dispatch"
    ]
    assert policy["relay_route"]["risk_tier"] == 3
    assert policy["relay_route"]["requires_independence"] is True


def test_aegis_logic_snapshot_explains_tier_policy_without_human_gate_drift():
    sections = aegis_logic_snapshot()["capabilitySections"]
    policy_section = next(
        section for section in sections if section["title"] == "Cognition Policy Gate"
    )
    rows = {row["key"]: row["value"] for row in policy_section["rows"]}

    assert rows["tier 2"] == "review required without mandatory Aegis proof"
    assert rows["tier 3"] == "proof and review required; blocking proof evidence prevents dispatch"
    assert rows["tier 4"] == "human lane and explicit approval are required"


def test_aegis_logic_snapshot_guardrails_are_non_executable():
    snapshot = aegis_logic_snapshot()

    assert snapshot["guardrails"] == [
        "display_only",
        "no_model_calls",
        "no_live_dispatch",
        "no_review_response",
        "no_raw_evidence_body",
        "no_branch_or_worktree_movement",
    ]
