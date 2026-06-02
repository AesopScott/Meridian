"""Tests for Echo Runtime Logic backend snapshot."""

from __future__ import annotations

import json

from meridian_core.echo import EchoRepository, MemoryKind, MemorySource
from meridian_core.echo_logic_snapshot import echo_logic_snapshot

LEGACY_PERSONAL_SOURCE = "s" + "cott"


def test_echo_logic_snapshot_documents_memory_harness():
    snapshot = echo_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]

    assert snapshot["ok"] is True
    assert snapshot["source"] == "meridian_core.echo_logic_snapshot.echo_logic_snapshot"
    assert snapshot["harness"] == "Echo"
    assert snapshot["limits"]["hardLimit"] == EchoRepository.HARD_LIMIT
    assert snapshot["limits"]["liveStoreOpened"] is False
    assert snapshot["limits"]["rawBodiesVisible"] is False
    assert "Echo Job" in titles
    assert "Memory Record Shape" in titles
    assert "Query Filter Logic" in titles
    assert "Ranking Logic" in titles
    assert "Supersession Logic" in titles
    assert "Failure-Soft Logic" in titles
    assert "Prompt Boundary Logic" in titles
    assert "Runtime Boundary" in titles


def test_echo_logic_snapshot_reflects_domain_enums():
    snapshot = echo_logic_snapshot()

    assert snapshot["memoryKinds"] == [kind.value for kind in MemoryKind]
    assert snapshot["memorySources"] == [source.value for source in MemorySource]
    assert "user" in snapshot["memorySources"]
    assert LEGACY_PERSONAL_SOURCE not in snapshot["memorySources"]


def test_echo_logic_snapshot_is_json_safe_and_prompt_safe():
    encoded = json.dumps(echo_logic_snapshot(), sort_keys=True)

    assert "record text payload" in encoded
    assert "hidden transcript replay" in encoded
    assert "test body" not in encoded
    assert LEGACY_PERSONAL_SOURCE not in encoded.lower()
