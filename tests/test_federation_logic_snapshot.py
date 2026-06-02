"""Tests for Federation Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.federation_logic_snapshot import federation_logic_snapshot


def test_federation_logic_snapshot_names_backend_source():
    snapshot = federation_logic_snapshot()

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.federation_logic_snapshot.federation_logic_snapshot"
    assert snapshot["harness"] == "Federation / Network"
    assert snapshot["version"] == "federation-runtime-v1"
    assert snapshot["status"] == "horizon-only"


def test_federation_logic_snapshot_documents_runtime_boundaries():
    snapshot = federation_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert "Federation Job" in titles
    assert "Discovery Consent Logic" in titles
    assert "Permission Boundary Logic" in titles
    assert "Typed Handoff Logic" in titles
    assert "Cross-Harness Relationship Logic" in titles
    assert "Runtime Boundary" in titles


def test_federation_logic_snapshot_is_display_only():
    snapshot = federation_logic_snapshot()
    boundary = next(section for section in snapshot["capabilitySections"] if section["title"] == "Runtime Boundary")
    rendered = json.dumps(boundary, sort_keys=True)

    assert "backend snapshot only" in rendered
    assert "no network protocol" in rendered
    assert "no authentication runtime" in rendered
    assert "no remote execution" in rendered
    assert snapshot["runtimeFlags"]["displayOnly"] is True
    assert snapshot["runtimeFlags"]["remoteExecution"] is False


def test_federation_logic_snapshot_uses_typed_handoff_packets():
    snapshot = federation_logic_snapshot()
    encoded = json.dumps(snapshot, sort_keys=True)

    assert "ProjectSummary" in encoded
    assert "TaskRequest" in encoded
    assert "ProofPacket" in encoded
    assert "ReviewResult" in encoded
    assert "RefusalOrBlocker" in encoded


def test_federation_logic_snapshot_is_json_serializable():
    encoded = json.dumps(federation_logic_snapshot(), sort_keys=True)

    assert "Federation / Network" in encoded
    assert "federation networking and identity/trust model remain V3 horizon work" in encoded
