"""
Mission boot protocol loader.

Locates and parses MISSION.md, returning a structured Mission object.
Prime reads this before meaningful action.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class MissionLoadError(Exception):
    """Raised when MISSION.md is missing, unreadable, or structurally incomplete."""


@dataclass
class PrimeDirective:
    number: int
    text: str


@dataclass
class QueueDisplayGuidance:
    orchestrator_queue: str
    non_orchestrator_queue: str


@dataclass
class Mission:
    directives: list[PrimeDirective] = field(default_factory=list)
    harness_boot_order: list[str] = field(default_factory=list)
    current_objective: str = ""
    queue_guidance: QueueDisplayGuidance = field(
        default_factory=lambda: QueueDisplayGuidance("", "")
    )


_REQUIRED_SECTIONS = frozenset(
    {"Prime Directives", "Harness Boot Order", "Current Mission Objective", "Queue Display Guidance"}
)


def find_mission_file(start: Path | None = None) -> Path:
    """
    Walk upward from `start` (default: cwd) looking for MISSION.md.
    Raises MissionLoadError if not found.
    """
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / "MISSION.md"
        if candidate.exists():
            return candidate
    raise MissionLoadError(
        f"MISSION.md not found searching upward from {start or Path.cwd()}"
    )


def load_mission(path: Path) -> Mission:
    """
    Parse MISSION.md at `path` and return a Mission object.
    Raises MissionLoadError if the file is missing or a required section is absent.
    """
    if not path.exists():
        raise MissionLoadError(f"Mission file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissionLoadError(f"Cannot read mission file: {exc}") from exc

    sections = _parse_sections(text)
    missing = _REQUIRED_SECTIONS - set(sections)
    if missing:
        raise MissionLoadError(
            f"Mission file missing required section(s): {', '.join(sorted(missing))}"
        )

    directives = [
        PrimeDirective(number=i + 1, text=item)
        for i, item in enumerate(_parse_numbered_list(sections["Prime Directives"]))
    ]
    boot_order = _parse_numbered_list(sections["Harness Boot Order"])
    objective = sections["Current Mission Objective"].strip()
    queue_guidance = _parse_queue_guidance(sections["Queue Display Guidance"])

    return Mission(
        directives=directives,
        harness_boot_order=boot_order,
        current_objective=objective,
        queue_guidance=queue_guidance,
    )


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------


def _parse_sections(text: str) -> dict[str, str]:
    """Split markdown into {section_title: section_body} for ## headings."""
    sections: dict[str, str] = {}
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        title, _, body = part.partition("\n")
        sections[title.strip()] = body.strip()
    return sections


def _parse_numbered_list(text: str) -> list[str]:
    """Extract items from a numbered markdown list, in order."""
    items = []
    for line in text.splitlines():
        match = re.match(r"^\d+\.\s+(.*)", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def _parse_queue_guidance(text: str) -> QueueDisplayGuidance:
    """Parse Orchestrator Queue / Non-Orchestrator Queue descriptions."""
    orchestrator: list[str] = []
    non_orchestrator: list[str] = []
    current: list[str] | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "Orchestrator Queue:":
            current = orchestrator
        elif stripped == "Non-Orchestrator Queue:":
            current = non_orchestrator
        elif current is not None:
            current.append(line)

    return QueueDisplayGuidance(
        orchestrator_queue="\n".join(orchestrator).strip(),
        non_orchestrator_queue="\n".join(non_orchestrator).strip(),
    )
