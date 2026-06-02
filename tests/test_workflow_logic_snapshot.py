"""Tests for Workflow Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.workflow_logic_snapshot import workflow_logic_snapshot


def test_workflow_logic_snapshot_names_backend_source():
    snapshot = workflow_logic_snapshot()

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.workflow_logic_snapshot.workflow_logic_snapshot"
    assert snapshot["harness"] == "Workflow / Sub-agents"
    assert snapshot["version"] == "workflow-runtime-v1"


def test_workflow_logic_snapshot_documents_runtime_boundaries():
    snapshot = workflow_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert "Work Order Logic" in titles
    assert "Input Boundary Logic" in titles
    assert "Heartbeat and Result Logic" in titles
    assert "Recovery Advice Logic" in titles
    assert "Prompt-Drag Boundary" in titles
    assert "Runtime Boundary" in titles


def test_workflow_logic_snapshot_is_display_only():
    snapshot = workflow_logic_snapshot()
    boundary = next(section for section in snapshot["capabilitySections"] if section["title"] == "Runtime Boundary")
    rendered = json.dumps(boundary, sort_keys=True)

    assert "backend snapshot only" in rendered
    assert "no workflow dispatch" in rendered
    assert "no live session mutation" in rendered


def test_workflow_logic_snapshot_exposes_current_recovery_enums():
    snapshot = workflow_logic_snapshot()
    heartbeat = {row["value"] for row in snapshot["enumValues"]["heartbeat"]}
    result = {row["value"] for row in snapshot["enumValues"]["result"]}

    assert {"fresh", "warning", "stale", "missing"} <= heartbeat
    assert {"pending", "succeeded", "timeout", "resteer_requested"} <= result


def test_workflow_logic_snapshot_is_json_serializable():
    encoded = json.dumps(workflow_logic_snapshot(), sort_keys=True)

    assert "Workflow / Sub-agents" in encoded
    assert "workflow_dispatch runtime remains V2 implementation work" in encoded
