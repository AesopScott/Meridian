"""Tests for ``meridian_core.workflow_dispatch``.

These tests exercise the first pure runtime slice of the Workflow
Sub-Agent Harness contract
(``docs/workflow-subagent-harness-contract.md``). They cover the frozen
domain dataclasses, the closed enums, the dispatch helper, the
promotion / acceptance helper, the input / path / tool validation
helpers, and the prompt-drag guards that reject raw transcript / log /
file / search return fields.

The tests are pure / local — no live workflow execution, no process /
session control, no model calls, no network, no UI behavior. Handlers
under test are fake / stub callables defined inline.
"""

from __future__ import annotations

import dataclasses

import pytest

from meridian_core.workflow_dispatch import (
    MAX_HEARTBEAT_SUMMARY_LENGTH,
    MAX_RESULT_SUMMARY_LENGTH,
    WORKFLOW_NESTING_CAP,
    HandlerReturn,
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowGateContext,
    WorkflowHandler,
    WorkflowHarness,
    WorkflowHeartbeat,
    WorkflowInputPacket,
    WorkflowInputRecord,
    WorkflowPhase,
    WorkflowPromotionDecision,
    WorkflowPromptBudget,
    WorkflowResteerChanges,
    WorkflowResteerRequest,
    WorkflowResultSummary,
    WorkflowValidationError,
    WorkflowWorkOrder,
    apply_resteer,
    dispatch_work_order,
    is_path_in_scope,
    promote_workflow_result,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _budget() -> WorkflowPromptBudget:
    return WorkflowPromptBudget(
        max_prompt_tokens=2000,
        max_response_tokens=400,
        notes="standard cap",
    )


def _packet(
    *,
    inputs: tuple[WorkflowInputRecord, ...] = (),
    allowed_tools: tuple[str, ...] = ("read_file",),
    allowed_paths: tuple[str, ...] = ("src/", "tests/"),
    forbidden_paths: tuple[str, ...] = (".env",),
    gate_context: WorkflowGateContext | None = None,
) -> WorkflowInputPacket:
    return WorkflowInputPacket(
        project="meridian",
        goal_summary="distill memory hits for the active goal",
        inputs=inputs,
        allowed_tools=allowed_tools,
        allowed_paths=allowed_paths,
        forbidden_paths=forbidden_paths,
        prompt_budget=_budget(),
        gate_context=gate_context,
    )


def _order(
    *,
    work_order_id: str = "wo-001",
    harness: WorkflowHarness = WorkflowHarness.ATLAS,
    action: str = "atlas.search",
    intent: str = "find candidate hits for the active goal",
    risk_tier: int = 1,
    input_packet: WorkflowInputPacket | None = None,
    expected_result_shape: str = "AtlasResult",
    time_budget_seconds: int = 30,
    hard_timeout_seconds: int = 60,
    created_at: str = "2026-06-07T16:20:00Z",
    parent_work_order_id: str = "",
    depth: int = 0,
) -> WorkflowWorkOrder:
    return WorkflowWorkOrder(
        work_order_id=work_order_id,
        harness=harness,
        action=action,
        intent=intent,
        risk_tier=risk_tier,
        input=input_packet if input_packet is not None else _packet(),
        expected_result_shape=expected_result_shape,
        time_budget_seconds=time_budget_seconds,
        hard_timeout_seconds=hard_timeout_seconds,
        created_at=created_at,
        parent_work_order_id=parent_work_order_id,
        depth=depth,
    )


def _gate() -> WorkflowGateContext:
    return WorkflowGateContext(
        policy_decision="ALLOW",
        proof_handles=("proof.atlas.candidates",),
        notes="tier-3 gate present",
    )


def _result(
    order: WorkflowWorkOrder,
    *,
    outputs: tuple = (),
    proof_trail: tuple[str, ...] = (),
    summary: str = "one bounded result distilled",
    next_action_recommendation: str = "",
    requires_human_gate: bool = False,
    tokens_used: int = 12,
    time_used_seconds: float = 0.5,
) -> WorkflowResultSummary:
    return WorkflowResultSummary(
        work_order_id=order.work_order_id,
        harness=order.harness,
        result_shape=order.expected_result_shape,
        summary=summary,
        outputs=outputs,
        proof_trail=proof_trail,
        tokens_used=tokens_used,
        time_used_seconds=time_used_seconds,
        next_action_recommendation=next_action_recommendation,
        requires_human_gate=requires_human_gate,
    )


# ---------------------------------------------------------------------------
# Domain shape — frozen dataclasses and closed enums
# ---------------------------------------------------------------------------

class TestEnumCoverage:
    def test_harness_values(self) -> None:
        assert {h.value for h in WorkflowHarness} == {
            "echo",
            "atlas",
            "aegis",
            "relay",
            "bifrost",
            "beacon",
            "session_lifecycle",
        }

    def test_phase_values(self) -> None:
        assert {p.value for p in WorkflowPhase} == {
            "started",
            "working",
            "waiting_for_tool",
            "waiting_for_gate",
            "warning",
            "finalizing",
        }

    def test_failure_kind_values(self) -> None:
        assert {f.value for f in WorkflowFailureKind} == {
            "timeout",
            "tool_denied",
            "input_invalid",
            "proof_unavailable",
            "gate_required",
            "internal_error",
            "resteer_requested",
        }


class TestFrozenDataclasses:
    @pytest.mark.parametrize(
        "factory",
        [
            lambda: WorkflowInputRecord(source="echo", kind="memory_hit"),
            lambda: _budget(),
            lambda: _gate(),
            lambda: _packet(),
            lambda: _order(),
            lambda: WorkflowHeartbeat(
                work_order_id="wo-001",
                sequence=0,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="started",
            ),
            lambda: _result(_order()),
            lambda: WorkflowErrorSummary(
                work_order_id="wo-001",
                harness=WorkflowHarness.ATLAS,
                failure_kind=WorkflowFailureKind.INTERNAL_ERROR,
                summary="boom",
            ),
            lambda: WorkflowResteerChanges(),
            lambda: WorkflowResteerRequest(
                original_work_order_id="wo-001",
                reason="narrower scope",
                suggested_changes=WorkflowResteerChanges(),
            ),
        ],
    )
    def test_frozen_mutation_raises(self, factory) -> None:
        instance = factory()
        with pytest.raises(dataclasses.FrozenInstanceError):
            object.__setattr__  # sanity; we use the public attribute path
            setattr(instance, "summary", "tampered")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Validation: WorkflowInputRecord
# ---------------------------------------------------------------------------

class TestInputRecord:
    def test_minimum_valid(self) -> None:
        rec = WorkflowInputRecord(source="echo", kind="memory_hit")
        assert rec.source == "echo"
        assert rec.kind == "memory_hit"
        assert rec.ref == ""
        assert rec.summary == ""

    def test_unsafe_summary_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputRecord(
                source="echo",
                kind="memory_hit",
                summary="raw_transcript: scott said ...",
            )

    def test_unsafe_ref_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputRecord(
                source="echo",
                kind="memory_hit",
                ref="bearer secret-token",
            )

    def test_ref_with_newline_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputRecord(
                source="echo",
                kind="memory_hit",
                ref="line1\nline2",
            )

    def test_invalid_identifier_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputRecord(source="echo source", kind="memory_hit")


# ---------------------------------------------------------------------------
# Validation: WorkflowPromptBudget & gate context
# ---------------------------------------------------------------------------

class TestPromptBudget:
    def test_non_positive_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowPromptBudget(max_prompt_tokens=0, max_response_tokens=10)
        with pytest.raises(WorkflowValidationError):
            WorkflowPromptBudget(max_prompt_tokens=10, max_response_tokens=-1)

    def test_bool_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowPromptBudget(
                max_prompt_tokens=True,  # type: ignore[arg-type]
                max_response_tokens=10,
            )


class TestGateContext:
    def test_unknown_policy_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowGateContext(policy_decision="MAYBE")

    def test_duplicate_handles_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowGateContext(
                policy_decision="ALLOW",
                proof_handles=("dup", "dup"),
            )


# ---------------------------------------------------------------------------
# Validation: WorkflowInputPacket
# ---------------------------------------------------------------------------

class TestInputPacket:
    def test_summarize_only_when_no_tools(self) -> None:
        packet = _packet(allowed_tools=())
        assert packet.is_summarize_only is True

    def test_with_tools_not_summarize_only(self) -> None:
        packet = _packet(allowed_tools=("read_file",))
        assert packet.is_summarize_only is False

    def test_file_path_input_outside_allowed_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(
                inputs=(
                    WorkflowInputRecord(
                        source="scott",
                        kind="file_path",
                        ref="secrets/key.pem",
                    ),
                ),
                allowed_paths=("src/", "tests/"),
                forbidden_paths=(".env",),
            )

    def test_file_path_input_inside_forbidden_rejected(self) -> None:
        # Segment-aware semantics: forbidden prefix matches at directory
        # boundaries, so a real secrets directory is rejected.
        with pytest.raises(WorkflowValidationError):
            _packet(
                inputs=(
                    WorkflowInputRecord(
                        source="scott",
                        kind="file_path",
                        ref="src/secrets/key.pem",
                    ),
                ),
                allowed_paths=("src/",),
                forbidden_paths=("src/secrets",),
            )

    def test_file_path_input_sibling_prefix_escape_rejected(self) -> None:
        # Regression: raw startswith would have accepted "src/atlas2/file.py"
        # under prefix "src/atlas". Segment-aware semantics rejects it.
        with pytest.raises(WorkflowValidationError):
            _packet(
                inputs=(
                    WorkflowInputRecord(
                        source="scott",
                        kind="file_path",
                        ref="src/atlas2/file.py",
                    ),
                ),
                allowed_paths=("src/atlas",),
                forbidden_paths=(),
            )

    def test_file_path_input_dash_sibling_escape_rejected(self) -> None:
        # Regression: "src/atlas-secret/file.py" must NOT match "src/atlas".
        with pytest.raises(WorkflowValidationError):
            _packet(
                inputs=(
                    WorkflowInputRecord(
                        source="scott",
                        kind="file_path",
                        ref="src/atlas-secret/file.py",
                    ),
                ),
                allowed_paths=("src/atlas",),
                forbidden_paths=(),
            )

    def test_file_path_input_exact_match_allowed(self) -> None:
        # Exact match against a non-slash-terminated prefix is allowed.
        packet = _packet(
            inputs=(
                WorkflowInputRecord(
                    source="scott",
                    kind="file_path",
                    ref="src/atlas",
                ),
            ),
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        )
        assert packet.inputs[0].ref == "src/atlas"

    def test_file_path_input_child_under_unterminated_prefix_allowed(self) -> None:
        packet = _packet(
            inputs=(
                WorkflowInputRecord(
                    source="scott",
                    kind="file_path",
                    ref="src/atlas/file.py",
                ),
            ),
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        )
        assert packet.inputs[0].ref == "src/atlas/file.py"

    def test_file_path_input_inside_allowed_accepted(self) -> None:
        packet = _packet(
            inputs=(
                WorkflowInputRecord(
                    source="scott",
                    kind="file_path",
                    ref="src/main.py",
                ),
            ),
            allowed_paths=("src/",),
            forbidden_paths=(".env",),
        )
        assert packet.inputs[0].ref == "src/main.py"

    def test_path_prefix_rejects_absolute(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_paths=("/etc/",))

    def test_path_prefix_rejects_traversal(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_paths=("../sibling/",))

    def test_path_prefix_rejects_windows_drive(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_paths=("C:/Users/scott/",))

    def test_duplicate_allowed_paths_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_paths=("src/", "src/"))

    def test_duplicate_tools_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_tools=("read_file", "read_file"))

    def test_unsafe_tool_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _packet(allowed_tools=("read file",))

    def test_unsafe_goal_summary_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputPacket(
                project="meridian",
                goal_summary="raw_transcript snippet here",
                inputs=(),
                allowed_tools=(),
                allowed_paths=(),
                forbidden_paths=(),
                prompt_budget=_budget(),
            )

    def test_empty_goal_summary_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputPacket(
                project="meridian",
                goal_summary="",
                inputs=(),
                allowed_tools=(),
                allowed_paths=(),
                forbidden_paths=(),
                prompt_budget=_budget(),
            )

    def test_inputs_not_tuple_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowInputPacket(
                project="meridian",
                goal_summary="ok",
                inputs=[],  # type: ignore[arg-type]
                allowed_tools=(),
                allowed_paths=(),
                forbidden_paths=(),
                prompt_budget=_budget(),
            )


class TestPathScopeHelper:
    def test_forbidden_overlap_always_denies(self) -> None:
        allowed = ("src/",)
        forbidden = ("src/secrets/",)
        assert is_path_in_scope(
            "src/main.py",
            allowed_paths=allowed,
            forbidden_paths=forbidden,
        ) is True
        assert is_path_in_scope(
            "src/secrets/key.pem",
            allowed_paths=allowed,
            forbidden_paths=forbidden,
        ) is False

    def test_outside_allowed_denied(self) -> None:
        assert is_path_in_scope(
            "docs/notes.md",
            allowed_paths=("src/",),
            forbidden_paths=(),
        ) is False

    def test_unsafe_path_rejected(self) -> None:
        assert is_path_in_scope(
            "/etc/passwd",
            allowed_paths=("/etc/",),
            forbidden_paths=(),
        ) is False

    def test_sibling_numeric_prefix_escape_rejected(self) -> None:
        # Regression: raw startswith would have accepted this.
        assert is_path_in_scope(
            "src/atlas2/file.py",
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        ) is False

    def test_sibling_dash_prefix_escape_rejected(self) -> None:
        assert is_path_in_scope(
            "src/atlas-secret/file.py",
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        ) is False

    def test_exact_match_allowed(self) -> None:
        assert is_path_in_scope(
            "src/atlas",
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        ) is True

    def test_child_under_unterminated_prefix_allowed(self) -> None:
        assert is_path_in_scope(
            "src/atlas/file.py",
            allowed_paths=("src/atlas",),
            forbidden_paths=(),
        ) is True

    def test_forbidden_segment_aware_blocks_real_child(self) -> None:
        assert is_path_in_scope(
            "src/atlas/secrets/key.pem",
            allowed_paths=("src/atlas",),
            forbidden_paths=("src/atlas/secrets",),
        ) is False

    def test_forbidden_segment_aware_does_not_block_sibling(self) -> None:
        # "src/atlas/secrets-public/file.py" is a sibling of the forbidden
        # "src/atlas/secrets" prefix and must remain allowed under the
        # parent "src/atlas" allow.
        assert is_path_in_scope(
            "src/atlas/secrets-public/file.py",
            allowed_paths=("src/atlas",),
            forbidden_paths=("src/atlas/secrets",),
        ) is True


# ---------------------------------------------------------------------------
# Validation: WorkflowWorkOrder
# ---------------------------------------------------------------------------

class TestWorkOrder:
    def test_happy_path(self) -> None:
        order = _order()
        assert order.work_order_id == "wo-001"
        assert order.harness is WorkflowHarness.ATLAS
        assert order.depth == 0

    def test_invalid_risk_tier_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(risk_tier=0)
        with pytest.raises(WorkflowValidationError):
            _order(risk_tier=5)

    def test_action_with_space_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(action="atlas search")

    def test_time_budget_above_hard_timeout_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(time_budget_seconds=120, hard_timeout_seconds=60)

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(time_budget_seconds=0, hard_timeout_seconds=60)

    def test_excessive_timeout_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(hard_timeout_seconds=10 ** 9)

    def test_unsafe_intent_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(intent="raw_transcript reveal")

    def test_depth_beyond_cap_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(
                depth=WORKFLOW_NESTING_CAP + 1,
                parent_work_order_id="wo-parent",
            )

    def test_depth_zero_with_parent_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(depth=0, parent_work_order_id="wo-parent")

    def test_nested_without_parent_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(depth=1, parent_work_order_id="")

    def test_created_at_required(self) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(created_at="")

    @pytest.mark.parametrize(
        "bad_timestamp",
        [
            "t",
            "now",
            "2026-06-07 16:20:00",
            "2026-06-07T16:20:00",
            "2026-06-07T16:20:00+00:00",
            "2026-06-07T16:20:00z",
            "26-06-07T16:20:00Z",
            "2026-13-07T16:20:00Z",
            "2026-00-07T16:20:00Z",
            "2026-06-07T24:00:00Z",
        ],
    )
    def test_invalid_created_at_rejected(self, bad_timestamp: str) -> None:
        with pytest.raises(WorkflowValidationError):
            _order(created_at=bad_timestamp)

    @pytest.mark.parametrize(
        "good_timestamp",
        [
            "2026-06-07T16:20:00Z",
            "2026-06-07T16:20:00.5Z",
            "2026-06-07T16:20:00.123456Z",
        ],
    )
    def test_valid_created_at_accepted(self, good_timestamp: str) -> None:
        order = _order(created_at=good_timestamp)
        assert order.created_at == good_timestamp


# ---------------------------------------------------------------------------
# Validation: WorkflowHeartbeat
# ---------------------------------------------------------------------------

class TestHeartbeat:
    def test_progress_estimate_bounds(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowHeartbeat(
                work_order_id="wo-001",
                sequence=0,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="hi",
                progress_estimate=1.5,
            )

    def test_negative_sequence_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowHeartbeat(
                work_order_id="wo-001",
                sequence=-1,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="hi",
            )

    def test_oversized_summary_rejected(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowHeartbeat(
                work_order_id="wo-001",
                sequence=0,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="x" * (MAX_HEARTBEAT_SUMMARY_LENGTH + 1),
            )

    @pytest.mark.parametrize(
        "bad_timestamp",
        [
            "t",
            "not a timestamp",
            "now",
            "2026-06-07 16:20:00",  # no T, no Z
            "2026-06-07T16:20:00",  # no Z
            "2026-06-07T16:20:00+00:00",  # offset, not Z
            "2026-06-07T16:20:00z",  # lowercase z
            "20260607T162000Z",  # no dashes / colons
            "26-06-07T16:20:00Z",  # 2-digit year
            "2026-13-07T16:20:00Z",  # bad month
            "2026-06-32T16:20:00Z",  # bad day
            "2026-06-07T25:20:00Z",  # bad hour
            "2026-06-07T16:60:00Z",  # bad minute
            "",
        ],
    )
    def test_invalid_emitted_at_rejected(self, bad_timestamp: str) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowHeartbeat(
                work_order_id="wo-001",
                sequence=0,
                emitted_at=bad_timestamp,
                phase=WorkflowPhase.WORKING,
                summary="hi",
            )

    @pytest.mark.parametrize(
        "good_timestamp",
        [
            "2026-06-07T16:21:00Z",
            "2026-06-07T16:21:00.5Z",
            "2026-06-07T16:21:00.123456Z",
            "2026-06-07T00:00:00Z",
            "2026-06-07T23:59:59Z",
        ],
    )
    def test_valid_emitted_at_accepted(self, good_timestamp: str) -> None:
        hb = WorkflowHeartbeat(
            work_order_id="wo-001",
            sequence=0,
            emitted_at=good_timestamp,
            phase=WorkflowPhase.WORKING,
            summary="hi",
        )
        assert hb.emitted_at == good_timestamp


# ---------------------------------------------------------------------------
# Validation: WorkflowResultSummary / WorkflowErrorSummary
# ---------------------------------------------------------------------------

class TestResultErrorConstruction:
    def test_result_outputs_must_be_tuple(self) -> None:
        order = _order()
        with pytest.raises(WorkflowValidationError):
            WorkflowResultSummary(
                work_order_id=order.work_order_id,
                harness=order.harness,
                result_shape=order.expected_result_shape,
                summary="hi",
                outputs=[],  # type: ignore[arg-type]
            )

    def test_result_summary_oversize_rejected(self) -> None:
        order = _order()
        with pytest.raises(WorkflowValidationError):
            _result(order, summary="x" * (MAX_RESULT_SUMMARY_LENGTH + 1))

    def test_result_summary_unsafe_marker_rejected(self) -> None:
        order = _order()
        with pytest.raises(WorkflowValidationError):
            _result(order, summary="BEGIN TRANSCRIPT: scott said...")

    def test_result_proof_trail_must_be_safe_refs(self) -> None:
        order = _order()
        with pytest.raises(WorkflowValidationError):
            _result(order, proof_trail=("proof with space",))

    def test_error_resteer_requires_request(self) -> None:
        with pytest.raises(WorkflowValidationError):
            WorkflowErrorSummary(
                work_order_id="wo-001",
                harness=WorkflowHarness.ATLAS,
                failure_kind=WorkflowFailureKind.RESTEER_REQUESTED,
                summary="needs resteer",
                resteer_request=None,
            )


# ---------------------------------------------------------------------------
# Dispatch — happy path & shape
# ---------------------------------------------------------------------------

class TestDispatchHappyPath:
    def test_tier1_minimal_success(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=("hit-a", "hit-b"))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)
        assert out.work_order_id == "wo-001"
        assert out.result_shape == "AtlasResult"
        assert isinstance(out.outputs, tuple)

    def test_outputs_remain_tuple(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=("a", "b", "c"))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)
        assert isinstance(out.outputs, tuple)
        assert out.outputs == ("a", "b", "c")

    def test_result_shape_mismatch_becomes_input_invalid(self) -> None:
        order = _order(expected_result_shape="AtlasResult")

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResultSummary(
                work_order_id=wo.work_order_id,
                harness=wo.harness,
                result_shape="WrongShape",
                summary="oops",
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_work_order_id_mismatch_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResultSummary(
                work_order_id="wo-other",
                harness=wo.harness,
                result_shape=wo.expected_result_shape,
                summary="cross-order leak",
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_harness_mismatch_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResultSummary(
                work_order_id=wo.work_order_id,
                harness=WorkflowHarness.RELAY,
                result_shape=wo.expected_result_shape,
                summary="cross-harness leak",
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID


# ---------------------------------------------------------------------------
# Dispatch — tier proof enforcement
# ---------------------------------------------------------------------------

class TestDispatchTierProof:
    def test_tier1_empty_proof_accepted(self) -> None:
        order = _order(risk_tier=1)

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo)

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)
        assert out.proof_trail == ()

    def test_tier2_empty_proof_becomes_proof_unavailable(self) -> None:
        order = _order(risk_tier=2)

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo)

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.PROOF_UNAVAILABLE

    def test_tier2_with_proof_accepted(self) -> None:
        order = _order(risk_tier=2)

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, proof_trail=("proof.alpha",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)


# ---------------------------------------------------------------------------
# Dispatch — gate context (tier-3+) gating
# ---------------------------------------------------------------------------

class TestDispatchGateContext:
    def test_tier3_missing_gate_context_rejected_before_handler(self) -> None:
        order = _order(
            risk_tier=3,
            input_packet=_packet(gate_context=None),
        )
        called = []

        def handler(wo, emit):  # noqa: ANN001
            called.append(wo.work_order_id)
            return _result(wo, proof_trail=("p1",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.GATE_REQUIRED
        assert called == []

    def test_tier3_with_gate_context_runs(self) -> None:
        order = _order(
            risk_tier=3,
            input_packet=_packet(gate_context=_gate()),
        )

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, proof_trail=("proof.alpha",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)


# ---------------------------------------------------------------------------
# Dispatch — exceptions, error pass-through, resteer
# ---------------------------------------------------------------------------

class TestDispatchErrors:
    def test_handler_exception_becomes_internal_error(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            raise RuntimeError("kaboom")

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INTERNAL_ERROR

    def test_handler_validation_error_becomes_input_invalid(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            raise WorkflowValidationError("malformed something")

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_handler_returns_timeout_error_passthrough(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowErrorSummary(
                work_order_id=wo.work_order_id,
                harness=wo.harness,
                failure_kind=WorkflowFailureKind.TIMEOUT,
                summary="hard timeout exceeded",
                partial_outputs=("partial",),
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.TIMEOUT
        assert out.partial_outputs == ("partial",)

    def test_handler_returns_resteer_request_wrapped(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResteerRequest(
                original_work_order_id=wo.work_order_id,
                reason="too broad — narrow allowed_paths",
                suggested_changes=WorkflowResteerChanges(
                    allowed_paths=("src/atlas/",),
                ),
                do_not_retry=False,
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.RESTEER_REQUESTED
        assert out.resteer_request is not None
        assert out.resteer_request.suggested_changes.allowed_paths == (
            "src/atlas/",
        )

    def test_resteer_with_mismatched_original_id_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResteerRequest(
                original_work_order_id="wo-other",
                reason="r",
                suggested_changes=WorkflowResteerChanges(),
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_handler_returns_unsupported_shape(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return "raw transcript text"

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_handler_returns_none(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return None

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID


# ---------------------------------------------------------------------------
# Dispatch — heartbeats stay out of return value
# ---------------------------------------------------------------------------

class TestDispatchHeartbeats:
    def test_sink_receives_monotonic_sequence(self) -> None:
        order = _order()
        seen: list[WorkflowHeartbeat] = []

        def handler(wo, emit):  # noqa: ANN001
            for i in range(3):
                emit(WorkflowHeartbeat(
                    work_order_id=wo.work_order_id,
                    sequence=i,
                    emitted_at=f"2026-06-07T16:21:{i:02d}Z",
                    phase=WorkflowPhase.WORKING,
                    summary=f"step {i}",
                ))
            return _result(wo)

        dispatch_work_order(order, handler, heartbeat_sink=seen.append)
        assert [hb.sequence for hb in seen] == [0, 1, 2]
        assert all(a.sequence < b.sequence for a, b in zip(seen, seen[1:]))

    def test_return_value_has_no_heartbeat_field(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            emit(WorkflowHeartbeat(
                work_order_id=wo.work_order_id,
                sequence=0,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="step",
            ))
            return _result(wo)

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)
        field_names = {f.name for f in dataclasses.fields(out)}
        # Heartbeat history must not be a field on either return shape.
        assert "heartbeats" not in field_names
        assert "heartbeat_history" not in field_names

    def test_error_summary_has_no_heartbeat_field(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            raise RuntimeError("bang")

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        field_names = {f.name for f in dataclasses.fields(out)}
        assert "heartbeats" not in field_names
        assert "heartbeat_history" not in field_names

    def test_mismatched_heartbeat_ignored(self) -> None:
        order = _order()
        seen: list[WorkflowHeartbeat] = []

        def handler(wo, emit):  # noqa: ANN001
            emit(WorkflowHeartbeat(
                work_order_id="wo-other",
                sequence=0,
                emitted_at="2026-06-07T16:21:00Z",
                phase=WorkflowPhase.WORKING,
                summary="not for us",
            ))
            emit(WorkflowHeartbeat(
                work_order_id=wo.work_order_id,
                sequence=0,
                emitted_at="2026-06-07T16:21:01Z",
                phase=WorkflowPhase.WORKING,
                summary="legit",
            ))
            return _result(wo)

        dispatch_work_order(order, handler, heartbeat_sink=seen.append)
        assert len(seen) == 1
        assert seen[0].summary == "legit"

    def test_non_heartbeat_emit_ignored(self) -> None:
        order = _order()
        seen: list[WorkflowHeartbeat] = []

        def handler(wo, emit):  # noqa: ANN001
            emit("raw heartbeat string")  # silently dropped
            emit(None)
            return _result(wo)

        out = dispatch_work_order(order, handler, heartbeat_sink=seen.append)
        assert isinstance(out, WorkflowResultSummary)
        assert seen == []


# ---------------------------------------------------------------------------
# Dispatch — prompt-drag guards on handler return payloads
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class _LeakyOutput:
    transcript: str = "raw chat content"


@dataclasses.dataclass(frozen=True)
class _CleanOutput:
    excerpt_ref: str = "atlas.candidates.0"


class TestPromptDragGuards:
    def test_output_with_forbidden_field_name_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=(_LeakyOutput(),))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_output_dict_with_forbidden_key_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=({"stdout": "dump..."},))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_output_with_unsafe_text_marker_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(
                wo,
                outputs=("BEGIN TRANSCRIPT: raw chat ...",),
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_output_with_filesystem_path_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=("/etc/passwd",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_output_with_list_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=([1, 2, 3],))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_output_with_raw_bytes_rejected(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(wo, outputs=(b"\x00\x01\x02",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_clean_output_accepted(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return _result(
                wo,
                outputs=(_CleanOutput(), {"score": 0.91}, "hit-1"),
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)

    def test_partial_outputs_on_error_also_guarded(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowErrorSummary(
                work_order_id=wo.work_order_id,
                harness=wo.harness,
                failure_kind=WorkflowFailureKind.TIMEOUT,
                summary="timeout",
                partial_outputs=(_LeakyOutput(),),
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        # Leaky partial_outputs are rejected; failure becomes INPUT_INVALID,
        # NOT a silent pass-through with the leak attached.
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_summarize_only_packet_accepted_with_distilled_outputs(self) -> None:
        order = _order(
            input_packet=_packet(allowed_tools=()),  # summarize-only
        )

        def handler(wo, emit):  # noqa: ANN001
            assert wo.input.is_summarize_only is True
            return _result(wo, outputs=("distilled-line-1",))

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowResultSummary)


# ---------------------------------------------------------------------------
# Promotion / acceptance helper
# ---------------------------------------------------------------------------

class TestPromotion:
    def test_tier1_accepted(self) -> None:
        order = _order(risk_tier=1)
        result = _result(order)
        decision = promote_workflow_result(order, result)
        assert isinstance(decision, WorkflowPromotionDecision)
        assert decision.accepted is True
        assert decision.policy_decision_required is False
        assert decision.requires_review_console is False
        assert decision.requires_human_gate is False

    def test_tier2_without_proof_rejected(self) -> None:
        order = _order(
            risk_tier=2, input_packet=_packet(gate_context=_gate()),
        )
        result = _result(order, proof_trail=())
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "proof_trail" in decision.reason

    def test_tier2_without_gate_context_rejected(self) -> None:
        # Repair: tier-2+ promotion requires gate_context, not just proof.
        order = _order(risk_tier=2, input_packet=_packet(gate_context=None))
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "gate_context" in decision.reason
        assert decision.policy_decision_required is True

    def test_tier2_with_allow_policy_accepted(self) -> None:
        order = _order(
            risk_tier=2,
            input_packet=_packet(
                gate_context=WorkflowGateContext(policy_decision="ALLOW"),
            ),
        )
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(order, result)
        assert decision.accepted is True

    def test_tier2_with_warn_policy_rejected(self) -> None:
        order = _order(
            risk_tier=2,
            input_packet=_packet(
                gate_context=WorkflowGateContext(policy_decision="WARN"),
            ),
        )
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "ALLOW" in decision.reason

    def test_tier2_with_deny_policy_rejected(self) -> None:
        order = _order(
            risk_tier=2,
            input_packet=_packet(
                gate_context=WorkflowGateContext(policy_decision="DENY"),
            ),
        )
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "ALLOW" in decision.reason

    def test_tier3_default_signals_rejected(self) -> None:
        # Repair: tier-3+ promotion now requires explicit
        # review_console_pass=True. Default-False blocks acceptance.
        order = _order(
            risk_tier=3,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "review_console_pass" in decision.reason
        assert decision.requires_review_console is True

    def test_tier3_with_review_console_pass_accepted(self) -> None:
        order = _order(
            risk_tier=3,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(order, proof_trail=("p.a",))
        decision = promote_workflow_result(
            order, result, review_console_pass=True,
        )
        assert decision.accepted is True
        assert decision.requires_review_console is True
        assert decision.requires_human_gate is False

    def test_tier4_default_signals_rejected(self) -> None:
        # Repair: tier-4 requires both review_console_pass AND human_approval.
        order = _order(
            risk_tier=4,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(
            order,
            proof_trail=("p.a",),
            requires_human_gate=True,
        )
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False
        assert "review_console_pass" in decision.reason

    def test_tier4_without_result_human_gate_rejected(self) -> None:
        order = _order(
            risk_tier=4,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(
            order,
            proof_trail=("p.a",),
            requires_human_gate=False,
        )
        decision = promote_workflow_result(
            order, result,
            review_console_pass=True,
            human_approval=True,
        )
        assert decision.accepted is False
        assert "requires_human_gate" in decision.reason

    def test_tier4_without_caller_human_approval_rejected(self) -> None:
        order = _order(
            risk_tier=4,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(
            order,
            proof_trail=("p.a",),
            requires_human_gate=True,
        )
        decision = promote_workflow_result(
            order, result,
            review_console_pass=True,
            human_approval=False,
        )
        assert decision.accepted is False
        assert "human_approval" in decision.reason

    def test_tier4_with_all_signals_accepted(self) -> None:
        order = _order(
            risk_tier=4,
            input_packet=_packet(gate_context=_gate()),
        )
        result = _result(
            order,
            proof_trail=("p.a",),
            requires_human_gate=True,
        )
        decision = promote_workflow_result(
            order, result,
            review_console_pass=True,
            human_approval=True,
        )
        assert decision.accepted is True
        assert decision.requires_human_gate is True
        assert decision.requires_review_console is True
        assert decision.policy_decision_required is True

    def test_error_never_promoted(self) -> None:
        order = _order(risk_tier=1)
        error = WorkflowErrorSummary(
            work_order_id=order.work_order_id,
            harness=order.harness,
            failure_kind=WorkflowFailureKind.INTERNAL_ERROR,
            summary="something failed",
        )
        decision = promote_workflow_result(order, error)
        assert decision.accepted is False

    def test_mismatched_id_rejected(self) -> None:
        order_a = _order(work_order_id="wo-a")
        order_b = _order(work_order_id="wo-b")
        result = _result(order_b)
        decision = promote_workflow_result(order_a, result)
        assert decision.accepted is False
        assert "work_order_id" in decision.reason

    def test_non_bool_signal_rejected(self) -> None:
        order = _order(risk_tier=3, input_packet=_packet(gate_context=_gate()))
        result = _result(order, proof_trail=("p.a",))
        with pytest.raises(WorkflowValidationError):
            promote_workflow_result(
                order, result,
                review_console_pass="yes",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# apply_resteer / nesting cap
# ---------------------------------------------------------------------------

class TestApplyResteer:
    def test_empty_changes_produces_equivalent_order(self) -> None:
        order = _order()
        new = apply_resteer(
            order,
            WorkflowResteerChanges(),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.work_order_id == "wo-002"
        assert new.parent_work_order_id == "wo-001"
        assert new.depth == 1
        assert new.harness is order.harness
        assert new.action == order.action

    def test_action_override_applied(self) -> None:
        order = _order()
        new = apply_resteer(
            order,
            WorkflowResteerChanges(action="atlas.narrow"),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.action == "atlas.narrow"

    def test_allowed_paths_overridden(self) -> None:
        order = _order()
        new = apply_resteer(
            order,
            WorkflowResteerChanges(allowed_paths=("src/atlas/",)),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.allowed_paths == ("src/atlas/",)

    def test_lowering_tier_allowed(self) -> None:
        order = _order(risk_tier=3, input_packet=_packet(gate_context=_gate()))
        new = apply_resteer(
            order,
            WorkflowResteerChanges(risk_tier=2),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.risk_tier == 2

    def test_raising_tier_rejected(self) -> None:
        order = _order(risk_tier=2)
        out = apply_resteer(
            order,
            WorkflowResteerChanges(risk_tier=3),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_resteer_at_cap_rejected(self) -> None:
        # Start at depth = cap. A resteer would push depth past the cap.
        parent_order = _order()
        at_cap = apply_resteer(
            parent_order,
            WorkflowResteerChanges(),
            new_work_order_id="wo-d1",
            created_at="2026-06-07T16:31:00Z",
        )
        assert isinstance(at_cap, WorkflowWorkOrder)
        assert at_cap.depth == 1
        at_cap_2 = apply_resteer(
            at_cap,
            WorkflowResteerChanges(),
            new_work_order_id="wo-d2",
            created_at="2026-06-07T16:32:00Z",
        )
        assert isinstance(at_cap_2, WorkflowWorkOrder)
        assert at_cap_2.depth == WORKFLOW_NESTING_CAP
        out = apply_resteer(
            at_cap_2,
            WorkflowResteerChanges(),
            new_work_order_id="wo-d3",
            created_at="2026-06-07T16:33:00Z",
        )
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.INPUT_INVALID

    def test_additional_inputs_appended(self) -> None:
        order = _order(
            input_packet=_packet(
                inputs=(
                    WorkflowInputRecord(source="echo", kind="memory_hit"),
                ),
                allowed_paths=("src/",),
            ),
        )
        new = apply_resteer(
            order,
            WorkflowResteerChanges(
                additional_inputs=(
                    WorkflowInputRecord(
                        source="atlas",
                        kind="file_path",
                        ref="src/main.py",
                    ),
                ),
            ),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert len(new.input.inputs) == 2
        assert new.input.inputs[1].kind == "file_path"

    def test_resteer_empty_allowed_tools_forces_summarize_only(self) -> None:
        # Repair: tuple overrides are tri-state — None means no change,
        # an empty tuple is an explicit override. ``allowed_tools=()``
        # must intentionally flip the new packet into summarize-only mode
        # even though the original packet had tools.
        order = _order(input_packet=_packet(allowed_tools=("read_file",)))
        assert order.input.is_summarize_only is False
        new = apply_resteer(
            order,
            WorkflowResteerChanges(allowed_tools=()),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.allowed_tools == ()
        assert new.input.is_summarize_only is True

    def test_resteer_empty_forbidden_paths_clears_blocklist(self) -> None:
        order = _order(
            input_packet=_packet(
                allowed_paths=("src/",),
                forbidden_paths=("src/secrets",),
            ),
        )
        new = apply_resteer(
            order,
            WorkflowResteerChanges(forbidden_paths=()),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.forbidden_paths == ()
        assert new.input.allowed_paths == ("src/",)

    def test_resteer_empty_allowed_paths_clears_scope(self) -> None:
        # Original packet has no file_path inputs, so clearing
        # allowed_paths is structurally valid (no input refs to invalidate).
        order = _order(
            input_packet=_packet(
                allowed_paths=("src/",),
                forbidden_paths=(),
            ),
        )
        new = apply_resteer(
            order,
            WorkflowResteerChanges(allowed_paths=()),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.allowed_paths == ()

    def test_resteer_none_tuple_fields_passthrough(self) -> None:
        # None means "no change" — original values pass through even when
        # the empty-tuple override pattern exists elsewhere.
        order = _order(
            input_packet=_packet(
                allowed_tools=("read_file",),
                allowed_paths=("src/",),
                forbidden_paths=("src/secrets",),
            ),
        )
        new = apply_resteer(
            order,
            WorkflowResteerChanges(),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.allowed_tools == ("read_file",)
        assert new.input.allowed_paths == ("src/",)
        assert new.input.forbidden_paths == ("src/secrets",)

    def test_resteer_narrow_allowed_paths_to_subdir(self) -> None:
        order = _order(input_packet=_packet(allowed_paths=("src/", "tests/")))
        new = apply_resteer(
            order,
            WorkflowResteerChanges(allowed_paths=("src/atlas/",)),
            new_work_order_id="wo-002",
            created_at="2026-06-07T16:30:00Z",
        )
        assert isinstance(new, WorkflowWorkOrder)
        assert new.input.allowed_paths == ("src/atlas/",)

    def test_resteer_changes_none_default_for_tuple_fields(self) -> None:
        # Construction default for the tri-state tuples must be None.
        changes = WorkflowResteerChanges()
        assert changes.allowed_paths is None
        assert changes.forbidden_paths is None
        assert changes.allowed_tools is None

    def test_resteer_request_do_not_retry_preserved_through_dispatch(self) -> None:
        order = _order()

        def handler(wo, emit):  # noqa: ANN001
            return WorkflowResteerRequest(
                original_work_order_id=wo.work_order_id,
                reason="cannot be done",
                suggested_changes=WorkflowResteerChanges(),
                do_not_retry=True,
            )

        out = dispatch_work_order(order, handler)
        assert isinstance(out, WorkflowErrorSummary)
        assert out.failure_kind is WorkflowFailureKind.RESTEER_REQUESTED
        assert out.resteer_request is not None
        assert out.resteer_request.do_not_retry is True


# ---------------------------------------------------------------------------
# Handler typing — module exports the alias / protocol shape
# ---------------------------------------------------------------------------

class TestExports:
    def test_handler_alias_exists(self) -> None:
        # WorkflowHandler and HandlerReturn are exported for callers building
        # typed harness handlers.
        assert WorkflowHandler is not None
        assert HandlerReturn is not None
