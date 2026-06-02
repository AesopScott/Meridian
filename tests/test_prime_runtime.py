"""Tests for Prime runtime decision contract."""

from meridian_core.compass_logic_snapshot import compass_logic_snapshot
from meridian_core.prime_runtime import (
    PrimeDecisionStatus,
    assemble_prime_runtime_context,
    make_prime_decision,
)
from meridian_core.relay_logic_snapshot import relay_logic_snapshot
from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot


def test_prime_runtime_context_assembles_backend_sources():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )

    assert context.project_id == "Meridian"
    assert "Prime oriented" in context.project_summary
    assert "session targets" in context.session_state
    assert "model-routing" in context.relay_route_summary
    assert [source.harness for source in context.source_refs] == [
        "Compass",
        "Vulcan",
        "Relay",
        "Aegis",
    ]


def test_prime_decision_shape_is_visible_and_executable():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = make_prime_decision(context=context)
    payload = decision.to_dict()

    assert payload["decisionId"] == "prime-runtime-decision-v1"
    assert payload["status"] == "executable"
    assert payload["ownerHarness"] == "Prime"
    assert payload["executable"] is True
    assert payload["blockers"] == []
    assert len(payload["proof"]) == 3
    assert {item["source"] for item in payload["proof"]} == {
        "Compass",
        "Vulcan",
        "Relay",
    }
    assert "visibleToScott" in payload


def test_prime_decision_blockers_force_blocked_status():
    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = make_prime_decision(
        context=context,
        status=PrimeDecisionStatus.EXECUTABLE,
        blockers=("Relay route unavailable",),
    )

    assert decision.status == PrimeDecisionStatus.BLOCKED
    assert decision.is_executable() is False
    assert decision.to_dict()["blockers"] == ["Relay route unavailable"]


def test_prime_context_falls_back_without_inventing_sources():
    context = assemble_prime_runtime_context(
        compass_snapshot={},
        vulcan_snapshot={},
        relay_snapshot={},
        project_id="Unknown",
    )
    payload = context.to_dict()

    assert payload["projectId"] == "Unknown"
    assert payload["projectSummary"] == "Compass project context unavailable."
    assert payload["sessionState"] == "Vulcan session lifecycle unavailable."
    assert payload["relayRouteSummary"] == "Relay model route unavailable."
    assert all(source["source"] in {"unknown", "pending"} for source in payload["sourceRefs"])
