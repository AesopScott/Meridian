"""Tests for Beacon runtime logic snapshot."""

from __future__ import annotations

import json

from meridian_core.beacon_logic_snapshot import beacon_logic_snapshot


def test_beacon_logic_snapshot_is_display_safe_backend_contract():
    snapshot = beacon_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]
    rendered = json.dumps(snapshot, sort_keys=True)

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.beacon_logic_snapshot.beacon_logic_snapshot"
    assert snapshot["harness"] == "Beacon"
    assert "Beacon Job" in titles
    assert "Liveness Target Logic" in titles
    assert "Heartbeat Status Logic" in titles
    assert "Advisory Evidence Logic" in titles
    assert "Runtime Boundary" in titles
    assert "Cross-Harness Relationship Logic" in titles
    assert "no restart" in rendered
    assert "without creating hidden controls" in rendered


def test_beacon_logic_snapshot_names_observation_not_execution():
    snapshot = beacon_logic_snapshot()
    rendered = json.dumps(snapshot, sort_keys=True).lower()

    assert "observes runtime state" in rendered
    assert "display-only" in rendered
    assert "cannot execute recovery" in rendered
    assert "branch movement" in rendered
    assert "worktree mutation" in rendered
