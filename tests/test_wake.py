"""Tests for the Prime wake sequence."""

from __future__ import annotations

from meridian_core.decisions import DecisionResult, run_decision_loop
from meridian_core.models import (
    Heartbeat,
    HeartbeatStatus,
    Portfolio,
    Priority,
    ScottBottleneck,
)
from meridian_core.sample_state import make_sample_heartbeats, make_sample_portfolio
from meridian_core.wake import WakeBrief, WakeStatus, build_wake_brief


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_result() -> DecisionResult:
    return DecisionResult()


# ---------------------------------------------------------------------------
# Healthy wake sequence
# ---------------------------------------------------------------------------


class TestHealthyWake:
    def test_title_is_always_prime_online(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        assert brief.title == "Prime online."

    def test_alive_harness_maps_to_online(self) -> None:
        hbs = [Heartbeat("agent_harness", HeartbeatStatus.ALIVE)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        relay = next(l for l in brief.lines if l.label == "Relay")
        assert relay.status == WakeStatus.ONLINE
        assert relay.message == "Relay online."

    def test_busy_harness_maps_to_stable(self) -> None:
        hbs = [Heartbeat("memory_harness", HeartbeatStatus.BUSY)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        echo = next(l for l in brief.lines if l.label == "Echo")
        assert echo.status == WakeStatus.STABLE
        assert echo.message == "Echo stable."

    def test_sleeping_harness_maps_to_standing_by(self) -> None:
        hbs = [Heartbeat("tool_harness", HeartbeatStatus.SLEEPING)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        forge = next(l for l in brief.lines if l.label == "Forge")
        assert forge.status == WakeStatus.STANDING_BY
        assert forge.message == "Forge standing by."

    def test_no_unhealthy_harnesses_absent_from_summary(self) -> None:
        hbs = [Heartbeat("agent_harness", HeartbeatStatus.ALIVE)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        assert "attention" not in brief.summary

    def test_empty_state_returns_nominal_summary(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        assert brief.summary == "All systems nominal."


# ---------------------------------------------------------------------------
# Degraded / stalled harness
# ---------------------------------------------------------------------------


class TestDegradedHarness:
    def test_stale_harness_is_degraded(self) -> None:
        hbs = [Heartbeat("proof_harness", HeartbeatStatus.STALE)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        aegis = next(l for l in brief.lines if l.label == "Aegis")
        assert aegis.status == WakeStatus.DEGRADED
        assert aegis.message == "Aegis degraded."

    def test_blocked_harness_is_blocked(self) -> None:
        hbs = [Heartbeat("git_harness", HeartbeatStatus.BLOCKED)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        groot = next(l for l in brief.lines if l.label == "Groot")
        assert groot.status == WakeStatus.BLOCKED
        assert groot.message == "Groot blocked."

    def test_failed_harness_is_offline(self) -> None:
        hbs = [Heartbeat("agent_harness", HeartbeatStatus.FAILED)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        relay = next(l for l in brief.lines if l.label == "Relay")
        assert relay.status == WakeStatus.OFFLINE
        assert relay.message == "Relay offline."

    def test_single_unhealthy_uses_singular(self) -> None:
        hbs = [Heartbeat("git_harness", HeartbeatStatus.BLOCKED)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        assert "1 harness needs attention" in brief.summary

    def test_multiple_unhealthy_uses_plural(self) -> None:
        hbs = [
            Heartbeat("git_harness", HeartbeatStatus.BLOCKED),
            Heartbeat("proof_harness", HeartbeatStatus.STALE),
        ]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        assert "2 harnesses need attention" in brief.summary

    def test_sample_state_stalled_harnesses_appear(self) -> None:
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        brief = build_wake_brief(portfolio, heartbeats, result)
        statuses = {l.label: l.status for l in brief.lines}
        assert statuses["Groot"] == WakeStatus.BLOCKED
        assert statuses["Aegis"] == WakeStatus.DEGRADED


# ---------------------------------------------------------------------------
# Bottlenecks
# ---------------------------------------------------------------------------


class TestBottlenecks:
    def test_scott_bottlenecks_appear_in_brief(self) -> None:
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        brief = build_wake_brief(portfolio, heartbeats, result)
        assert len(brief.bottlenecks) > 0

    def test_bottleneck_titles_match_decision_result(self) -> None:
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        brief = build_wake_brief(portfolio, heartbeats, result)
        expected = {bn.title for bn in result.scott_bottlenecks}
        assert set(brief.bottlenecks) == expected

    def test_single_bottleneck_uses_singular(self) -> None:
        result = DecisionResult(
            scott_bottlenecks=[
                ScottBottleneck(
                    id="bn1",
                    title="Choose API approach",
                    description="Pick one.",
                    priority=Priority.HIGH,
                )
            ]
        )
        brief = build_wake_brief(Portfolio(), [], result)
        assert "1 decision needs your judgment" in brief.summary

    def test_multiple_bottlenecks_uses_plural(self) -> None:
        result = DecisionResult(
            scott_bottlenecks=[
                ScottBottleneck(id=f"bn{i}", title=f"Decision {i}", description=".", priority=Priority.HIGH)
                for i in range(3)
            ]
        )
        brief = build_wake_brief(Portfolio(), [], result)
        assert "3 decisions need your judgment" in brief.summary

    def test_no_bottlenecks_omits_judgment_phrase(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        assert "judgment" not in brief.summary


# ---------------------------------------------------------------------------
# Order stability
# ---------------------------------------------------------------------------


class TestOrderStability:
    def test_canonical_order_respected(self) -> None:
        hbs = [
            Heartbeat("git_harness", HeartbeatStatus.ALIVE),      # Groot
            Heartbeat("memory_harness", HeartbeatStatus.BUSY),    # Echo
            Heartbeat("agent_harness", HeartbeatStatus.ALIVE),    # Relay
        ]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        labels = [l.label for l in brief.lines]
        assert labels.index("Echo") < labels.index("Relay") < labels.index("Groot")

    def test_unknown_harness_appears_after_canonical(self) -> None:
        hbs = [
            Heartbeat("agent_harness", HeartbeatStatus.ALIVE),
            Heartbeat("zzz_custom", HeartbeatStatus.ALIVE),
        ]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        labels = [l.label for l in brief.lines]
        assert labels.index("Relay") < labels.index("zzz_custom")

    def test_output_is_deterministic(self) -> None:
        portfolio = make_sample_portfolio()
        heartbeats = make_sample_heartbeats()
        result = run_decision_loop(portfolio, heartbeats)
        brief1 = build_wake_brief(portfolio, heartbeats, result)
        brief2 = build_wake_brief(portfolio, heartbeats, result)
        assert [l.label for l in brief1.lines] == [l.label for l in brief2.lines]

    def test_same_harness_id_same_label_repeated_calls(self) -> None:
        hbs = [Heartbeat("proof_harness", HeartbeatStatus.STALE)]
        b1 = build_wake_brief(Portfolio(), hbs, _empty_result())
        b2 = build_wake_brief(Portfolio(), hbs, _empty_result())
        assert b1.lines[0].label == b2.lines[0].label == "Bifrost"


# ---------------------------------------------------------------------------
# Canonical harnesses always present
# ---------------------------------------------------------------------------


class TestCanonicalAlwaysPresent:
    def test_all_canonical_harnesses_appear_with_no_heartbeats(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        labels = [l.label for l in brief.lines]
        for expected in ("Bifrost", "Beacon", "Echo", "Atlas", "Vault", "Forge",
                         "Aegis", "Charter", "Loom", "Compass", "Relay", "Groot",
                         "Lens", "Launch"):
            assert expected in labels, f"{expected} missing from wake lines"

    def test_beacon_appears_without_heartbeat(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        beacon = next(l for l in brief.lines if l.label == "Beacon")
        assert beacon.status == WakeStatus.UNKNOWN
        assert beacon.message == "Beacon pending."

    def test_canonical_harness_without_heartbeat_is_pending(self) -> None:
        # Only give Echo a heartbeat; Relay should still appear as pending
        hbs = [Heartbeat("memory_harness", HeartbeatStatus.BUSY)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        relay = next(l for l in brief.lines if l.label == "Relay")
        assert relay.status == WakeStatus.UNKNOWN
        assert relay.message == "Relay pending."

    def test_heartbeat_overrides_pending_for_canonical_harness(self) -> None:
        hbs = [Heartbeat("health_harness", HeartbeatStatus.ALIVE)]
        brief = build_wake_brief(Portfolio(), hbs, _empty_result())
        beacon = next(l for l in brief.lines if l.label == "Beacon")
        assert beacon.status == WakeStatus.ONLINE
        assert beacon.message == "Beacon online."

    def test_canonical_count_is_fourteen(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        assert len(brief.lines) == 14

    def test_canonical_order_stable_without_heartbeats(self) -> None:
        brief = build_wake_brief(Portfolio(), [], _empty_result())
        labels = [l.label for l in brief.lines]
        assert labels == [
            "Bifrost", "Beacon", "Echo", "Atlas", "Vault", "Forge",
            "Aegis", "Charter", "Loom", "Compass", "Relay", "Groot",
            "Lens", "Launch",
        ]
