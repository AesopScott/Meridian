"""
Worker lane state domain model for Prime orchestration.

Provides immutable state objects and pure transition helpers Prime needs
to coordinate build and review queues. All transitions return new objects.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class LaneStatus(Enum):
    IDLE = "idle"
    POLLING = "polling"
    RUNNING = "running"
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    REPAIR_ROUTED = "repair_routed"
    STALE = "stale"
    OFFLINE = "offline"


class LaneReviewState(Enum):
    NOT_REQUIRED = "not_required"
    READY = "ready"
    IN_REVIEW = "in_review"
    PASSED = "passed"
    REPAIR_REQUIRED = "repair_required"


@dataclass(frozen=True)
class WorkerLaneState:
    """
    Immutable snapshot of a worker lane's current state.

    All transition helpers return new instances; the original is unchanged.
    Timestamps are plain strings — no datetime parsing dependency.
    """

    lane_id: str
    build_name: str
    status: LaneStatus
    active_task: str
    last_commit: str
    review_state: LaneReviewState
    last_poll_at: str
    notes: str

    def mark_running(
        self,
        active_task: str = "",
        last_poll_at: str = "",
        notes: str = "",
    ) -> WorkerLaneState:
        """Transition to RUNNING, optionally updating active_task, last_poll_at, notes."""
        return replace(
            self,
            status=LaneStatus.RUNNING,
            active_task=active_task if active_task else self.active_task,
            last_poll_at=last_poll_at if last_poll_at else self.last_poll_at,
            notes=notes if notes else self.notes,
        )

    def mark_blocked(self, notes: str = "") -> WorkerLaneState:
        """Transition to BLOCKED, optionally updating notes."""
        return replace(
            self,
            status=LaneStatus.BLOCKED,
            notes=notes if notes else self.notes,
        )

    def mark_ready_for_review(
        self,
        last_commit: str = "",
        notes: str = "",
    ) -> WorkerLaneState:
        """
        Transition to READY_FOR_REVIEW and set review_state to READY.
        Optionally updates last_commit and notes.
        """
        return replace(
            self,
            status=LaneStatus.READY_FOR_REVIEW,
            review_state=LaneReviewState.READY,
            last_commit=last_commit if last_commit else self.last_commit,
            notes=notes if notes else self.notes,
        )

    def mark_review_passed(self, notes: str = "") -> WorkerLaneState:
        """
        Transition to IDLE and set review_state to PASSED.
        Clears active_task; lane is ready for new work.
        """
        return replace(
            self,
            status=LaneStatus.IDLE,
            review_state=LaneReviewState.PASSED,
            active_task="",
            notes=notes if notes else self.notes,
        )
