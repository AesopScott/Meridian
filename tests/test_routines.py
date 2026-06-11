"""Tests for backend routine authority."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meridian_core.routines import (
    PrimeRoutineReview,
    RoutineReviewDisposition,
    RoutineReviewSource,
    RoutineDefinition,
    RoutineRunPlanStatus,
    RoutineState,
    RoutineTrigger,
    RoutineTriggerKind,
    RoutineValidationError,
    create_routine,
    plan_routine_run,
    review_routine_result,
    set_routine_enabled,
)
from meridian_core.workflow_dispatch import (
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowHarness,
    WorkflowResteerChanges,
    WorkflowResteerRequest,
    WorkflowResultSummary,
)


NOW = datetime(2026, 6, 10, 22, 45, tzinfo=timezone.utc)


def make_trigger() -> RoutineTrigger:
    return RoutineTrigger(
        trigger_id="routine-trigger-manual",
        kind=RoutineTriggerKind.MANUAL,
        label="Manual review checkpoint",
        evidence_refs=("proof://routine/trigger",),
    )


def make_routine(enabled: bool = False) -> RoutineDefinition:
    return create_routine(
        routine_id="routine-review-checkpoint",
        name="Review checkpoint",
        owner="prime",
        scope_refs=("workflow://review/checkpoint",),
        triggers=(make_trigger(),),
        created_by="prime",
        created_at=NOW,
        enabled=enabled,
        evidence_refs=("proof://routine/create",),
    )


def test_create_routine_records_definition_without_execution_authority():
    routine = make_routine()
    payload = routine.to_dict()

    assert routine.state is RoutineState.DISABLED
    assert payload["routine_id"] == "routine-review-checkpoint"
    assert payload["scheduler_mutation_authorized"] is False
    assert payload["execution_authorized"] is False
    assert payload["triggers"][0]["kind"] == "manual"


def test_set_routine_enabled_toggles_state_with_safe_evidence():
    routine = make_routine()
    enabled = set_routine_enabled(
        routine,
        enabled=True,
        actor="prime",
        timestamp=NOW,
        evidence_refs=("proof://routine/enabled",),
    )
    disabled = set_routine_enabled(
        enabled,
        enabled=False,
        actor="prime",
        timestamp=NOW,
        evidence_refs=("proof://routine/disabled",),
    )

    assert enabled.state is RoutineState.ENABLED
    assert enabled.evidence_refs[-1] == "proof://routine/enabled"
    assert disabled.state is RoutineState.DISABLED
    assert disabled.evidence_refs[-1] == "proof://routine/disabled"


def test_plan_routine_run_blocks_disabled_routine():
    plan = plan_routine_run(
        make_routine(enabled=False),
        plan_id="routine-plan-1",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://routine/run-request",),
    )
    payload = plan.to_dict()

    assert plan.status is RoutineRunPlanStatus.BLOCKED_DISABLED
    assert payload["execution_authorized"] is False
    assert payload["scheduler_mutation_authorized"] is False


def test_plan_routine_run_for_enabled_routine_is_non_executable_plan():
    plan = plan_routine_run(
        make_routine(enabled=True),
        plan_id="routine-plan-2",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://routine/run-request",),
    )

    assert plan.status is RoutineRunPlanStatus.PLANNED
    assert plan.to_dict()["execution_authorized"] is False


def test_plan_routine_run_requires_registered_trigger():
    with pytest.raises(RoutineValidationError, match="trigger_id"):
        plan_routine_run(
            make_routine(enabled=True),
            plan_id="routine-plan-3",
            trigger_id="routine-trigger-other",
            requested_by="prime",
            requested_at=NOW,
        )


def make_enabled_plan():
    return plan_routine_run(
        make_routine(enabled=True),
        plan_id="workflow.routine.001",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
        evidence_refs=("proof://routine/run-request",),
    )


def make_result(*, requires_human_gate: bool = False) -> WorkflowResultSummary:
    return WorkflowResultSummary(
        work_order_id="workflow.routine.001",
        harness=WorkflowHarness.RELAY,
        result_shape="RoutineResult",
        summary="Routine completed and produced a bounded summary.",
        proof_trail=("proof.routine.result",),
        requires_human_gate=requires_human_gate,
    )


def test_review_routine_result_accepts_success_without_execution_authority():
    routine = make_routine(enabled=True)
    plan = make_enabled_plan()
    review = review_routine_result(
        routine,
        plan,
        make_result(),
        review_id="routine-review-1",
        reviewed_by="prime",
        reviewed_at=NOW,
        evidence_refs=("proof://routine/review",),
    )
    payload = review.to_dict()

    assert isinstance(review, PrimeRoutineReview)
    assert review.source is RoutineReviewSource.RESULT_SUMMARY
    assert review.disposition is RoutineReviewDisposition.ACCEPTED
    assert payload["accept_authorized"] is False
    assert payload["reroute_authorized"] is False
    assert payload["retry_authorized"] is False
    assert payload["escalate_authorized"] is False
    assert payload["execution_authorized"] is False
    assert payload["raw_result_body_visible"] is False
    assert "Routine completed" in payload["summary"]


def test_review_routine_result_escalates_human_gate_without_authorizing_action():
    review = review_routine_result(
        make_routine(enabled=True),
        make_enabled_plan(),
        make_result(requires_human_gate=True),
        review_id="routine-review-gate",
        reviewed_by="prime",
        reviewed_at=NOW,
    )

    assert review.disposition is RoutineReviewDisposition.ESCALATE_HUMAN_GATE
    assert review.gate_required is True
    assert review.escalation_required is True
    assert review.to_dict()["escalate_authorized"] is False


def test_review_routine_error_routes_repair_without_authority():
    error = WorkflowErrorSummary(
        work_order_id="workflow.routine.001",
        harness=WorkflowHarness.RELAY,
        failure_kind=WorkflowFailureKind.RESTEER_REQUESTED,
        summary="Routine output needs a bounded repair route.",
        proof_trail=("proof.routine.error",),
        resteer_request=WorkflowResteerRequest(
            original_work_order_id="workflow.routine.001",
            reason="narrow the routine review scope",
            suggested_changes=WorkflowResteerChanges(allowed_paths=("docs/",)),
        ),
    )
    review = review_routine_result(
        make_routine(enabled=True),
        make_enabled_plan(),
        error,
        review_id="routine-review-route-repair",
        reviewed_by="prime",
        reviewed_at=NOW,
    )

    assert review.source is RoutineReviewSource.ERROR_SUMMARY
    assert review.disposition is RoutineReviewDisposition.ROUTE_REPAIR
    assert review.to_dict()["reroute_authorized"] is False
    assert review.to_dict()["scheduler_mutation_authorized"] is False


def test_review_routine_proof_error_escalates_without_authority():
    error = WorkflowErrorSummary(
        work_order_id="workflow.routine.001",
        harness=WorkflowHarness.RELAY,
        failure_kind=WorkflowFailureKind.PROOF_UNAVAILABLE,
        summary="Routine result is missing required proof.",
        proof_trail=("proof.routine.error",),
    )
    review = review_routine_result(
        make_routine(enabled=True),
        make_enabled_plan(),
        error,
        review_id="routine-review-error",
        reviewed_by="prime",
        reviewed_at=NOW,
    )

    assert review.source is RoutineReviewSource.ERROR_SUMMARY
    assert review.disposition is RoutineReviewDisposition.ESCALATE_HUMAN_GATE
    assert review.to_dict()["retry_authorized"] is False
    assert review.to_dict()["scheduler_mutation_authorized"] is False


def test_review_routine_internal_error_recommends_retry_after_repair_only():
    error = WorkflowErrorSummary(
        work_order_id="workflow.routine.001",
        harness=WorkflowHarness.RELAY,
        failure_kind=WorkflowFailureKind.INTERNAL_ERROR,
        summary="Routine execution failed in a bounded worker.",
        proof_trail=("proof.routine.error",),
    )
    review = review_routine_result(
        make_routine(enabled=True),
        make_enabled_plan(),
        error,
        review_id="routine-review-retry",
        reviewed_by="prime",
        reviewed_at=NOW,
    )

    assert review.disposition is RoutineReviewDisposition.RETRY_AFTER_REPAIR
    assert review.to_dict()["retry_authorized"] is False


def test_review_routine_rejects_blocked_disabled_plan():
    routine = make_routine(enabled=False)
    plan = plan_routine_run(
        routine,
        plan_id="routine-plan-disabled-review",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
    )

    with pytest.raises(RoutineValidationError, match="blocked routine"):
        review_routine_result(
            routine,
            plan,
            make_result(),
            review_id="routine-review-disabled",
            reviewed_by="prime",
            reviewed_at=NOW,
        )


def test_review_routine_rejects_cross_routine_plan():
    routine = make_routine(enabled=True)
    other_plan = plan_routine_run(
        create_routine(
            routine_id="routine-other",
            name="Other routine",
            owner="prime",
            scope_refs=("workflow://review/other",),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
            enabled=True,
        ),
        plan_id="routine-plan-other",
        trigger_id="routine-trigger-manual",
        requested_by="prime",
        requested_at=NOW,
    )

    with pytest.raises(RoutineValidationError, match="routine_id"):
        review_routine_result(
            routine,
            other_plan,
            make_result(),
            review_id="routine-review-cross",
            reviewed_by="prime",
            reviewed_at=NOW,
        )


def test_review_routine_rejects_result_for_different_work_order():
    result = WorkflowResultSummary(
        work_order_id="workflow.routine.other",
        harness=WorkflowHarness.RELAY,
        result_shape="RoutineResult",
        summary="Routine completed elsewhere.",
        proof_trail=("proof.routine.result",),
    )

    with pytest.raises(RoutineValidationError, match="work_order_id"):
        review_routine_result(
            make_routine(enabled=True),
            make_enabled_plan(),
            result,
            review_id="routine-review-drift",
            reviewed_by="prime",
            reviewed_at=NOW,
        )


def test_review_routine_rejects_resteer_original_work_order_drift():
    error = WorkflowErrorSummary(
        work_order_id="workflow.routine.001",
        harness=WorkflowHarness.RELAY,
        failure_kind=WorkflowFailureKind.RESTEER_REQUESTED,
        summary="Routine output needs a bounded repair route.",
        proof_trail=("proof.routine.error",),
        resteer_request=WorkflowResteerRequest(
            original_work_order_id="workflow.routine.other",
            reason="narrow the routine review scope",
            suggested_changes=WorkflowResteerChanges(allowed_paths=("docs/",)),
        ),
    )

    with pytest.raises(RoutineValidationError, match="original_work_order_id"):
        review_routine_result(
            make_routine(enabled=True),
            make_enabled_plan(),
            error,
            review_id="routine-review-resteer-drift",
            reviewed_by="prime",
            reviewed_at=NOW,
        )


def test_create_routine_rejects_duplicate_trigger_ids():
    duplicate = RoutineTrigger(
        trigger_id="routine-trigger-manual",
        kind=RoutineTriggerKind.CADENCE,
        label="Scheduled review checkpoint",
        evidence_refs=("proof://routine/trigger/scheduled",),
    )

    with pytest.raises(RoutineValidationError, match="trigger_id values must be unique"):
        create_routine(
            routine_id="routine-duplicate-triggers",
            name="Duplicate trigger ids",
            owner="prime",
            scope_refs=("workflow://review/checkpoint",),
            triggers=(make_trigger(), duplicate),
            created_by="prime",
            created_at=NOW,
        )


def test_create_routine_requires_scope_and_trigger():
    with pytest.raises(RoutineValidationError, match="scope_refs"):
        create_routine(
            routine_id="routine-no-scope",
            name="No scope",
            owner="prime",
            scope_refs=(),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )

    with pytest.raises(RoutineValidationError, match="triggers"):
        create_routine(
            routine_id="routine-no-trigger",
            name="No trigger",
            owner="prime",
            scope_refs=("workflow://review/checkpoint",),
            triggers=(),
            created_by="prime",
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "raw prompt contents",
        "provider response body",
        "worker chat transcript",
        "token=abc123",
        r"C:\Users\scott\routine.json",
        "../private/routine.json",
        "docs/routine.md",
    ),
)
def test_routines_reject_unsafe_text_and_refs(unsafe_value):
    with pytest.raises(RoutineValidationError):
        RoutineTrigger(
            trigger_id="routine-trigger-unsafe",
            kind=RoutineTriggerKind.MANUAL,
            label=unsafe_value,
        )

    with pytest.raises(RoutineValidationError):
        create_routine(
            routine_id="routine-unsafe",
            name="Unsafe",
            owner="prime",
            scope_refs=(unsafe_value,),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "routine://../private/routine.json",
        "workflow://./runtime/queue.json",
        r"proof://C:\Users\scott\routine.txt",
    ),
)
def test_routine_safe_uri_refs_reject_path_payloads(unsafe_ref):
    with pytest.raises(RoutineValidationError, match="local paths"):
        create_routine(
            routine_id="routine-unsafe-ref",
            name="Unsafe ref",
            owner="prime",
            scope_refs=(unsafe_ref,),
            triggers=(make_trigger(),),
            created_by="prime",
            created_at=NOW,
        )
