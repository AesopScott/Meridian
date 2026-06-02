"""Tests for Atlas Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.atlas import DOC_ALLOWLIST, EXCLUDED_AREAS, AtlasSource
from meridian_core.atlas_logic_snapshot import atlas_logic_snapshot


def test_atlas_logic_snapshot_documents_retrieval_harness():
    snapshot = atlas_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.atlas_logic_snapshot.atlas_logic_snapshot"
    assert snapshot["harness"] == "Atlas"
    assert snapshot["limits"]["docAllowlistCount"] == len(DOC_ALLOWLIST)
    assert snapshot["limits"]["excludedAreaCount"] == len(EXCLUDED_AREAS)
    assert snapshot["limits"]["broadCrawlEnabled"] is False
    assert snapshot["limits"]["networkEnabled"] is False
    assert snapshot["limits"]["hiddenPromptInjection"] is False
    assert "Atlas Job" in titles
    assert "Retrieval Source Logic" in titles
    assert "FileMap Ranking Logic" in titles
    assert "Doc Allowlist Logic" in titles
    assert "Required Path Logic" in titles
    assert "Ordering Logic" in titles
    assert "Prompt Boundary Logic" in titles
    assert "Runtime Boundary" in titles


def test_atlas_logic_snapshot_reflects_domain_sources():
    snapshot = atlas_logic_snapshot()

    assert snapshot["sources"] == [source.value for source in AtlasSource]
    assert snapshot["docAllowlist"] == list(DOC_ALLOWLIST)
    assert snapshot["excludedAreas"] == list(EXCLUDED_AREAS)


def test_atlas_logic_snapshot_is_json_safe_and_prompt_safe():
    encoded = json.dumps(atlas_logic_snapshot(), sort_keys=True)

    assert "hidden raw transcript replay" in encoded
    assert "broad file dumps" in encoded
    assert "network" in encoded.lower()
    assert "test body" not in encoded
