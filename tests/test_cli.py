"""Tests for the prime_wake CLI command."""

from __future__ import annotations

from pathlib import Path

from meridian_core.cli import prime_wake

_VALID_MISSION = """\
# Meridian Mission

## Prime Directives

1. Logic, not rules.
2. Prime reads this mission file before meaningful action.
3. Prime states progress intention before meaningful work.

## Harness Boot Order

1. Bifrost
2. Beacon
3. Echo

## Current Mission Objective

Build the V0 prime wake surface.

## Queue Display Guidance

Orchestrator Queue:
Prime's conversational messages.

Non-Orchestrator Queue:
System messages and harness health.
"""


class TestPrimeWakeSuccess:
    def test_output_includes_mission_objective(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Build the V0 prime wake surface" in out

    def test_output_includes_prime_online_title(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Prime online." in out

    def test_output_includes_canonical_harness_statuses(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        for harness in ("Bifrost", "Beacon", "Relay", "Groot"):
            assert harness in out, f"{harness} missing from wake output"

    def test_output_is_deterministic(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        prime_wake(mission_path=f)
        first = capsys.readouterr().out
        prime_wake(mission_path=f)
        second = capsys.readouterr().out
        assert first == second


class TestPrimeWakeMissionFailure:
    def test_missing_mission_prints_readable_failure(self, tmp_path: Path, capsys) -> None:
        prime_wake(mission_path=tmp_path / "MISSION.md")
        out = capsys.readouterr().out
        assert "Mission load failed" in out

    def test_corrupt_mission_prints_readable_failure(self, tmp_path: Path, capsys) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text("# Broken\nNo sections here.", encoding="utf-8")
        prime_wake(mission_path=f)
        out = capsys.readouterr().out
        assert "Mission load failed" in out

    def test_missing_mission_does_not_raise(self, tmp_path: Path) -> None:
        prime_wake(mission_path=tmp_path / "MISSION.md")

    def test_corrupt_mission_does_not_raise(self, tmp_path: Path) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text("garbage", encoding="utf-8")
        prime_wake(mission_path=f)
