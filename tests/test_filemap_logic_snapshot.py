"""Tests for Charon/FileMap runtime logic snapshot."""

import json

from meridian_core.filemap import make_default_map
from meridian_core.filemap_logic_snapshot import filemap_logic_snapshot


def test_filemap_logic_snapshot_uses_default_filemap_counts():
    filemap = make_default_map()
    snapshot = filemap_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.filemap_logic_snapshot.filemap_logic_snapshot"
    assert snapshot["harness"] == "Charon / FileMap"
    assert snapshot["totals"]["entries"] == len(filemap.all_entries())
    assert snapshot["totals"]["entriesWithTests"] == len(filemap.with_tests())
    assert "Charon Job" in titles
    assert "Registry Shape Logic" in titles
    assert "Lookup Logic" in titles
    assert "Required Path Coverage" in titles
    assert "Runtime Boundary" in titles


def test_filemap_logic_snapshot_keeps_required_paths_registered():
    snapshot = filemap_logic_snapshot()
    required_section = next(
        section
        for section in snapshot["capabilitySections"]
        if section["title"] == "Required Path Coverage"
    )

    assert {row["value"] for row in required_section["rows"]} == {"registered"}
    assert {row["key"] for row in required_section["rows"]} >= {
        "MISSION.md",
        "docs/FileMap.md",
        "meridian_core/filemap.py",
        "index.html",
    }


def test_filemap_logic_snapshot_is_display_safe_boundary():
    snapshot = filemap_logic_snapshot()
    rendered = json.dumps(snapshot, sort_keys=True)

    assert "does not edit files" in rendered
    assert "does not own" in rendered
    assert "no writes" in rendered
    assert "FileMapEntry.related_tests" in rendered
