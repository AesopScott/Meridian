"""Backend routine authority for Meridian V2.

This module owns routine definitions, enable/disable state, and non-executable
run plans. It does not schedule automation, execute workflows, mutate queues,
call providers, or wire UI controls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from .workflow_dispatch import (
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowResultSummary,
)


SHORT_TEXT_MAX = 160
SUMMARY_MAX = 420
SAFE_REF_SCHEMES = (
    "goal://",
    "proof://",
    "routine://",
    "task://",
    "workflow://",
)
UNSAFE_TERMS = (
    "raw prompt",
    "serialized prompt",
    "provider response",
    "worker chat",
    "transcript",
    "api key",
    "secret",
    "credential",
    "token=",
)


class RoutineValidationError(ValueError):
    """Raised when routine authority input is unsafe or inconsistent."""


class RoutineState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class RoutineTriggerKind(Enum):
    MANUAL = "manual"
    CADENCE = "cadence"
    EVENT = "event"


class RoutineRunPlanStatus(Enum):
    PLANNED = "planned"
    BLOCKED_DISABLED = "blocked_disabled"


class RoutineReviewSource(Enum):
    RESULT_SUMMARY = "result_summary"
    ERROR_SUMMARY = "error_summary"


class RoutineReviewDisposition(Enum):
    ACCEPTED = "accepted"
    ROUTE_REPAIR = "route_repair"
    RETRY_AFTER_REPAIR = "retry_after_repair"
    ESCALATE_HUMAN_GATE = "escalate_human_gate"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RoutineValidationError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _looks_like_path(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if re.search(r"\b[\w.-]+[\\/][\w.-]+", value):
        return True
    return False


def _looks_like_uri_path_payload(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if "\\" in value:
        return True
    segments = [segment for segment in value.split("/") if segment]
    if any(segment in (".", "..") for segment in segments):
        return True
    if any(re.search(r"\.[A-Za-z0-9]{1,8}$", segment) for segment in segments):
        return True
    return False


def _safe_text(value: str, field: str, max_length: int = SHORT_TEXT_MAX) -> str:
    text = str(value).strip()
    if not text:
        raise RoutineValidationError(f"{field} must not be empty")
    if len(text) > max_length:
        raise RoutineValidationError(f"{field} is too long")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise RoutineValidationError(f"{field} contains unsafe content")
    if _looks_like_path(text):
        raise RoutineValidationError(f"{field} must not contain local paths")
    return text


def _safe_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise RoutineValidationError(f"{field} must not be empty")
    if len(ref) > SHORT_TEXT_MAX:
        raise RoutineValidationError(f"{field} is too long")
    if not ref.startswith(SAFE_REF_SCHEMES):
        ref = _safe_text(ref, field)
        if "://" in ref:
            raise RoutineValidationError(f"{field} uses an unsupported URI scheme")
        return ref
    lowered = ref.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise RoutineValidationError(f"{field} contains unsafe content")
    payload = ref.split("://", 1)[1]
    if not payload or _looks_like_uri_path_payload(payload):
        raise RoutineValidationError(f"{field} must not contain local paths")
    return ref


def _safe_refs(values: Iterable[str], field: str) -> tuple[str, ...]:
    refs = tuple(_safe_ref(value, field) for value in values)
    if len(set(refs)) != len(refs):
        raise RoutineValidationError(f"{field} must not contain duplicates")
    return refs


@dataclass(frozen=True)
class RoutineTrigger:
    trigger_id: str
    kind: RoutineTriggerKind
    label: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.trigger_id, "RoutineTrigger.trigger_id")
        if not isinstance(self.kind, RoutineTriggerKind):
            raise RoutineValidationError("kind must be RoutineTriggerKind")
        _safe_text(self.label, "RoutineTrigger.label")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineTrigger.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "trigger_id": self.trigger_id,
            "kind": self.kind.value,
            "label": self.label,
            "evidence_refs": self.evidence_refs,
        }


@dataclass(frozen=True)
class RoutineDefinition:
    routine_id: str
    name: str
    owner: str
    scope_refs: tuple[str, ...]
    triggers: tuple[RoutineTrigger, ...]
    created_by: str
    created_at: datetime
    state: RoutineState = RoutineState.DISABLED
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.routine_id, "RoutineDefinition.routine_id")
        _safe_text(self.name, "RoutineDefinition.name")
        _safe_text(self.owner, "RoutineDefinition.owner")
        object.__setattr__(self, "scope_refs", _safe_refs(self.scope_refs, "RoutineDefinition.scope_refs"))
        if not self.scope_refs:
            raise RoutineValidationError("RoutineDefinition.scope_refs must not be empty")
        object.__setattr__(self, "triggers", tuple(self.triggers))
        if not self.triggers:
            raise RoutineValidationError("RoutineDefinition.triggers must not be empty")
        trigger_ids: set[str] = set()
        for trigger in self.triggers:
            if not isinstance(trigger, RoutineTrigger):
                raise RoutineValidationError("triggers must be RoutineTrigger")
            if trigger.trigger_id in trigger_ids:
                raise RoutineValidationError("RoutineDefinition.triggers trigger_id values must be unique")
            trigger_ids.add(trigger.trigger_id)
        _safe_text(self.created_by, "RoutineDefinition.created_by")
        _as_utc(self.created_at)
        if not isinstance(self.state, RoutineState):
            raise RoutineValidationError("state must be RoutineState")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineDefinition.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "routine_id": self.routine_id,
            "name": self.name,
            "owner": self.owner,
            "scope_refs": self.scope_refs,
            "triggers": tuple(trigger.to_dict() for trigger in self.triggers),
            "created_by": self.created_by,
            "created_at": _as_utc(self.created_at).isoformat(),
            "state": self.state.value,
            "evidence_refs": self.evidence_refs,
            "scheduler_mutation_authorized": False,
            "execution_authorized": False,
        }


def create_routine(
    *,
    routine_id: str,
    name: str,
    owner: str,
    scope_refs: tuple[str, ...],
    triggers: tuple[RoutineTrigger, ...],
    created_by: str,
    created_at: datetime,
    enabled: bool = False,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineDefinition:
    return RoutineDefinition(
        routine_id=routine_id,
        name=name,
        owner=owner,
        scope_refs=scope_refs,
        triggers=triggers,
        created_by=created_by,
        created_at=created_at,
        state=RoutineState.ENABLED if enabled else RoutineState.DISABLED,
        evidence_refs=evidence_refs,
    )


def set_routine_enabled(
    routine: RoutineDefinition,
    *,
    enabled: bool,
    actor: str,
    timestamp: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineDefinition:
    if not isinstance(routine, RoutineDefinition):
        raise RoutineValidationError("routine must be RoutineDefinition")
    _safe_text(actor, "actor")
    _as_utc(timestamp)
    refs = _safe_refs(evidence_refs, "set_routine_enabled.evidence_refs")
    return replace(
        routine,
        state=RoutineState.ENABLED if enabled else RoutineState.DISABLED,
        evidence_refs=routine.evidence_refs + refs,
    )


@dataclass(frozen=True)
class RoutineRunPlan:
    plan_id: str
    routine_id: str
    trigger_id: str
    requested_by: str
    requested_at: datetime
    status: RoutineRunPlanStatus
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.plan_id, "RoutineRunPlan.plan_id")
        _safe_text(self.routine_id, "RoutineRunPlan.routine_id")
        _safe_text(self.trigger_id, "RoutineRunPlan.trigger_id")
        _safe_text(self.requested_by, "RoutineRunPlan.requested_by")
        _as_utc(self.requested_at)
        if not isinstance(self.status, RoutineRunPlanStatus):
            raise RoutineValidationError("status must be RoutineRunPlanStatus")
        _safe_text(self.reason, "RoutineRunPlan.reason", SUMMARY_MAX)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "RoutineRunPlan.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "routine_id": self.routine_id,
            "trigger_id": self.trigger_id,
            "requested_by": self.requested_by,
            "requested_at": _as_utc(self.requested_at).isoformat(),
            "status": self.status.value,
            "reason": self.reason,
            "evidence_refs": self.evidence_refs,
            "execution_authorized": False,
            "scheduler_mutation_authorized": False,
        }


def plan_routine_run(
    routine: RoutineDefinition,
    *,
    plan_id: str,
    trigger_id: str,
    requested_by: str,
    requested_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> RoutineRunPlan:
    if not isinstance(routine, RoutineDefinition):
        raise RoutineValidationError("routine must be RoutineDefinition")
    if trigger_id not in {trigger.trigger_id for trigger in routine.triggers}:
        raise RoutineValidationError("trigger_id is not registered on routine")
    if routine.state is RoutineState.DISABLED:
        return RoutineRunPlan(
            plan_id=plan_id,
            routine_id=routine.routine_id,
            trigger_id=trigger_id,
            requested_by=requested_by,
            requested_at=requested_at,
            status=RoutineRunPlanStatus.BLOCKED_DISABLED,
            reason="Routine is disabled; no execution is authorized.",
            evidence_refs=evidence_refs,
        )
    return RoutineRunPlan(
        plan_id=plan_id,
        routine_id=routine.routine_id,
        trigger_id=trigger_id,
        requested_by=requested_by,
        requested_at=requested_at,
        status=RoutineRunPlanStatus.PLANNED,
        reason="Routine run plan is display-safe and non-executable.",
        evidence_refs=evidence_refs,
    )


@dataclass(frozen=True)
class PrimeRoutineReview:
    review_id: str
    routine_id: str
    run_ref: str
    reviewed_by: str
    reviewed_at: datetime
    source: RoutineReviewSource
    disposition: RoutineReviewDisposition
    summary: str
    proof_trail: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    gate_required: bool = False
    escalation_required: bool = False

    def __post_init__(self) -> None:
        _safe_text(self.review_id, "PrimeRoutineReview.review_id")
        _safe_text(self.routine_id, "PrimeRoutineReview.routine_id")
        _safe_text(self.run_ref, "PrimeRoutineReview.run_ref")
        _safe_text(self.reviewed_by, "PrimeRoutineReview.reviewed_by")
        _as_utc(self.reviewed_at)
        if not isinstance(self.source, RoutineReviewSource):
            raise RoutineValidationError("source must be RoutineReviewSource")
        if not isinstance(self.disposition, RoutineReviewDisposition):
            raise RoutineValidationError("disposition must be RoutineReviewDisposition")
        _safe_text(self.summary, "PrimeRoutineReview.summary", SUMMARY_MAX)
        object.__setattr__(self, "proof_trail", _safe_refs(self.proof_trail, "PrimeRoutineReview.proof_trail"))
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "PrimeRoutineReview.evidence_refs"))
        if not isinstance(self.gate_required, bool):
            raise RoutineValidationError("gate_required must be bool")
        if not isinstance(self.escalation_required, bool):
            raise RoutineValidationError("escalation_required must be bool")

    def to_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "routine_id": self.routine_id,
            "run_ref": self.run_ref,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": _as_utc(self.reviewed_at).isoformat(),
            "source": self.source.value,
            "disposition": self.disposition.value,
            "summary": self.summary,
            "proof_trail": self.proof_trail,
            "evidence_refs": self.evidence_refs,
            "gate_required": self.gate_required,
            "escalation_required": self.escalation_required,
            "accept_authorized": False,
            "reroute_authorized": False,
            "retry_authorized": False,
            "escalate_authorized": False,
            "scheduler_mutation_authorized": False,
            "execution_authorized": False,
            "raw_result_body_visible": False,
            "raw_worker_history_visible": False,
        }


def review_routine_result(
    routine: RoutineDefinition,
    plan: RoutineRunPlan,
    result: WorkflowResultSummary | WorkflowErrorSummary,
    *,
    review_id: str,
    reviewed_by: str,
    reviewed_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> PrimeRoutineReview:
    if not isinstance(routine, RoutineDefinition):
        raise RoutineValidationError("routine must be RoutineDefinition")
    if not isinstance(plan, RoutineRunPlan):
        raise RoutineValidationError("plan must be RoutineRunPlan")
    if plan.routine_id != routine.routine_id:
        raise RoutineValidationError("plan.routine_id must match routine.routine_id")
    if plan.status is RoutineRunPlanStatus.BLOCKED_DISABLED:
        raise RoutineValidationError("blocked routine plans cannot produce routine review")
    if not isinstance(result, (WorkflowResultSummary, WorkflowErrorSummary)):
        raise RoutineValidationError("result must be WorkflowResultSummary or WorkflowErrorSummary")
    if result.work_order_id != plan.plan_id:
        raise RoutineValidationError("result.work_order_id must match plan.plan_id")
    if (
        isinstance(result, WorkflowErrorSummary)
        and result.failure_kind is WorkflowFailureKind.RESTEER_REQUESTED
        and (
            result.resteer_request is None
            or result.resteer_request.original_work_order_id != result.work_order_id
        )
    ):
        raise RoutineValidationError("resteer_request.original_work_order_id must match result.work_order_id")
    _safe_text(review_id, "review_id")
    _safe_text(reviewed_by, "reviewed_by")
    _as_utc(reviewed_at)
    refs = _safe_refs(evidence_refs, "review_routine_result.evidence_refs")

    if isinstance(result, WorkflowResultSummary):
        disposition = (
            RoutineReviewDisposition.ESCALATE_HUMAN_GATE
            if result.requires_human_gate
            else RoutineReviewDisposition.ACCEPTED
        )
        return PrimeRoutineReview(
            review_id=review_id,
            routine_id=routine.routine_id,
            run_ref=result.work_order_id,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            source=RoutineReviewSource.RESULT_SUMMARY,
            disposition=disposition,
            summary=result.summary,
            proof_trail=result.proof_trail,
            evidence_refs=plan.evidence_refs + refs,
            gate_required=result.requires_human_gate,
            escalation_required=result.requires_human_gate,
        )

    if isinstance(result, WorkflowErrorSummary):
        if result.failure_kind is WorkflowFailureKind.RESTEER_REQUESTED:
            disposition = RoutineReviewDisposition.ROUTE_REPAIR
        elif result.failure_kind is WorkflowFailureKind.INTERNAL_ERROR:
            disposition = RoutineReviewDisposition.RETRY_AFTER_REPAIR
        else:
            disposition = RoutineReviewDisposition.ESCALATE_HUMAN_GATE
        return PrimeRoutineReview(
            review_id=review_id,
            routine_id=routine.routine_id,
            run_ref=result.work_order_id,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            source=RoutineReviewSource.ERROR_SUMMARY,
            disposition=disposition,
            summary=result.summary,
            proof_trail=result.proof_trail,
            evidence_refs=plan.evidence_refs + refs,
            gate_required=disposition is RoutineReviewDisposition.ESCALATE_HUMAN_GATE,
            escalation_required=disposition is RoutineReviewDisposition.ESCALATE_HUMAN_GATE,
        )

    raise RoutineValidationError("result must be WorkflowResultSummary or WorkflowErrorSummary")
