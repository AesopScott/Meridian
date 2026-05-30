"""Beacon liveness checks for Meridian harnesses.

V0 Beacon is intentionally small: it turns flat-file queue or sentinel file
freshness into the existing Heartbeat domain model. Process supervision,
session spawning, and restart/resteer actions belong to later Prime slices.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import Heartbeat, HeartbeatStatus


@dataclass(frozen=True)
class LivenessTarget:
    """A file-backed liveness target for one harness or worker lane."""

    harness_id: str
    path: Path
    stale_after_seconds: int = 300


def check_harness_liveness(
    targets: list[LivenessTarget] | tuple[LivenessTarget, ...],
    *,
    now: datetime | None = None,
) -> tuple[Heartbeat, ...]:
    """Return one Heartbeat per target based on file freshness."""
    checked_at = _as_utc(now or datetime.now(timezone.utc))
    heartbeats: list[Heartbeat] = []
    for target in targets:
        heartbeats.append(_check_target(target, checked_at))
    return tuple(heartbeats)


def _check_target(target: LivenessTarget, checked_at: datetime) -> Heartbeat:
    if target.stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be zero or greater")

    if not target.path.exists():
        return Heartbeat(
            harness_id=target.harness_id,
            status=HeartbeatStatus.FAILED,
            current_work=str(target.path),
            last_event="liveness sentinel missing",
            blockers=[f"missing sentinel: {target.path}"],
            updated_at=checked_at,
        )

    modified_at = datetime.fromtimestamp(target.path.stat().st_mtime, timezone.utc)
    age_seconds = max(0, int((checked_at - modified_at).total_seconds()))
    status = (
        HeartbeatStatus.ALIVE
        if age_seconds <= target.stale_after_seconds
        else HeartbeatStatus.STALE
    )
    blockers = (
        [f"stale for {age_seconds}s; threshold {target.stale_after_seconds}s"]
        if status is HeartbeatStatus.STALE
        else []
    )
    return Heartbeat(
        harness_id=target.harness_id,
        status=status,
        current_work=str(target.path),
        last_event=f"sentinel updated {age_seconds}s ago",
        blockers=blockers,
        updated_at=checked_at,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
