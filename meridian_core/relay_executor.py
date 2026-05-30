"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .relay import ModelRole
from .relay_dispatch import RelayDispatchPlan


class ModelCallFn(Protocol):
    """Callable boundary: receives only the lane payload string, returns text."""

    def __call__(self, payload: str) -> str: ...


@dataclass(frozen=True)
class RelayExecutionResult:
    """Successful output for one lane."""

    role: ModelRole
    preferred_model: str
    output: str


@dataclass(frozen=True)
class RelayExecutionError:
    """Captured exception for one lane."""

    role: ModelRole
    preferred_model: str
    error: str


@dataclass(frozen=True)
class RelayExecutionSummary:
    """Immutable collection of per-lane results and errors from one plan execution."""

    results: tuple[RelayExecutionResult, ...]
    errors: tuple[RelayExecutionError, ...]


def execute_relay_dispatch_plan(
    plan: RelayDispatchPlan,
    model_call: ModelCallFn,
) -> RelayExecutionSummary:
    """
    Execute every lane in *plan* by calling model_call(lane.payload).

    Only the lane payload is forwarded to model_call — no role, model name,
    or metadata. Exceptions are caught per-lane and converted to
    RelayExecutionError entries; successful outputs become RelayExecutionResult
    entries. Lane order matches plan.lanes.
    """
    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []

    for lane in plan.lanes:
        try:
            output = model_call(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                RelayExecutionError(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    error=str(exc),
                )
            )

    return RelayExecutionSummary(
        results=tuple(results),
        errors=tuple(errors),
    )
