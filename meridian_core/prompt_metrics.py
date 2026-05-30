"""
Prompt Metrics -- domain model for Relay prompt performance measurement.

Captures per-sample timing data and summarises across samples to determine
whether Relay is introducing measurable prompt drag. Domain-only: no model
calls, no persistence, no UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromptPerformanceStatus(Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class PromptMetricSample:
    sample_id: str
    prompt_tokens: int
    construction_time_ms: float
    total_response_time_ms: float
    time_to_first_token_ms: float | None = None
    native_baseline_ms: float | None = None

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError(f"prompt_tokens must be >= 0, got {self.prompt_tokens}")
        if self.construction_time_ms < 0.0:
            raise ValueError(f"construction_time_ms must be >= 0, got {self.construction_time_ms}")
        if self.total_response_time_ms < 0.0:
            raise ValueError(f"total_response_time_ms must be >= 0, got {self.total_response_time_ms}")
        if self.time_to_first_token_ms is not None and self.time_to_first_token_ms < 0.0:
            raise ValueError(f"time_to_first_token_ms must be >= 0, got {self.time_to_first_token_ms}")
        if self.native_baseline_ms is not None and self.native_baseline_ms < 0.0:
            raise ValueError(f"native_baseline_ms must be >= 0, got {self.native_baseline_ms}")


@dataclass(frozen=True)
class PromptMetricSummary:
    sample_count: int
    avg_prompt_tokens: float
    avg_construction_time_ms: float
    avg_total_response_time_ms: float
    avg_time_to_first_token_ms: float | None
    avg_overhead_delta_ms: float | None
    status: PromptPerformanceStatus


# Classification thresholds (ms)
_DELTA_WATCH_MS: float = 50.0
_DELTA_DEGRADED_MS: float = 200.0
_CONSTRUCTION_WATCH_MS: float = 100.0
_CONSTRUCTION_DEGRADED_MS: float = 300.0


def summarize_prompt_metrics(samples: list[PromptMetricSample]) -> PromptMetricSummary:
    """Aggregate prompt metric samples into a summary with performance status.

    Raises ValueError for an empty sample list.
    """
    if not samples:
        raise ValueError("cannot summarize an empty sample list")

    n = len(samples)

    avg_tokens = sum(s.prompt_tokens for s in samples) / n
    avg_construction = sum(s.construction_time_ms for s in samples) / n
    avg_total = sum(s.total_response_time_ms for s in samples) / n

    ttft_values = [s.time_to_first_token_ms for s in samples if s.time_to_first_token_ms is not None]
    avg_ttft = sum(ttft_values) / len(ttft_values) if ttft_values else None

    delta_values = [
        s.total_response_time_ms - s.native_baseline_ms
        for s in samples
        if s.native_baseline_ms is not None
    ]
    avg_delta = sum(delta_values) / len(delta_values) if delta_values else None

    return PromptMetricSummary(
        sample_count=n,
        avg_prompt_tokens=avg_tokens,
        avg_construction_time_ms=avg_construction,
        avg_total_response_time_ms=avg_total,
        avg_time_to_first_token_ms=avg_ttft,
        avg_overhead_delta_ms=avg_delta,
        status=_classify_status(avg_construction, avg_delta),
    )


def _classify_status(
    avg_construction_ms: float,
    avg_delta_ms: float | None,
) -> PromptPerformanceStatus:
    """Deterministic status classification from averaged metrics."""
    if avg_delta_ms is not None:
        if avg_delta_ms >= _DELTA_DEGRADED_MS:
            return PromptPerformanceStatus.DEGRADED
        if avg_delta_ms >= _DELTA_WATCH_MS:
            return PromptPerformanceStatus.WATCH
        return PromptPerformanceStatus.HEALTHY
    # No baseline available: classify on construction time alone
    if avg_construction_ms >= _CONSTRUCTION_DEGRADED_MS:
        return PromptPerformanceStatus.DEGRADED
    if avg_construction_ms >= _CONSTRUCTION_WATCH_MS:
        return PromptPerformanceStatus.WATCH
    return PromptPerformanceStatus.HEALTHY
