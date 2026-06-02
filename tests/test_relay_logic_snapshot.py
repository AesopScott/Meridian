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


def test_tier4_exposes_human_gate_block():
    tier4 = relay_logic_snapshot()["tiers"][4]

    assert tier4["mode"] == "human-gate"
    assert tier4["requiresHumanGate"] is True
    assert tier4["audit"]["trustState"] == "blocked"
    assert "human_gate_required" in tier4["audit"]["fallbackBlockers"]


def test_snapshot_is_json_serializable_and_relay_only():
    rendered = json.dumps(relay_logic_snapshot(), sort_keys=True)

    assert "heartbeat" not in rendered.lower()
