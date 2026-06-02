"""Tests for the Relay logic snapshot consumed by visible harnesses."""

from __future__ import annotations

import json

from meridian_core.relay_logic_snapshot import relay_logic_snapshot


def test_snapshot_identifies_domain_source():
    snapshot = relay_logic_snapshot()

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.relay.route_from_tier"
    assert snapshot["version"] == "relay-domain-v1"


def test_route_precedence_is_account_session_first():
    snapshot = relay_logic_snapshot()

    assert snapshot["routePrecedence"][0] == "account_session"
    assert snapshot["routePrecedence"][-1] == "aggregator_api"


def test_tier3_exposes_dual_model_proof_logic():
    tier3 = relay_logic_snapshot()["tiers"][3]

    assert tier3["mode"] == "dual-lane-proof"
    assert tier3["requiresIndependence"] is True
    assert any(lane["independent"] for lane in tier3["lanes"])
    assert "independent_dual_model_lanes" in tier3["audit"]["proofRequired"]
    assert "aggregator_cannot_be_authoritative" in tier3["audit"]["fallbackBlockers"]
    assert "dual_lane_independence_required" in tier3["audit"]["fallbackBlockers"]


def test_tier3_exposes_dispatch_plan_without_prompt_text():
    tier3 = relay_logic_snapshot()["tiers"][3]
    dispatch = tier3["dispatch"]

    assert dispatch["source"] == "meridian_core.relay_dispatch.build_relay_dispatch_plan"
    assert dispatch["laneCount"] == 3
    assert dispatch["laneOrder"] == ["builder", "reviewer", "verifier"]
    assert dispatch["payloadPolicy"] == "model_payload_only"
    assert dispatch["payloadTextVisible"] is False
    assert all(lane["payloadEqualsModelPayload"] for lane in dispatch["lanes"])
    assert not any(lane["payloadIncludesPacketMetadata"] for lane in dispatch["lanes"])


def test_tier3_exposes_audit_depth_for_no_silent_fallback():
    tier3 = relay_logic_snapshot()["tiers"][3]
    audit_depth = tier3["auditDepth"]

    assert audit_depth["routeClass"] == "account_session"
    assert audit_depth["sessionAction"] == "start_new"
    assert audit_depth["trustState"] == "candidate"
    assert audit_depth["contextHealth"] == "clean"
    assert audit_depth["alternativesRejectedCount"] >= 2
    assert audit_depth["fallbackBlockerCount"] >= 5
    assert audit_depth["proofRequiredCount"] >= 3
    assert audit_depth["telemetryRequiredCount"] >= 7
    assert audit_depth["silentFallbackBlocked"] is True
    assert audit_depth["primaryFallbackBlocker"] == "unknown_trust_route"


def test_tier4_audit_depth_blocks_autonomous_fallback():
    tier4 = relay_logic_snapshot()["tiers"][4]
    audit_depth = tier4["auditDepth"]

    assert audit_depth["trustState"] == "blocked"
    assert audit_depth["silentFallbackBlocked"] is True
    assert audit_depth["primaryFallbackBlocker"] == "human_gate_required"
    assert audit_depth["primaryProofRequirement"] == "human_gate_approval"


def test_snapshot_exposes_capability_sections_for_harness_headers():
    snapshot = relay_logic_snapshot()
    section_titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert section_titles == [
        "Relay Job",
        "Risk Tier Routing",
        "Model Lane Logic",
        "Access Route Precedence",
        "Session Lifecycle Logic",
        "Context Latency Privacy",
        "Prompt Budget Logic",
        "Audit Logic",
        "Dispatch Logic",
        "Current Limits",
    ]
    assert all(section["summary"] for section in snapshot["capabilitySections"])
    assert all(section["rows"] for section in snapshot["capabilitySections"])


def test_snapshot_exposes_relay_prime_directives_and_proofs():
    snapshot = relay_logic_snapshot()

    assert [item["name"] for item in snapshot["primeDirectives"]] == [
        "Account/session-first, never silent fallback",
        "Risk tier determines model depth",
        "No drift between route, proof, and visible harness",
    ]
    assert [item["proves"] for item in snapshot["primeDirectiveProofs"]] == [
        "account/session-first precedence and no silent fallback",
        "risk-tier routing depth and autonomy limits",
        "no drift between backend Relay and visible harness evidence",
    ]


def test_capability_sections_include_expert_relay_depth():
    rendered = json.dumps(relay_logic_snapshot()["capabilitySections"], sort_keys=True)

    assert "model-routing brain" in rendered
    assert "account/session-first" in rendered
    assert "dual-lane" in rendered
    assert "model_payload_only" in rendered
    assert "Auto stays disabled" in rendered


def test_tier4_exposes_human_gate_block():
    tier4 = relay_logic_snapshot()["tiers"][4]

    assert tier4["mode"] == "human-gate"
    assert tier4["requiresHumanGate"] is True
    assert tier4["audit"]["trustState"] == "blocked"
    assert "human_gate_required" in tier4["audit"]["fallbackBlockers"]


def test_snapshot_is_json_serializable_and_relay_only():
    rendered = json.dumps(relay_logic_snapshot(), sort_keys=True)

    assert "heartbeat" not in rendered.lower()
