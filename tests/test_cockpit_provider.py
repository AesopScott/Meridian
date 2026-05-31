"""Tests for Prime cockpit snapshot provider."""

from __future__ import annotations

import pytest

from meridian_core.cockpit_state import (
    CockpitStatus,
    EventSeverity,
    LaneCockpitStatus,
    LaneSummary,
    ProgressEvent,
    ProgressEventCategory,
    QueuePolicy,
)
from meridian_core.cockpit_provider import build_snapshot, demo_snapshot


def _lane(
    lane_id: str,
    status: LaneCockpitStatus = LaneCockpitStatus.IDLE,
    attention: bool = False,
) -> LaneSummary:
    return LaneSummary(
        lane_id=lane_id,
        role="builder",
        status=status,
        last_poll_at="2026-06-03T00:00:00",
        last_commit="abc1234",
        attention=attention,
    )


def _event(
    category: ProgressEventCategory = ProgressEventCategory.ROUTINE_PROGRESS,
    severity: EventSeverity = EventSeverity.INFO,
) -> ProgressEvent:
    return ProgressEvent(
        category=category,
        severity=severity,
        timestamp="2026-06-03T00:00:00",
        message="test",
    )


def _base_kwargs(**overrides):
    defaults = dict(
        project="Meridian",
        bearing="V1 Bifrost",
        risk_tier="low",
        prime_status=CockpitStatus.ONLINE,
        queue_policy=QueuePolicy.ON,
        lanes=[],
        progress_events=[],
        review_gate_count=0,
    )
    defaults.update(overrides)
    return defaults


class TestBuildSnapshot:
    def test_returns_snapshot_with_correct_fields(self) -> None:
        snap = build_snapshot(**_base_kwargs())
        assert snap.project == "Meridian"
        assert snap.bearing == "V1 Bifrost"
        assert snap.risk_tier == "low"
        assert snap.prime_status == CockpitStatus.ONLINE
        assert snap.queue_policy == QueuePolicy.ON
        assert snap.review_gate_count == 0

    def test_lanes_stored_as_tuple(self) -> None:
        snap = build_snapshot(**_base_kwargs(lanes=[_lane("b1")]))
        assert isinstance(snap.lanes, tuple)

    def test_events_stored_as_tuple(self) -> None:
        snap = build_snapshot(**_base_kwargs(progress_events=[_event()]))
        assert isinstance(snap.progress_events, tuple)

    def test_lanes_sorted_attention_first(self) -> None:
        l_idle = _lane("idle", LaneCockpitStatus.IDLE, attention=False)
        l_attn = _lane("attn", LaneCockpitStatus.OFFLINE, attention=True)
        snap = build_snapshot(**_base_kwargs(lanes=[l_idle, l_attn]))
        assert snap.lanes[0].lane_id == "attn"

    def test_lanes_sorted_by_status_within_attention_group(self) -> None:
        l_offline = _lane("off", LaneCockpitStatus.OFFLINE)
        l_running = _lane("run", LaneCockpitStatus.RUNNING)
        snap = build_snapshot(**_base_kwargs(lanes=[l_offline, l_running]))
        assert snap.lanes[0].lane_id == "run"

    def test_empty_lanes_accepted(self) -> None:
        snap = build_snapshot(**_base_kwargs(lanes=[]))
        assert snap.lanes == ()

    def test_empty_events_accepted(self) -> None:
        snap = build_snapshot(**_base_kwargs(progress_events=[]))
        assert snap.progress_events == ()

    def test_review_gate_count_zero_accepted(self) -> None:
        snap = build_snapshot(**_base_kwargs(review_gate_count=0))
        assert snap.review_gate_count == 0

    def test_review_gate_count_positive_accepted(self) -> None:
        snap = build_snapshot(**_base_kwargs(review_gate_count=3))
        assert snap.review_gate_count == 3

    def test_blank_project_raises(self) -> None:
        with pytest.raises(ValueError, match="project"):
            build_snapshot(**_base_kwargs(project=""))

    def test_whitespace_project_raises(self) -> None:
        with pytest.raises(ValueError, match="project"):
            build_snapshot(**_base_kwargs(project="   "))

    def test_blank_bearing_raises(self) -> None:
        with pytest.raises(ValueError, match="bearing"):
            build_snapshot(**_base_kwargs(bearing=""))

    def test_whitespace_bearing_raises(self) -> None:
        with pytest.raises(ValueError, match="bearing"):
            build_snapshot(**_base_kwargs(bearing="   "))

    def test_negative_review_gate_count_raises(self) -> None:
        with pytest.raises(ValueError, match="review_gate_count"):
            build_snapshot(**_base_kwargs(review_gate_count=-1))

    def test_snapshot_is_immutable(self) -> None:
        snap = build_snapshot(**_base_kwargs())
        with pytest.raises(Exception):
            snap.project = "tampered"  # type: ignore[misc]

    def test_original_lane_list_not_mutated(self) -> None:
        lanes = [_lane("b1"), _lane("b2")]
        original_ids = [l.lane_id for l in lanes]
        build_snapshot(**_base_kwargs(lanes=lanes))
        assert [l.lane_id for l in lanes] == original_ids


class TestDemoSnapshot:
    def test_returns_snapshot(self) -> None:
        from meridian_core.cockpit_state import PrimeCockpitSnapshot
        snap = demo_snapshot()
        assert isinstance(snap, PrimeCockpitSnapshot)

    def test_project_is_meridian(self) -> None:
        assert demo_snapshot().project == "Meridian"

    def test_bearing_is_v1_bifrost(self) -> None:
        assert demo_snapshot().bearing == "V1 Bifrost"

    def test_has_lanes(self) -> None:
        assert len(demo_snapshot().lanes) > 0

    def test_has_events(self) -> None:
        assert len(demo_snapshot().progress_events) > 0

    def test_attention_lane_sorted_first(self) -> None:
        snap = demo_snapshot()
        assert snap.lanes[0].attention is True

    def test_is_deterministic(self) -> None:
        assert demo_snapshot().project == demo_snapshot().project
        assert demo_snapshot().lanes == demo_snapshot().lanes
        assert demo_snapshot().progress_events == demo_snapshot().progress_events
