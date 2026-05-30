"""Tests for the Mission boot protocol loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from meridian_core.mission import (
    Mission,
    MissionLoadError,
    PrimeDirective,
    QueueDisplayGuidance,
    find_mission_file,
    load_mission,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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

Build the boot protocol slice.

## Queue Display Guidance

Orchestrator Queue:
Prime's conversational messages.

Non-Orchestrator Queue:
System messages and harness health.
"""


@pytest.fixture
def mission_file(tmp_path: Path) -> Path:
    f = tmp_path / "MISSION.md"
    f.write_text(_VALID_MISSION, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Successful load
# ---------------------------------------------------------------------------


class TestSuccessfulLoad:
    def test_returns_mission_object(self, mission_file: Path) -> None:
        result = load_mission(mission_file)
        assert isinstance(result, Mission)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(MissionLoadError, match="not found"):
            load_mission(tmp_path / "MISSING.md")


# ---------------------------------------------------------------------------
# Prime Directives
# ---------------------------------------------------------------------------


class TestPrimeDirectives:
    def test_directives_parsed_in_order(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert [d.number for d in mission.directives] == [1, 2, 3]

    def test_directive_text_matches_source(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.directives[0].text == "Logic, not rules."
        assert mission.directives[1].text == "Prime reads this mission file before meaningful action."
        assert mission.directives[2].text == "Prime states progress intention before meaningful work."

    def test_directive_numbers_are_one_indexed(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.directives[0].number == 1

    def test_directive_type(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert all(isinstance(d, PrimeDirective) for d in mission.directives)


# ---------------------------------------------------------------------------
# Harness boot order
# ---------------------------------------------------------------------------


class TestHarnessBootOrder:
    def test_boot_order_parsed_in_order(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.harness_boot_order == ["Bifrost", "Beacon", "Echo"]

    def test_full_boot_order_from_real_mission(self) -> None:
        real = Path(__file__).parent.parent / "MISSION.md"
        mission = load_mission(real)
        assert mission.harness_boot_order[0] == "Bifrost"
        assert mission.harness_boot_order[-1] == "Launch"
        assert len(mission.harness_boot_order) == 14

    def test_boot_order_first_is_bifrost(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.harness_boot_order[0] == "Bifrost"


# ---------------------------------------------------------------------------
# Current mission objective
# ---------------------------------------------------------------------------


class TestCurrentObjective:
    def test_objective_is_parsed(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.current_objective == "Build the boot protocol slice."

    def test_objective_is_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(
            _VALID_MISSION.replace(
                "Build the boot protocol slice.",
                "\n  Build the boot protocol slice.  \n",
            ),
            encoding="utf-8",
        )
        mission = load_mission(f)
        assert mission.current_objective == "Build the boot protocol slice."


# ---------------------------------------------------------------------------
# Queue display guidance
# ---------------------------------------------------------------------------


class TestQueueDisplayGuidance:
    def test_guidance_type(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert isinstance(mission.queue_guidance, QueueDisplayGuidance)

    def test_orchestrator_queue_parsed(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert "Prime's conversational messages" in mission.queue_guidance.orchestrator_queue

    def test_non_orchestrator_queue_parsed(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert "System messages" in mission.queue_guidance.non_orchestrator_queue

    def test_queues_are_distinct(self, mission_file: Path) -> None:
        mission = load_mission(mission_file)
        assert mission.queue_guidance.orchestrator_queue != mission.queue_guidance.non_orchestrator_queue

    def test_real_mission_orchestrator_content(self) -> None:
        real = Path(__file__).parent.parent / "MISSION.md"
        mission = load_mission(real)
        assert "progress intentions" in mission.queue_guidance.orchestrator_queue

    def test_real_mission_non_orchestrator_content(self) -> None:
        real = Path(__file__).parent.parent / "MISSION.md"
        mission = load_mission(real)
        assert "NASA-style Go calls" in mission.queue_guidance.non_orchestrator_queue

    def test_real_mission_non_orchestrator_is_prompt_window(self) -> None:
        real = Path(__file__).parent.parent / "MISSION.md"
        mission = load_mission(real)
        assert "prompt window" in mission.queue_guidance.non_orchestrator_queue


# ---------------------------------------------------------------------------
# Missing required sections
# ---------------------------------------------------------------------------


class TestMissingSection:
    @pytest.mark.parametrize("section", [
        "Prime Directives",
        "Harness Boot Order",
        "Current Mission Objective",
        "Queue Display Guidance",
    ])
    def test_missing_section_raises(self, tmp_path: Path, section: str) -> None:
        truncated = "\n".join(
            line for line in _VALID_MISSION.splitlines()
            if section not in line
        )
        f = tmp_path / "MISSION.md"
        f.write_text(truncated, encoding="utf-8")
        with pytest.raises(MissionLoadError, match="missing required section"):
            load_mission(f)


# ---------------------------------------------------------------------------
# find_mission_file
# ---------------------------------------------------------------------------


class TestFindMissionFile:
    def test_finds_file_in_start_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        assert find_mission_file(tmp_path) == f

    def test_finds_file_in_parent_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "MISSION.md"
        f.write_text(_VALID_MISSION, encoding="utf-8")
        child = tmp_path / "subdir"
        child.mkdir()
        assert find_mission_file(child) == f

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        empty = tmp_path / "deep" / "nested"
        empty.mkdir(parents=True)
        with pytest.raises(MissionLoadError, match="not found"):
            find_mission_file(empty)

    def test_real_repo_mission_is_findable(self) -> None:
        repo_root = Path(__file__).parent.parent
        found = find_mission_file(repo_root)
        assert found.name == "MISSION.md"
