"""
Prime wake sequence builder.

Reads portfolio and harness state to produce a structured WakeBrief.
Every line maps to a real system check or a known placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .decisions import DecisionResult
from .models import Heartbeat, HeartbeatStatus, Portfolio


class WakeStatus(Enum):
    ONLINE = "online"
    STABLE = "stable"
    STANDING_BY = "standing_by"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class WakeLine:
    label: str
    status: WakeStatus
    message: str


@dataclass
class WakeBrief:
    title: str
    lines: list[WakeLine] = field(default_factory=list)
    summary: str = ""
    bottlenecks: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


# Harness ID → presentation label, in canonical wake order.
_HARNESS_LABELS: dict[str, str] = {
    "ui_harness": "Bifrost",
    "health_harness": "Beacon",
    "memory_harness": "Echo",
    "knowledge_harness": "Atlas",
    "vault_harness": "Vault",
    "tool_harness": "Forge",
    "proof_harness": "Aegis",
    "policy_harness": "Charter",
    "workflow_harness": "Loom",
    "portfolio_harness": "Compass",
    "agent_harness": "Relay",
    "git_harness": "Groot",
    "browser_harness": "Lens",
    "release_harness": "Launch",
}

_CANONICAL_ORDER: list[str] = list(_HARNESS_LABELS.keys())

_HEARTBEAT_TO_WAKE: dict[HeartbeatStatus, WakeStatus] = {
    HeartbeatStatus.ALIVE: WakeStatus.ONLINE,
    HeartbeatStatus.BUSY: WakeStatus.STABLE,
    HeartbeatStatus.SLEEPING: WakeStatus.STANDING_BY,
    HeartbeatStatus.STALE: WakeStatus.DEGRADED,
    HeartbeatStatus.BLOCKED: WakeStatus.BLOCKED,
    HeartbeatStatus.FAILED: WakeStatus.OFFLINE,
}

_STATUS_WORDS: dict[WakeStatus, str] = {
    WakeStatus.ONLINE: "online",
    WakeStatus.STABLE: "stable",
    WakeStatus.STANDING_BY: "standing by",
    WakeStatus.DEGRADED: "degraded",
    WakeStatus.BLOCKED: "blocked",
    WakeStatus.OFFLINE: "offline",
    WakeStatus.UNKNOWN: "pending",
}

_UNHEALTHY: frozenset[HeartbeatStatus] = frozenset(
    {HeartbeatStatus.BLOCKED, HeartbeatStatus.STALE, HeartbeatStatus.FAILED}
)


def _make_wake_line(harness_id: str, heartbeat: Optional[Heartbeat]) -> WakeLine:
    label = _HARNESS_LABELS.get(harness_id, harness_id)
    status = _HEARTBEAT_TO_WAKE.get(heartbeat.status, WakeStatus.UNKNOWN) if heartbeat else WakeStatus.UNKNOWN
    word = _STATUS_WORDS[status]
    return WakeLine(label=label, status=status, message=f"{label} {word}.")


def _build_summary(
    portfolio: Portfolio,
    heartbeats: list[Heartbeat],
    decision_result: DecisionResult,
) -> str:
    initiative_count = len(portfolio.all_initiatives())
    stalled_count = sum(1 for hb in heartbeats if hb.status in _UNHEALTHY)
    bottleneck_count = len(decision_result.scott_bottlenecks)

    parts: list[str] = []

    if initiative_count == 1:
        parts.append("1 initiative active.")
    elif initiative_count > 1:
        parts.append(f"{initiative_count} initiatives active.")

    if stalled_count == 1:
        parts.append("1 harness needs attention.")
    elif stalled_count > 1:
        parts.append(f"{stalled_count} harnesses need attention.")

    if bottleneck_count == 1:
        parts.append("1 decision needs your judgment.")
    elif bottleneck_count > 1:
        parts.append(f"{bottleneck_count} decisions need your judgment.")

    return " ".join(parts) if parts else "All systems nominal."


def build_wake_brief(
    portfolio: Portfolio,
    heartbeats: list[Heartbeat],
    decision_result: DecisionResult,
) -> WakeBrief:
    """
    Build a structured wake brief from real portfolio and harness state.

    Lines follow canonical harness order; unrecognized harnesses appear
    at the end sorted by ID.
    """
    hb_by_id = {hb.harness_id: hb for hb in heartbeats}

    lines: list[WakeLine] = []
    seen: set[str] = set()

    for harness_id in _CANONICAL_ORDER:
        lines.append(_make_wake_line(harness_id, hb_by_id.get(harness_id)))
        seen.add(harness_id)

    for harness_id in sorted(hb_by_id.keys()):
        if harness_id not in seen:
            lines.append(_make_wake_line(harness_id, hb_by_id[harness_id]))

    return WakeBrief(
        title="Prime online.",
        lines=lines,
        summary=_build_summary(portfolio, heartbeats, decision_result),
        bottlenecks=[bn.title for bn in decision_result.scott_bottlenecks],
        recommended_actions=[
            move.description for move in decision_result.safe_next_moves
        ] + [
            f"Inject directive to {inj.target_session_id}"
            for inj in decision_result.injections
        ],
    )
