"""Tests for the Prompt Metrics domain slice (meridian_core/prompt_metrics.py)."""

from __future__ import annotations

import pytest

from meridian_core.prompt_metrics import (
    PromptMetricSample,
    PromptMetricSummary,
    PromptPerformanceStatus,
    summarize_prompt_metrics,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample(
    sample_id: str = "s-1",
    prompt_tokens: int = 500,
    construction_time_ms: float = 20.0,
    total_response_time_ms: float = 400.0,
    time_to_first_token_ms: float | None = None,
    native_baseline_ms: float | None = None,
) -> PromptMetricSample:
    return PromptMetricSample(
        sample_id=sample_id,
        prompt_tokens=prompt_tokens,
        construction_time_ms=construction_time_ms,
        total_response_time_ms=total_response_time_ms,
        time_to_first_token_ms=time_to_first_token_ms,
        native_baseline_ms=native_baseline_ms,
    )


# ---------------------------------------------------------------------------
# PromptMetricSample construction
# ---------------------------------------------------------------------------


class TestPromptMetricSample:
    def test_required_fields_stored(self):
        s = _sample()
        assert s.sample_id == "s-1"
        assert s.prompt_tokens == 500
        assert s.construction_time_ms == 20.0
        assert s.total_response_time_ms == 400.0

    def test_optional_fields_default_none(self):
        s = _sample()
        assert s.time_to_first_token_ms is None
        assert s.native_baseline_ms is None

    def test_optional_fields_stored(self):
        s = _sample(time_to_first_token_ms=80.0, native_baseline_ms=350.0)
        assert s.time_to_first_token_ms == 80.0
        assert s.native_baseline_ms == 350.0

    def test_sample_is_immutable(self):
        s = _sample()
        with pytest.raises((AttributeError, TypeError)):
            s.prompt_tokens = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Empty sample list
# ---------------------------------------------------------------------------


class TestEmptySampleList:
    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            summarize_prompt_metrics([])


# ---------------------------------------------------------------------------
# Single sample summary
# ---------------------------------------------------------------------------


class TestSingleSample:
    def _summary(self, **kwargs) -> PromptMetricSummary:
        return summarize_prompt_metrics([_sample(**kwargs)])

    def test_sample_count_is_one(self):
        assert self._summary().sample_count == 1

    def test_avg_prompt_tokens(self):
        assert self._summary(prompt_tokens=800).avg_prompt_tokens == 800.0

    def test_avg_construction_time(self):
        assert self._summary(construction_time_ms=30.0).avg_construction_time_ms == 30.0

    def test_avg_total_response_time(self):
        assert self._summary(total_response_time_ms=500.0).avg_total_response_time_ms == 500.0

    def test_avg_ttft_none_when_not_provided(self):
        assert self._summary().avg_time_to_first_token_ms is None

    def test_avg_ttft_when_provided(self):
        assert self._summary(time_to_first_token_ms=90.0).avg_time_to_first_token_ms == 90.0

    def test_avg_overhead_delta_none_without_baseline(self):
        assert self._summary(total_response_time_ms=400.0).avg_overhead_delta_ms is None

    def test_avg_overhead_delta_with_baseline(self):
        s = _sample(total_response_time_ms=400.0, native_baseline_ms=360.0)
        summary = summarize_prompt_metrics([s])
        assert summary.avg_overhead_delta_ms == pytest.approx(40.0)

    def test_returns_prompt_metric_summary(self):
        assert isinstance(self._summary(), PromptMetricSummary)

    def test_summary_is_immutable(self):
        summary = self._summary()
        with pytest.raises((AttributeError, TypeError)):
            summary.sample_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Multi-sample averages
# ---------------------------------------------------------------------------


class TestMultiSample:
    def test_sample_count(self):
        samples = [_sample(f"s-{i}") for i in range(5)]
        assert summarize_prompt_metrics(samples).sample_count == 5

    def test_avg_prompt_tokens_averages_correctly(self):
        samples = [
            _sample("s-1", prompt_tokens=200),
            _sample("s-2", prompt_tokens=400),
            _sample("s-3", prompt_tokens=600),
        ]
        assert summarize_prompt_metrics(samples).avg_prompt_tokens == pytest.approx(400.0)

    def test_avg_construction_time_averages_correctly(self):
        samples = [
            _sample("s-1", construction_time_ms=10.0),
            _sample("s-2", construction_time_ms=30.0),
        ]
        assert summarize_prompt_metrics(samples).avg_construction_time_ms == pytest.approx(20.0)

    def test_avg_total_response_time_averages_correctly(self):
        samples = [
            _sample("s-1", total_response_time_ms=300.0),
            _sample("s-2", total_response_time_ms=500.0),
        ]
        assert summarize_prompt_metrics(samples).avg_total_response_time_ms == pytest.approx(400.0)

    def test_avg_ttft_only_from_samples_with_value(self):
        samples = [
            _sample("s-1", time_to_first_token_ms=100.0),
            _sample("s-2", time_to_first_token_ms=None),
            _sample("s-3", time_to_first_token_ms=200.0),
        ]
        # average of 100 and 200 only
        assert summarize_prompt_metrics(samples).avg_time_to_first_token_ms == pytest.approx(150.0)

    def test_avg_ttft_none_when_all_missing(self):
        samples = [_sample(f"s-{i}") for i in range(3)]
        assert summarize_prompt_metrics(samples).avg_time_to_first_token_ms is None

    def test_avg_overhead_delta_only_from_baseline_samples(self):
        samples = [
            _sample("s-1", total_response_time_ms=400.0, native_baseline_ms=350.0),  # delta=50
            _sample("s-2", total_response_time_ms=500.0, native_baseline_ms=None),   # no baseline
            _sample("s-3", total_response_time_ms=450.0, native_baseline_ms=400.0),  # delta=50
        ]
        assert summarize_prompt_metrics(samples).avg_overhead_delta_ms == pytest.approx(50.0)

    def test_avg_overhead_delta_none_when_no_baselines(self):
        samples = [_sample(f"s-{i}") for i in range(3)]
        assert summarize_prompt_metrics(samples).avg_overhead_delta_ms is None


# ---------------------------------------------------------------------------
# Status classification — with baseline delta
# ---------------------------------------------------------------------------


class TestStatusWithBaseline:
    def _summary_for_delta(self, delta: float) -> PromptMetricSummary:
        # Set total 400, baseline = 400 - delta so overhead_delta == delta
        s = _sample(total_response_time_ms=400.0, native_baseline_ms=400.0 - delta)
        return summarize_prompt_metrics([s])

    def test_delta_below_watch_threshold_is_healthy(self):
        assert self._summary_for_delta(0.0).status is PromptPerformanceStatus.HEALTHY

    def test_delta_just_below_watch_threshold_is_healthy(self):
        assert self._summary_for_delta(49.9).status is PromptPerformanceStatus.HEALTHY

    def test_delta_at_watch_threshold_is_watch(self):
        assert self._summary_for_delta(50.0).status is PromptPerformanceStatus.WATCH

    def test_delta_between_watch_and_degraded_is_watch(self):
        assert self._summary_for_delta(100.0).status is PromptPerformanceStatus.WATCH

    def test_delta_just_below_degraded_threshold_is_watch(self):
        assert self._summary_for_delta(199.9).status is PromptPerformanceStatus.WATCH

    def test_delta_at_degraded_threshold_is_degraded(self):
        assert self._summary_for_delta(200.0).status is PromptPerformanceStatus.DEGRADED

    def test_delta_above_degraded_threshold_is_degraded(self):
        assert self._summary_for_delta(500.0).status is PromptPerformanceStatus.DEGRADED

    def test_negative_delta_is_healthy(self):
        # Total faster than baseline: no overhead
        assert self._summary_for_delta(-10.0).status is PromptPerformanceStatus.HEALTHY


# ---------------------------------------------------------------------------
# Status classification — without baseline (construction time only)
# ---------------------------------------------------------------------------


class TestStatusWithoutBaseline:
    def _summary_for_construction(self, ms: float) -> PromptMetricSummary:
        return summarize_prompt_metrics([_sample(construction_time_ms=ms)])

    def test_fast_construction_is_healthy(self):
        assert self._summary_for_construction(50.0).status is PromptPerformanceStatus.HEALTHY

    def test_just_below_watch_threshold_is_healthy(self):
        assert self._summary_for_construction(99.9).status is PromptPerformanceStatus.HEALTHY

    def test_at_watch_threshold_is_watch(self):
        assert self._summary_for_construction(100.0).status is PromptPerformanceStatus.WATCH

    def test_between_watch_and_degraded_is_watch(self):
        assert self._summary_for_construction(200.0).status is PromptPerformanceStatus.WATCH

    def test_just_below_degraded_threshold_is_watch(self):
        assert self._summary_for_construction(299.9).status is PromptPerformanceStatus.WATCH

    def test_at_degraded_threshold_is_degraded(self):
        assert self._summary_for_construction(300.0).status is PromptPerformanceStatus.DEGRADED

    def test_above_degraded_threshold_is_degraded(self):
        assert self._summary_for_construction(1000.0).status is PromptPerformanceStatus.DEGRADED

    def test_baseline_takes_precedence_over_construction(self):
        # Fast construction (10ms) but large delta (300ms) -> DEGRADED
        s = _sample(construction_time_ms=10.0, total_response_time_ms=500.0, native_baseline_ms=200.0)
        assert summarize_prompt_metrics([s]).status is PromptPerformanceStatus.DEGRADED


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self):
        samples = [
            _sample("s-1", prompt_tokens=300, construction_time_ms=20.0, total_response_time_ms=350.0),
            _sample("s-2", prompt_tokens=700, construction_time_ms=40.0, total_response_time_ms=600.0),
        ]
        s1 = summarize_prompt_metrics(samples)
        s2 = summarize_prompt_metrics(samples)
        assert s1.avg_prompt_tokens == s2.avg_prompt_tokens
        assert s1.avg_construction_time_ms == s2.avg_construction_time_ms
        assert s1.status is s2.status

    def test_status_enum_values_are_stable(self):
        assert PromptPerformanceStatus.HEALTHY.value == "healthy"
        assert PromptPerformanceStatus.WATCH.value == "watch"
        assert PromptPerformanceStatus.DEGRADED.value == "degraded"
