"""Tests for Arbiter Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.arbiter_logic_snapshot import arbiter_logic_snapshot


def test_arbiter_logic_snapshot_names_backend_source():
    snapshot = arbiter_logic_snapshot()

    assert snapshot["source"] == "meridian_core.arbiter_logic_snapshot.arbiter_logic_snapshot"
    assert snapshot["harness"] == "Arbiter / Reviews"
    assert snapshot["version"] == "arbiter-review-console-v1"


def test_arbiter_logic_snapshot_documents_review_console_logic():
    snapshot = arbiter_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert "Review Item Shape" in titles
    assert "Item Type Logic" in titles
    assert "Severity and Status Logic" in titles
    assert "Pending Gate Logic" in titles
    assert "Prompt Metrics Finding Logic" in titles
    assert "Runtime Boundary" in titles


def test_arbiter_logic_snapshot_exposes_display_only_boundary():
    snapshot = arbiter_logic_snapshot()
    boundary = next(section for section in snapshot["capabilitySections"] if section["title"] == "Runtime Boundary")
    values = " ".join(row["value"] for row in boundary["rows"])

    assert "backend snapshot only" in values
    assert "no approve/reject/modify controls" in values
    assert "not this UI" in values


def test_arbiter_logic_snapshot_records_gate_and_informational_split():
    snapshot = arbiter_logic_snapshot()
    gates = next(section for section in snapshot["capabilitySections"] if section["title"] == "Pending Gate Logic")
    rows = {row["key"]: row["value"] for row in gates["rows"]}

    assert rows["pending gates"] == "gate"
    assert "system" in rows["informational"]
    assert "cross" in rows["informational"]
    assert rows["gate response"] == "approve -> responded"
    assert rows["acknowledge response"] == "acknowledged"


def test_arbiter_logic_snapshot_is_json_serializable():
    encoded = json.dumps(arbiter_logic_snapshot(), sort_keys=True)

    assert "Arbiter / Reviews" in encoded
    assert "Review Console" in encoded
