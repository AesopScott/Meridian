"""Tests for the Aegis Runtime Logic snapshot."""

from __future__ import annotations

import json

from meridian_core.aegis_logic_snapshot import aegis_logic_snapshot


def test_aegis_logic_snapshot_documents_proof_harness() -> None:
    snapshot = aegis_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.aegis_logic_snapshot.aegis_logic_snapshot"
    assert snapshot["harness"] == "Aegis"
    assert "Aegis Job" in titles
    assert "Proof Gate Logic" in titles
    assert "PromptPacket Policy Logic" in titles
    assert "Prompt Payload Meter Logic" in titles
    assert "Provider Result Validation Logic" in titles
    assert "Command Staging UI Review Logic" in titles
    assert "Runtime Boundary Logic" in titles


def test_aegis_logic_snapshot_is_json_serializable() -> None:
    rendered = json.dumps(aegis_logic_snapshot(), sort_keys=True)

    assert "Aegis Runtime Logic" not in rendered
    assert "proof gates" in rendered
    assert "safe outputs" in rendered


def test_aegis_logic_snapshot_excludes_raw_sensitive_payloads() -> None:
    rendered = json.dumps(aegis_logic_snapshot(), sort_keys=True).lower()

    blocked_terms = (
        "raw prompt text:",
        "raw provider response:",
        "api_key=",
        "secret_value",
        "authorization:",
        "password=",
    )
    for term in blocked_terms:
        assert term not in rendered
