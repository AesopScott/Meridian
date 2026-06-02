"""Tests for Source/Git Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.source_git_logic_snapshot import source_git_logic_snapshot


def test_source_git_logic_snapshot_names_backend_source():
    snapshot = source_git_logic_snapshot()

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.source_git_logic_snapshot.source_git_logic_snapshot"
    assert snapshot["harness"] == "Source / Git"
    assert snapshot["version"] == "source-git-runtime-v1"
    assert snapshot["status"] == "coordination-display-only"


def test_source_git_logic_snapshot_documents_coordination_gates():
    snapshot = source_git_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert "Source/Git Job" in titles
    assert "Main Write Gate Logic" in titles
    assert "Clean-State Logic" in titles
    assert "Completion Proof Logic" in titles
    assert "Runtime Boundary" in titles


def test_source_git_logic_snapshot_is_display_only():
    snapshot = source_git_logic_snapshot()
    boundary = next(section for section in snapshot["capabilitySections"] if section["title"] == "Runtime Boundary")
    rendered = json.dumps(boundary, sort_keys=True)

    assert "backend snapshot only" in rendered
    assert "no commit" in rendered
    assert "no push" in rendered
    assert "no merge" in rendered
    assert snapshot["runtimeFlags"]["displayOnly"] is True
    assert snapshot["runtimeFlags"]["push"] is False
    assert snapshot["runtimeFlags"]["reset"] is False


def test_source_git_logic_snapshot_names_main_write_protocol_sources():
    snapshot = source_git_logic_snapshot()

    assert "docs/main-write-coordination-handoff.md" in snapshot["sourceRefs"]
    assert "docs/main-write-coordination-ledger.md" in snapshot["sourceRefs"]
    assert "docs/ui-integration-checklist.md" in snapshot["sourceRefs"]


def test_source_git_logic_snapshot_is_json_serializable():
    encoded = json.dumps(source_git_logic_snapshot(), sort_keys=True)

    assert "Source / Git" in encoded
    assert "default window is 10 minutes after ACK" in encoded
