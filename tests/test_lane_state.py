"""Tests for the worker lane state domain model (meridian_core/lane_state.py)."""

from __future__ import annotations

import pytest

from meridian_core.lane_state import (
    LaneReviewState,
    LaneStatus,
    WorkerLaneState,
)


def _make_lane(
    lane_id: str = "build-1",
    build_name: str = "Build 1",
    status: LaneStatus = LaneStatus.IDLE,
    active_task: str = "",
    last_commit: str = "abc1234",
    review_state: LaneReviewState = LaneReviewState.NOT_REQUIRED,
    last_poll_at: str = "2026-05-31 04:00 CDT",
    notes: str = "",
) -> WorkerLaneState:
    return WorkerLaneState(
        lane_id=lane_id,
        build_name=build_name,
        status=status,
        active_task=active_task,
        last_commit=last_commit,
        review_state=review_state,
        last_poll_at=last_poll_at,
        notes=notes,
    )


class TestLaneStatusEnum:
    def test_all_values_present(self):
        names = {s.name for s in LaneStatus}
        assert names == {
            "IDLE", "POLLING", "RUNNING", "BLOCKED",
            "READY_FOR_REVIEW", "UNDER_REVIEW", "REPAIR_ROUTED",
            "STALE", "OFFLINE",
        }

    def test_values_are_strings(self):
        for s in LaneStatus:
            assert isinstance(s.value, str)

    def test_idle_value(self):
        assert LaneStatus.IDLE.value == "idle"

    def test_running_value(self):
        assert LaneStatus.RUNNING.value == "running"


class TestLaneReviewStateEnum:
    def test_all_values_present(self):
        names = {s.name for s in LaneReviewState}
        assert names == {
            "NOT_REQUIRED", "READY", "IN_REVIEW", "PASSED", "REPAIR_REQUIRED",
        }

    def test_values_are_strings(self):
        for s in LaneReviewState:
            assert isinstance(s.value, str)

    def test_passed_value(self):
        assert LaneReviewState.PASSED.value == "passed"


class TestWorkerLaneStateConstruction:
    def test_can_construct(self):
        lane = _make_lane()
        assert lane.lane_id == "build-1"

    def test_fields_stored(self):
        lane = _make_lane(
            lane_id="b1",
            build_name="Build 1",
            status=LaneStatus.RUNNING,
            active_task="some task",
            last_commit="def5678",
            review_state=LaneReviewState.READY,
            last_poll_at="2026-05-31 04:05 CDT",
            notes="test note",
        )
        assert lane.lane_id == "b1"
        assert lane.build_name == "Build 1"
        assert lane.status == LaneStatus.RUNNING
        assert lane.active_task == "some task"
        assert lane.last_commit == "def5678"
        assert lane.review_state == LaneReviewState.READY
        assert lane.last_poll_at == "2026-05-31 04:05 CDT"
        assert lane.notes == "test note"

    def test_is_frozen(self):
        lane = _make_lane()
        with pytest.raises((AttributeError, TypeError)):
            lane.status = LaneStatus.RUNNING  # type: ignore[misc]


class TestMarkRunning:
    def test_status_becomes_running(self):
        lane = _make_lane()
        updated = lane.mark_running()
        assert updated.status == LaneStatus.RUNNING

    def test_original_unchanged(self):
        lane = _make_lane()
        lane.mark_running()
        assert lane.status == LaneStatus.IDLE

    def test_returns_new_object(self):
        lane = _make_lane()
        updated = lane.mark_running()
        assert updated is not lane

    def test_active_task_updated_when_provided(self):
        lane = _make_lane()
        updated = lane.mark_running(active_task="new task")
        assert updated.active_task == "new task"

    def test_active_task_preserved_when_not_provided(self):
        lane = _make_lane(active_task="existing task")
        updated = lane.mark_running()
        assert updated.active_task == "existing task"

    def test_last_poll_at_updated_when_provided(self):
        lane = _make_lane()
        updated = lane.mark_running(last_poll_at="2026-05-31 05:00 CDT")
        assert updated.last_poll_at == "2026-05-31 05:00 CDT"

    def test_other_fields_preserved(self):
        lane = _make_lane(last_commit="abc1234", build_name="Build 1")
        updated = lane.mark_running()
        assert updated.last_commit == "abc1234"
        assert updated.build_name == "Build 1"
        assert updated.lane_id == lane.lane_id


class TestMarkBlocked:
    def test_status_becomes_blocked(self):
        lane = _make_lane(status=LaneStatus.RUNNING)
        updated = lane.mark_blocked()
        assert updated.status == LaneStatus.BLOCKED

    def test_original_unchanged(self):
        lane = _make_lane(status=LaneStatus.RUNNING)
        lane.mark_blocked()
        assert lane.status == LaneStatus.RUNNING

    def test_returns_new_object(self):
        lane = _make_lane()
        updated = lane.mark_blocked()
        assert updated is not lane

    def test_notes_updated_when_provided(self):
        lane = _make_lane()
        updated = lane.mark_blocked(notes="waiting on dependency")
        assert updated.notes == "waiting on dependency"

    def test_other_fields_preserved(self):
        lane = _make_lane(last_commit="abc1234", active_task="task A")
        updated = lane.mark_blocked()
        assert updated.last_commit == "abc1234"
        assert updated.active_task == "task A"


class TestMarkReadyForReview:
    def test_status_becomes_ready_for_review(self):
        lane = _make_lane(status=LaneStatus.RUNNING)
        updated = lane.mark_ready_for_review()
        assert updated.status == LaneStatus.READY_FOR_REVIEW

    def test_review_state_becomes_ready(self):
        lane = _make_lane()
        updated = lane.mark_ready_for_review()
        assert updated.review_state == LaneReviewState.READY

    def test_original_unchanged(self):
        lane = _make_lane()
        lane.mark_ready_for_review()
        assert lane.status == LaneStatus.IDLE
        assert lane.review_state == LaneReviewState.NOT_REQUIRED

    def test_last_commit_updated_when_provided(self):
        lane = _make_lane(last_commit="old123")
        updated = lane.mark_ready_for_review(last_commit="new456")
        assert updated.last_commit == "new456"

    def test_last_commit_preserved_when_not_provided(self):
        lane = _make_lane(last_commit="keep999")
        updated = lane.mark_ready_for_review()
        assert updated.last_commit == "keep999"

    def test_other_fields_preserved(self):
        lane = _make_lane(build_name="Build 2", active_task="task X")
        updated = lane.mark_ready_for_review()
        assert updated.build_name == "Build 2"
        assert updated.active_task == "task X"


class TestMarkReviewPassed:
    def test_status_becomes_idle(self):
        lane = _make_lane(
            status=LaneStatus.UNDER_REVIEW,
            review_state=LaneReviewState.IN_REVIEW,
        )
        updated = lane.mark_review_passed()
        assert updated.status == LaneStatus.IDLE

    def test_review_state_becomes_passed(self):
        lane = _make_lane(review_state=LaneReviewState.IN_REVIEW)
        updated = lane.mark_review_passed()
        assert updated.review_state == LaneReviewState.PASSED

    def test_active_task_cleared(self):
        lane = _make_lane(active_task="completed task")
        updated = lane.mark_review_passed()
        assert updated.active_task == ""

    def test_original_unchanged(self):
        lane = _make_lane(
            status=LaneStatus.READY_FOR_REVIEW,
            active_task="task",
        )
        lane.mark_review_passed()
        assert lane.status == LaneStatus.READY_FOR_REVIEW
        assert lane.active_task == "task"

    def test_last_commit_preserved(self):
        lane = _make_lane(last_commit="fd35a81")
        updated = lane.mark_review_passed()
        assert updated.last_commit == "fd35a81"

    def test_notes_updated_when_provided(self):
        lane = _make_lane()
        updated = lane.mark_review_passed(notes="reviewed by Codex")
        assert updated.notes == "reviewed by Codex"

    def test_other_fields_preserved(self):
        lane = _make_lane(build_name="Build 1", lane_id="b1", last_poll_at="ts")
        updated = lane.mark_review_passed()
        assert updated.build_name == "Build 1"
        assert updated.lane_id == "b1"
        assert updated.last_poll_at == "ts"


class TestTransitionChaining:
    def test_idle_to_running_to_ready_to_passed(self):
        lane = _make_lane()
        lane = lane.mark_running(active_task="build relay_dispatch")
        assert lane.status == LaneStatus.RUNNING
        lane = lane.mark_ready_for_review(last_commit="fd35a81")
        assert lane.status == LaneStatus.READY_FOR_REVIEW
        assert lane.review_state == LaneReviewState.READY
        lane = lane.mark_review_passed()
        assert lane.status == LaneStatus.IDLE
        assert lane.review_state == LaneReviewState.PASSED
        assert lane.active_task == ""

    def test_running_to_blocked_preserves_task(self):
        lane = _make_lane(status=LaneStatus.RUNNING, active_task="important task")
        blocked = lane.mark_blocked(notes="dep unavailable")
        assert blocked.status == LaneStatus.BLOCKED
        assert blocked.active_task == "important task"
