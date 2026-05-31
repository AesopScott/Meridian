"""Prime cockpit snapshot provider for V1 Bifrost.

Pure factory layer — no filesystem, no live queue reads, no CLI.
Accepts explicit typed inputs and returns immutable PrimeCockpitSnapshot.
"""

from __future__ import annotations

from typing import Sequence

from .cockpit_state import (
    CockpitStatus,
    EventSeverity,
    LaneCockpitStatus,
    LaneSummary,
    PrimeCockpitSnapshot,
    ProgressEvent,
    ProgressEventCategory,
    QueuePolicy,
    sort_lanes,
)


def build_snapshot(
    *,
    project: str,
    bearing: str,
    risk_tier: str,
    prime_status: CockpitStatus,
    queue_policy: QueuePolicy,
    lanes: Sequence[LaneSummary],
    progress_events: Sequence[ProgressEvent],
    review_gate_count: int,
) -> PrimeCockpitSnapshot:
    """Build an immutable PrimeCockpitSnapshot from explicit typed inputs.

    Lanes are sorted (attention-first, then by status) before storage.
    """
    if not project or not project.strip():
        raise ValueError("project must not be blank")
    if not bearing or not bearing.strip():
        raise ValueError("bearing must not be blank")
    if review_gate_count < 0:
        raise ValueError("review_gate_count must not be negative")

    return PrimeCockpitSnapshot(
        project=project,
        bearing=bearing,
        risk_tier=risk_tier,
        prime_status=prime_status,
        queue_policy=queue_policy,
        lanes=tuple(sort_lanes(list(lanes))),
        progress_events=tuple(progress_events),
        review_gate_count=review_gate_count,
    )


def demo_snapshot() -> PrimeCockpitSnapshot:
    """Return a deterministic sample snapshot for Bifrost preview wiring."""
    lanes = [
        LaneSummary(
            lane_id="build-1",
            role="domain-builder",
            status=LaneCockpitStatus.RUNNING,
            last_poll_at="2026-06-03T03:00:00",
            last_commit="f56af55",
            attention=False,
        ),
        LaneSummary(
            lane_id="build-5",
            role="bifrost-builder",
            status=LaneCockpitStatus.POLLING,
            last_poll_at="2026-06-03T03:00:00",
            last_commit="d13f1d1",
            attention=False,
        ),
        LaneSummary(
            lane_id="codex-reviews-c",
            role="reviewer",
            status=LaneCockpitStatus.IDLE,
            last_poll_at="2026-06-03T03:00:00",
            last_commit="2706806",
            attention=True,
        ),
    ]
    events = [
        ProgressEvent(
            category=ProgressEventCategory.ROUTINE_PROGRESS,
            severity=EventSeverity.INFO,
            timestamp="2026-06-03T03:00:00",
            message="V1 Bifrost cockpit domain shape complete",
        ),
        ProgressEvent(
            category=ProgressEventCategory.REVIEW_RESULT,
            severity=EventSeverity.INFO,
            timestamp="2026-06-03T03:20:00",
            message="Reviews C Rounds C3/C4/C5 cleared cadence on 4 slices",
        ),
    ]
    return build_snapshot(
        project="Meridian",
        bearing="V1 Bifrost",
        risk_tier="low",
        prime_status=CockpitStatus.ONLINE,
        queue_policy=QueuePolicy.ON,
        lanes=lanes,
        progress_events=events,
        review_gate_count=0,
    )
