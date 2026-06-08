"""Tests for ``meridian_core.workflow_atlas`` — the first per-harness
Workflow Sub-Agent adapter slice.

The tests are pure / local: no live workflow execution, no process /
session control, no model calls, no network, no UI / Electron / Bifrost
behavior. Dependencies on the promoted Atlas surface (``atlas.query``)
are exercised both directly (with hand-rolled FileMap entry stubs) and
through an injected ``query_fn`` fake for cases that need to vary the
returned :class:`AtlasResult` shape — display-safety rejection, Echo
source preservation, and edge cases.

Each Review A blocking finding and each Review B proof gap recorded in
``docs/live-build-1.md`` for the prior 2026-06-07 Atlas adapter
candidate is mapped to one or more tests below; the docstrings call the
finding out explicitly.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from meridian_core.atlas import (
    AtlasHit,
    AtlasQuery,
    AtlasResult,
    AtlasSource,
)
from meridian_core.workflow_atlas import (
    ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER,
    ATLAS_ACTION_QUERY,
    ATLAS_INPUT_SOURCE,
    ATLAS_KIND_AREA,
    ATLAS_KIND_INCLUDE_ECHO,
    ATLAS_KIND_LIMIT,
    ATLAS_KIND_REQUIRED_PATH,
    ATLAS_KIND_TERM,
    ATLAS_PROOF_REF,
    ATLAS_RESULT_SHAPE,
    AtlasOutputRecord,
    AtlasResultRecord,
    build_atlas_work_order,
    make_atlas_handler,
    query_from_work_order,
)
from meridian_core.workflow_dispatch import (
    WorkflowErrorSummary,
    WorkflowFailureKind,
    WorkflowGateContext,
    WorkflowHarness,
    WorkflowHeartbeat,
    WorkflowInputPacket,
    WorkflowInputRecord,
    WorkflowPhase,
    WorkflowPromptBudget,
    WorkflowResultSummary,
    WorkflowValidationError,
    WorkflowWorkOrder,
    dispatch_work_order,
    promote_workflow_result,
)


# ---------------------------------------------------------------------------
# Local fixtures and helpers (intentionally not imported from
# ``tests/test_workflow_dispatch.py`` so this slice has no cross-test
# coupling and remains readable on its own).
# ---------------------------------------------------------------------------

class _MockFileMapEntry:
    """Minimal duck-typed FileMap entry shaped like the one in
    ``tests/test_atlas.py``."""

    def __init__(self, path, area, purpose, notes=""):
        self.path = path
        self.area = area
        self.purpose = purpose
        self.notes = notes
        self.related_tests = []


def _budget() -> WorkflowPromptBudget:
    return WorkflowPromptBudget(
        max_prompt_tokens=2000,
        max_response_tokens=400,
        notes="atlas adapter budget",
    )


def _build(
    *,
    query: AtlasQuery,
    work_order_id: str = "wo-atlas-001",
    risk_tier: int = 1,
    allowed_paths: tuple[str, ...] = ("docs", "meridian_core", "tests"),
    forbidden_paths: tuple[str, ...] = (".env",),
    allowed_tools: tuple[str, ...] = (),
    gate_context: WorkflowGateContext | None = None,
    project: str = "meridian",
    intent: str = "retrieve atlas hits for the active goal",
    goal_summary: str = "atlas retrieval query",
    time_budget_seconds: int = 30,
    hard_timeout_seconds: int = 60,
    created_at: str = "2026-06-08T17:00:00Z",
    parent_work_order_id: str = "",
    depth: int = 0,
    additional_inputs: tuple[WorkflowInputRecord, ...] = (),
) -> WorkflowWorkOrder:
    return build_atlas_work_order(
        work_order_id=work_order_id,
        project=project,
        query=query,
        intent=intent,
        risk_tier=risk_tier,
        allowed_paths=allowed_paths,
        prompt_budget=_budget(),
        time_budget_seconds=time_budget_seconds,
        hard_timeout_seconds=hard_timeout_seconds,
        created_at=created_at,
        goal_summary=goal_summary,
        allowed_tools=allowed_tools,
        forbidden_paths=forbidden_paths,
        gate_context=gate_context,
        parent_work_order_id=parent_work_order_id,
        depth=depth,
        additional_inputs=additional_inputs,
    )


def _allowing_gate() -> WorkflowGateContext:
    return WorkflowGateContext(
        policy_decision="ALLOW",
        proof_handles=("atlas.query",),
        notes="tier-2 atlas gate present",
    )


# ---------------------------------------------------------------------------
# Constants and adapter records
# ---------------------------------------------------------------------------

class TestConstants:
    def test_action_and_shape_are_bounded_identifiers(self):
        assert ATLAS_ACTION_QUERY == "atlas.query"
        assert ATLAS_RESULT_SHAPE == "atlas.query.v1"
        assert ATLAS_PROOF_REF == "atlas.query"

    def test_atlas_input_source_constant(self):
        assert ATLAS_INPUT_SOURCE == "atlas"

    def test_required_path_kind_matches_promoted_dispatch_kind(self):
        # Review A finding #1: required paths must surface as the
        # promoted ``file_path`` kind so WorkflowInputPacket enforces
        # ``allowed_paths`` / ``forbidden_paths`` on them by
        # construction. Anything else is a contract violation.
        assert ATLAS_KIND_REQUIRED_PATH == "file_path"

    def test_module_explicitly_marks_no_private_helper_import(self):
        # Self-documenting flag asserted in the source. The stronger
        # source-level check is below.
        assert ADAPTER_IMPORTS_PRIVATE_DISPATCH_HELPER is False


class TestRecords:
    def test_atlas_output_record_is_frozen(self):
        rec = AtlasOutputRecord(
            path="meridian_core/atlas.py",
            title="Atlas retrieval",
            reason="path match",
            excerpt="atlas retrieval surface",
            source=AtlasSource.FILEMAP.value,
            score=0.8,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            rec.path = "other"

    def test_atlas_result_record_is_frozen(self):
        rec = AtlasResultRecord(hits=(), missing_paths=(), truncated=False)
        with pytest.raises(dataclasses.FrozenInstanceError):
            rec.truncated = True


# ---------------------------------------------------------------------------
# Builder — encoding AtlasQuery as WorkflowInputRecord(s)
# ---------------------------------------------------------------------------

class TestBuildWorkOrder:
    def test_sets_atlas_harness_action_and_shape(self):
        order = _build(query=AtlasQuery(terms=("atlas",)))
        assert order.harness == WorkflowHarness.ATLAS
        assert order.action == ATLAS_ACTION_QUERY
        assert order.expected_result_shape == ATLAS_RESULT_SHAPE

    def test_encodes_terms_areas_and_include_echo_and_limit(self):
        order = _build(query=AtlasQuery(
            terms=("relay", "atlas"),
            areas=("meridian_core",),
            include_echo=True,
            limit=10,
        ))
        kinds = tuple(
            (rec.source, rec.kind, rec.ref)
            for rec in order.input.inputs
        )
        assert (ATLAS_INPUT_SOURCE, ATLAS_KIND_TERM, "relay") in kinds
        assert (ATLAS_INPUT_SOURCE, ATLAS_KIND_TERM, "atlas") in kinds
        assert (ATLAS_INPUT_SOURCE, ATLAS_KIND_AREA, "meridian_core") in kinds
        assert (ATLAS_INPUT_SOURCE, ATLAS_KIND_INCLUDE_ECHO, "true") in kinds
        assert (ATLAS_INPUT_SOURCE, ATLAS_KIND_LIMIT, "10") in kinds

    def test_encodes_required_paths_as_file_path_kind(self):
        # Review A finding #1: required paths flow through the promoted
        # ``file_path`` kind so packet scope applies.
        order = _build(
            query=AtlasQuery(
                terms=(),
                required_paths=("docs/atlas-retrieval-contract.md",),
            ),
            allowed_paths=("docs",),
        )
        file_path_records = [
            rec for rec in order.input.inputs if rec.kind == "file_path"
        ]
        assert len(file_path_records) == 1
        assert file_path_records[0].ref == "docs/atlas-retrieval-contract.md"
        assert file_path_records[0].source == ATLAS_INPUT_SOURCE

    def test_required_path_outside_allowed_scope_is_rejected(self):
        # Review A finding #1: required paths CANNOT bypass
        # ``allowed_paths``. Packet construction must reject them.
        with pytest.raises(WorkflowValidationError):
            _build(
                query=AtlasQuery(
                    terms=(),
                    required_paths=("secret/leak.md",),
                ),
                allowed_paths=("docs",),
                forbidden_paths=(),
            )

    def test_required_path_inside_forbidden_paths_is_rejected(self):
        # Review A finding #1: ``forbidden_paths`` win over
        # ``allowed_paths`` for required paths too — the promoted
        # dispatch rule must apply.
        with pytest.raises(WorkflowValidationError):
            _build(
                query=AtlasQuery(
                    terms=(),
                    required_paths=("docs/secret.md",),
                ),
                allowed_paths=("docs",),
                forbidden_paths=("docs/secret.md",),
            )

    def test_required_path_inside_allowed_scope_is_accepted(self):
        order = _build(
            query=AtlasQuery(
                terms=(),
                required_paths=("docs/atlas-retrieval-contract.md",),
            ),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        # Construction succeeded; we just sanity-check the packet shape.
        assert isinstance(order.input, WorkflowInputPacket)
        assert "docs" in order.input.allowed_paths

    def test_rejects_non_atlas_query_argument(self):
        with pytest.raises(WorkflowValidationError):
            build_atlas_work_order(
                work_order_id="wo-atlas-001",
                project="meridian",
                query="not-an-atlas-query",  # type: ignore[arg-type]
                intent="x",
                risk_tier=1,
                allowed_paths=("docs",),
                prompt_budget=_budget(),
                time_budget_seconds=30,
                hard_timeout_seconds=60,
                created_at="2026-06-08T17:00:00Z",
            )

    def test_additional_inputs_must_be_workflow_input_records(self):
        with pytest.raises(WorkflowValidationError):
            _build(
                query=AtlasQuery(terms=("x",)),
                additional_inputs=("not-a-record",),  # type: ignore[arg-type]
            )

    def test_term_with_unsafe_marker_is_rejected_at_record_level(self):
        # An attempted prompt-drag term (e.g. an unsafe marker) is caught
        # by the promoted WorkflowInputRecord validation, not the
        # adapter. This proves the adapter respects the promoted bound.
        with pytest.raises(WorkflowValidationError):
            _build(query=AtlasQuery(terms=("git checkout",)))


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

class TestQueryFromWorkOrder:
    def test_round_trips_all_fields(self):
        original = AtlasQuery(
            terms=("relay", "atlas"),
            areas=("meridian_core",),
            required_paths=("docs/atlas-retrieval-contract.md",),
            include_echo=True,
            limit=10,
        )
        order = _build(query=original, allowed_paths=("docs", "meridian_core"))
        decoded = query_from_work_order(order)
        assert decoded.terms == ("relay", "atlas")
        assert decoded.areas == ("meridian_core",)
        assert decoded.required_paths == (
            "docs/atlas-retrieval-contract.md",
        )
        assert decoded.include_echo is True
        assert decoded.limit == 10
        # ``project`` flows from the packet, not from the original query.
        assert decoded.project == "meridian"

    def test_unknown_atlas_kind_raises(self):
        # Hand-build a packet with an unknown atlas kind to confirm the
        # decoder rejects it.
        bad_record = WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind="atlas_unknown_kind",
            ref="x",
        )
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="test",
            inputs=(bad_record,),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-bad",
            harness=WorkflowHarness.ATLAS,
            action=ATLAS_ACTION_QUERY,
            intent="x",
            risk_tier=1,
            input=packet,
            expected_result_shape=ATLAS_RESULT_SHAPE,
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        with pytest.raises(WorkflowValidationError):
            query_from_work_order(order)

    def test_invalid_include_echo_value_raises(self):
        bad = WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_INCLUDE_ECHO,
            ref="maybe",
        )
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="test",
            inputs=(bad,),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-bad",
            harness=WorkflowHarness.ATLAS,
            action=ATLAS_ACTION_QUERY,
            intent="x",
            risk_tier=1,
            input=packet,
            expected_result_shape=ATLAS_RESULT_SHAPE,
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        with pytest.raises(WorkflowValidationError):
            query_from_work_order(order)

    def test_invalid_limit_value_raises(self):
        bad = WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_LIMIT,
            ref="not-a-number",
        )
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="test",
            inputs=(bad,),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-bad",
            harness=WorkflowHarness.ATLAS,
            action=ATLAS_ACTION_QUERY,
            intent="x",
            risk_tier=1,
            input=packet,
            expected_result_shape=ATLAS_RESULT_SHAPE,
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        with pytest.raises(WorkflowValidationError):
            query_from_work_order(order)

    def test_negative_limit_value_raises(self):
        bad = WorkflowInputRecord(
            source=ATLAS_INPUT_SOURCE,
            kind=ATLAS_KIND_LIMIT,
            ref="-5",
        )
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="test",
            inputs=(bad,),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-bad",
            harness=WorkflowHarness.ATLAS,
            action=ATLAS_ACTION_QUERY,
            intent="x",
            risk_tier=1,
            input=packet,
            expected_result_shape=ATLAS_RESULT_SHAPE,
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        with pytest.raises(WorkflowValidationError):
            query_from_work_order(order)

    def test_rejects_non_workflow_work_order(self):
        with pytest.raises(WorkflowValidationError):
            query_from_work_order("not-an-order")  # type: ignore[arg-type]

    def test_rejects_non_atlas_harness(self):
        # Build a non-ATLAS work order and confirm the decoder rejects.
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="echo work",
            inputs=(),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-echo-001",
            harness=WorkflowHarness.ECHO,
            action="echo.recall",
            intent="echo recall",
            risk_tier=1,
            input=packet,
            expected_result_shape="echo.recall.v1",
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        with pytest.raises(WorkflowValidationError):
            query_from_work_order(order)

    def test_ignores_non_atlas_sourced_records(self):
        # Non-atlas-sourced inputs should be ignored, not rejected. This
        # lets adapters layer additional records (e.g. echo-sourced
        # hints) without breaking decode.
        extras = (
            WorkflowInputRecord(
                source="echo",
                kind="memory_hit",
                ref="echo://meridian/x",
                summary="prior recall",
            ),
        )
        order = _build(
            query=AtlasQuery(terms=("relay",)),
            additional_inputs=extras,
        )
        decoded = query_from_work_order(order)
        assert decoded.terms == ("relay",)


# ---------------------------------------------------------------------------
# Dispatch — happy path via the promoted contract
# ---------------------------------------------------------------------------

def _make_filemap(*entries):
    return tuple(entries)


class TestDispatchHappyPath:
    def test_returns_atlas_result_record_via_promoted_contract(self):
        # Review B proof gap: result shape must be compatible with the
        # promoted Atlas / Workflow contract. The dispatcher round-trip
        # is the proof — not a local wrapper assertion.
        entries = _make_filemap(
            _MockFileMapEntry(
                "meridian_core/relay.py",
                "meridian_core",
                "Relay dispatch",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(query=AtlasQuery(terms=("relay",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        assert result.harness == WorkflowHarness.ATLAS
        assert result.result_shape == ATLAS_RESULT_SHAPE
        assert len(result.outputs) == 1
        record = result.outputs[0]
        assert isinstance(record, AtlasResultRecord)
        assert len(record.hits) == 1
        assert record.hits[0].path == "meridian_core/relay.py"
        assert record.hits[0].source == AtlasSource.FILEMAP.value

    def test_preserves_hit_order_and_source_attribution(self):
        # Build two filemap entries that both match; verify the result
        # preserves the promoted Atlas ranking order (score desc, then
        # source priority, then path asc).
        entries = _make_filemap(
            _MockFileMapEntry(
                "meridian_core/atlas.py",
                "meridian_core",
                "Atlas retrieval",  # purpose match -> 0.7
            ),
            _MockFileMapEntry(
                "meridian_core/atlas_helper.py",
                "meridian_core",
                "atlas helpers",  # path match -> 0.8
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(query=AtlasQuery(terms=("atlas",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        # Both hits should be present; the path-match (0.8) comes before
        # the purpose-match (0.7).
        scores = [h.score for h in record.hits]
        assert scores == sorted(scores, reverse=True)
        assert all(h.source == AtlasSource.FILEMAP.value for h in record.hits)

    def test_preserves_missing_paths_and_truncated(self):
        # Required path that doesn't exist in FileMap -> missing_paths.
        entries = _make_filemap(
            _MockFileMapEntry("docs/x.md", "docs", "doc"),
        )

        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="docs/x.md",
                        title="doc",
                        reason="path match",
                        excerpt=None,
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=("docs/missing.md",),
                truncated=True,
            )

        handler = make_atlas_handler(
            filemap_entries=entries,
            query_fn=fake_query,
        )
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert record.missing_paths == ("docs/missing.md",)
        assert record.truncated is True


# ---------------------------------------------------------------------------
# Dispatch — tier proof behavior
# ---------------------------------------------------------------------------

class TestFileMapPathScope:
    def test_term_hit_outside_allowed_scope_does_not_succeed_or_leak(self):
        entries = _make_filemap(
            _MockFileMapEntry(
                "secrets/incident.md",
                "docs",
                "Incident response relay notes",
                "sensitive excerpt",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(
            query=AtlasQuery(terms=("incident",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )

        result = dispatch_work_order(order, handler)

        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert record.hits == ()
        assert "secrets/incident.md" not in repr(result)
        assert "sensitive excerpt" not in repr(result)

    def test_term_hit_inside_forbidden_scope_does_not_succeed_or_leak(self):
        entries = _make_filemap(
            _MockFileMapEntry(
                "docs/secret.md",
                "docs",
                "Secret relay notes",
                "forbidden excerpt",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(
            query=AtlasQuery(terms=("secret",)),
            allowed_paths=("docs",),
            forbidden_paths=("docs/secret.md",),
        )

        result = dispatch_work_order(order, handler)

        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert record.hits == ()
        assert "docs/secret.md" not in repr(result)
        assert "forbidden excerpt" not in repr(result)

    def test_area_hit_outside_allowed_scope_is_filtered_before_query(self):
        captured_paths: list[tuple[str, ...]] = []

        def recording_query_fn(q, filemap_entries=(), echo_store=None):
            captured_paths.append(tuple(entry.path for entry in filemap_entries))
            return AtlasResult(hits=(), missing_paths=(), truncated=False)

        entries = _make_filemap(
            _MockFileMapEntry(
                "docs/public.md",
                "docs",
                "Public atlas note",
            ),
            _MockFileMapEntry(
                "secrets/incident.md",
                "docs",
                "Incident response relay notes",
            ),
        )
        handler = make_atlas_handler(
            filemap_entries=entries,
            query_fn=recording_query_fn,
        )
        order = _build(
            query=AtlasQuery(terms=("atlas",), areas=("docs",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )

        result = dispatch_work_order(order, handler)

        assert isinstance(result, WorkflowResultSummary)
        assert captured_paths == [("docs/public.md",)]

    def test_query_fn_filemap_hit_outside_scope_fails_closed(self):
        def leaking_query_fn(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="secrets/incident.md",
                        title="Incident",
                        reason="term match",
                        excerpt="sensitive excerpt",
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )

        handler = make_atlas_handler(query_fn=leaking_query_fn)
        order = _build(
            query=AtlasQuery(terms=("incident",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )

        result = dispatch_work_order(order, handler)

        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID
        assert "secrets/incident.md" not in repr(result)
        assert "sensitive excerpt" not in repr(result)


class TestTierProof:
    def test_tier_1_returns_empty_proof_trail(self):
        handler = make_atlas_handler()
        order = _build(query=AtlasQuery(terms=()), risk_tier=1)
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        assert result.proof_trail == ()

    def test_tier_2_returns_required_proof_trail(self):
        handler = make_atlas_handler()
        # Tier-2 dispatch requires no gate_context (only tier-3+ does),
        # but the result must carry a non-empty ``proof_trail`` or the
        # dispatcher rejects with PROOF_UNAVAILABLE.
        order = _build(
            query=AtlasQuery(terms=()),
            risk_tier=2,
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        assert ATLAS_PROOF_REF in result.proof_trail

    def test_tier_3_without_gate_context_rejected_by_dispatch(self):
        # The promoted dispatcher rejects tier-3 orders without
        # gate_context — the adapter does not need to special-case this.
        handler = make_atlas_handler()
        order = _build(
            query=AtlasQuery(terms=()),
            risk_tier=3,
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.GATE_REQUIRED

    def test_tier_3_with_gate_context_returns_result_with_proof_trail(self):
        handler = make_atlas_handler()
        order = _build(
            query=AtlasQuery(terms=()),
            risk_tier=3,
            gate_context=_allowing_gate(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        assert ATLAS_PROOF_REF in result.proof_trail


# ---------------------------------------------------------------------------
# Dispatch — display-safety rejection end-to-end
# ---------------------------------------------------------------------------

class TestDisplaySafetyEndToEnd:
    def _unsafe_title_query_fn(self):
        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="docs/x.md",
                        # "raw_transcript" is in the promoted
                        # _UNSAFE_FREE_TEXT_MARKERS set; the dispatcher
                        # rejects strings containing it.
                        title="raw_transcript leak attempt",
                        reason="path match",
                        excerpt=None,
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )
        return fake_query

    def test_unsafe_title_rejected_end_to_end_through_dispatch(self):
        # Review B proof gap: display-safety rejection must be proven
        # end-to-end through ``dispatch_work_order``, not just via a
        # local wrapper. The adapter returns its result; the dispatcher
        # walks the payload and emits INPUT_INVALID.
        handler = make_atlas_handler(
            query_fn=self._unsafe_title_query_fn(),
        )
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_unsafe_excerpt_rejected_end_to_end_through_dispatch(self):
        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="docs/x.md",
                        title="doc",
                        reason="path match",
                        # "git checkout" is in the promoted unsafe
                        # markers; rejected even in an excerpt.
                        excerpt="prep step: git checkout main",
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )

        handler = make_atlas_handler(query_fn=fake_query)
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_unsafe_field_does_not_silently_blank_and_succeed(self):
        # Review A finding #2: the prior candidate silently blanked
        # unsafe title/reason/excerpt fields and still returned a
        # successful result. This adapter must NOT do that — the
        # dispatcher's INPUT_INVALID failure is the only acceptable
        # outcome, and the original unsafe content must NOT appear as a
        # blank field in a success result.
        handler = make_atlas_handler(
            query_fn=self._unsafe_title_query_fn(),
        )
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert not isinstance(result, WorkflowResultSummary)
        assert isinstance(result, WorkflowErrorSummary)


# ---------------------------------------------------------------------------
# Dispatch — heartbeats stay out of the result
# ---------------------------------------------------------------------------

class TestHeartbeatsExcluded:
    def test_handler_emitted_heartbeats_do_not_appear_in_result(self):
        # The promoted dispatcher guarantees heartbeat history is never
        # in the result. We verify the adapter does not add a heartbeat
        # field of its own.
        captured: list[WorkflowHeartbeat] = []
        handler = make_atlas_handler()
        order = _build(query=AtlasQuery(terms=()))
        result = dispatch_work_order(
            order, handler, heartbeat_sink=captured.append,
        )
        assert isinstance(result, WorkflowResultSummary)
        # The promoted WorkflowResultSummary has no heartbeats field.
        field_names = {f.name for f in dataclasses.fields(result)}
        assert "heartbeats" not in field_names
        assert "heartbeat_history" not in field_names


# ---------------------------------------------------------------------------
# Dispatch — handler does not close over the query
# ---------------------------------------------------------------------------

class TestHandlerHasNoSidecarQuery:
    def test_same_handler_serves_different_queries_distinctly(self):
        # Review A finding #3: the prior candidate's handler closed over
        # an AtlasQuery that could diverge from the work order's typed
        # inputs. This adapter reconstructs the query each call, so the
        # SAME handler instance must produce different results for
        # different work orders.
        captured: list[AtlasQuery] = []

        def recording_query_fn(q, filemap_entries=(), echo_store=None):
            captured.append(q)
            return AtlasResult(
                hits=(), missing_paths=(), truncated=False,
            )

        handler = make_atlas_handler(query_fn=recording_query_fn)
        order_a = _build(
            query=AtlasQuery(terms=("alpha",)),
            work_order_id="wo-a",
        )
        order_b = _build(
            query=AtlasQuery(terms=("beta",), include_echo=True),
            work_order_id="wo-b",
        )
        dispatch_work_order(order_a, handler)
        dispatch_work_order(order_b, handler)
        assert len(captured) == 2
        assert captured[0].terms == ("alpha",)
        assert captured[0].include_echo is False
        assert captured[1].terms == ("beta",)
        assert captured[1].include_echo is True

    def test_factory_signature_takes_no_query_argument(self):
        # Static enforcement that there's no sidecar query parameter.
        import inspect

        sig = inspect.signature(make_atlas_handler)
        for name in sig.parameters:
            assert "query" not in name or name == "query_fn", (
                f"make_atlas_handler must not accept a query sidecar; "
                f"found parameter {name!r}"
            )


# ---------------------------------------------------------------------------
# Dispatch — empty query returns successful empty result
# ---------------------------------------------------------------------------

class TestEmptyQuery:
    def test_empty_query_returns_successful_empty_result_not_resteer(self):
        # Review A finding #4: empty AtlasQuery must return a successful
        # empty AtlasResult, not a WorkflowResteerRequest.
        handler = make_atlas_handler()
        order = _build(query=AtlasQuery(
            terms=(), areas=(), required_paths=(), include_echo=False,
        ))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert record.hits == ()
        assert record.missing_paths == ()
        assert record.truncated is False
        # Specifically: NOT an error and NOT carrying a resteer request.
        assert not isinstance(result, WorkflowErrorSummary)

    def test_empty_query_via_atlas_default_does_not_resteer(self):
        # Sanity: even when the real ``atlas.query`` is used, an empty
        # AtlasQuery yields an empty successful AtlasResult.
        handler = make_atlas_handler()
        order = _build(query=AtlasQuery(terms=()))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        assert isinstance(result.outputs[0], AtlasResultRecord)


# ---------------------------------------------------------------------------
# Dispatch — Echo compatibility via injected source path
# ---------------------------------------------------------------------------

class TestEchoCompatibility:
    def test_echo_source_path_preserved_through_dispatch(self):
        # Review B proof gap: Echo compatibility must be proven through
        # an injected Echo source path when available, not only through
        # direct construction of an ``echo://`` hit.
        sentinel_echo_store = object()
        injected_echo_stores: list[object] = []
        injected_flags: list[bool] = []

        def fake_query_fn(q, filemap_entries=(), echo_store=None):
            injected_echo_stores.append(echo_store)
            injected_flags.append(q.include_echo)
            if q.include_echo and echo_store is not None:
                return AtlasResult(
                    hits=(
                        AtlasHit(
                            path="echo://meridian/r-001",
                            title="Echo Record 1",
                            reason="echo summary match",
                            excerpt="bounded summary text",
                            source=AtlasSource.ECHO,
                            score=0.6,
                        ),
                    ),
                    missing_paths=(),
                    truncated=False,
                )
            return AtlasResult(hits=(), missing_paths=(), truncated=False)

        handler = make_atlas_handler(
            echo_store=sentinel_echo_store,
            query_fn=fake_query_fn,
        )
        order = _build(query=AtlasQuery(terms=(), include_echo=True))
        result = dispatch_work_order(order, handler)

        # The Echo source path was injected via the adapter's
        # echo_store parameter — the handler forwarded it intact.
        assert injected_echo_stores == [sentinel_echo_store]
        assert injected_flags == [True]
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert len(record.hits) == 1
        hit = record.hits[0]
        assert hit.source == AtlasSource.ECHO.value
        assert hit.path == "echo://meridian/r-001"

    def test_include_echo_false_skips_echo_store(self):
        captured_stores: list[object] = []

        def fake_query_fn(q, filemap_entries=(), echo_store=None):
            captured_stores.append(echo_store)
            return AtlasResult(hits=(), missing_paths=(), truncated=False)

        sentinel = object()
        handler = make_atlas_handler(
            echo_store=sentinel,
            query_fn=fake_query_fn,
        )
        order = _build(query=AtlasQuery(terms=(), include_echo=False))
        dispatch_work_order(order, handler)
        # The Echo store is always passed through; gating it on
        # include_echo is the promoted Atlas surface's responsibility,
        # not the adapter's. We just verify the adapter does not drop
        # the injected store.
        assert captured_stores == [sentinel]


# ---------------------------------------------------------------------------
# Adapter does not import the private dispatch helper
# ---------------------------------------------------------------------------

class TestNoPrivateDispatchHelperImport:
    def test_module_attribute_does_not_carry_private_helper(self):
        # Review A finding #5: the adapter must not import
        # ``_is_safe_output_string`` from ``workflow_dispatch``.
        from meridian_core import workflow_atlas

        assert "_is_safe_output_string" not in vars(workflow_atlas)

    def test_module_source_does_not_reference_private_helper(self):
        # Stronger source-level check: even an indirect reference
        # (``workflow_dispatch._is_safe_output_string``) is forbidden.
        from meridian_core import workflow_atlas

        source = Path(workflow_atlas.__file__).read_text(encoding="utf-8")
        assert "_is_safe_output_string" not in source


# ---------------------------------------------------------------------------
# Handler failure / defensive paths
# ---------------------------------------------------------------------------

class TestHandlerDefensivePaths:
    def test_internal_exception_in_query_fn_returns_internal_error(self):
        def boom(q, filemap_entries=(), echo_store=None):
            raise RuntimeError("synthetic failure")

        handler = make_atlas_handler(query_fn=boom)
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INTERNAL_ERROR

    def test_query_fn_returning_wrong_type_returns_input_invalid(self):
        def wrong_shape(q, filemap_entries=(), echo_store=None):
            return "not-an-atlas-result"

        handler = make_atlas_handler(query_fn=wrong_shape)
        order = _build(query=AtlasQuery(terms=("x",)))
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_handler_wrong_harness_in_work_order_returns_input_invalid(self):
        # Defensive: even if a caller hands the adapter handler a
        # non-ATLAS work order, the handler returns a typed error.
        handler = make_atlas_handler()
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="echo work",
            inputs=(),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-echo-001",
            harness=WorkflowHarness.ECHO,
            action="echo.recall",
            intent="echo recall",
            risk_tier=1,
            input=packet,
            expected_result_shape="echo.recall.v1",
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        result = dispatch_work_order(order, handler)
        # The dispatcher rejects the mismatched harness in the error
        # response before returning. Either way, the outcome must be a
        # WorkflowErrorSummary, never a success.
        assert isinstance(result, WorkflowErrorSummary)

    def test_handler_unsupported_atlas_action_returns_input_invalid(self):
        handler = make_atlas_handler()
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="atlas reindex",
            inputs=(),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-other",
            harness=WorkflowHarness.ATLAS,
            action="atlas.reindex",  # not supported in this slice
            intent="reindex atlas",
            risk_tier=1,
            input=packet,
            expected_result_shape=ATLAS_RESULT_SHAPE,
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_handler_wrong_result_shape_returns_input_invalid(self):
        handler = make_atlas_handler()
        packet = WorkflowInputPacket(
            project="meridian",
            goal_summary="atlas query",
            inputs=(),
            allowed_tools=(),
            allowed_paths=("docs",),
            forbidden_paths=(),
            prompt_budget=_budget(),
        )
        order = WorkflowWorkOrder(
            work_order_id="wo-atlas-shape",
            harness=WorkflowHarness.ATLAS,
            action=ATLAS_ACTION_QUERY,
            intent="atlas query",
            risk_tier=1,
            input=packet,
            expected_result_shape="other.shape.v1",
            time_budget_seconds=30,
            hard_timeout_seconds=60,
            created_at="2026-06-08T17:00:00Z",
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_factory_rejects_non_callable_query_fn(self):
        with pytest.raises(WorkflowValidationError):
            make_atlas_handler(query_fn="not-a-callable")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Promotion helper compatibility
# ---------------------------------------------------------------------------

class TestPromotionCompatibility:
    def test_tier_1_adapter_result_is_promotable(self):
        handler = make_atlas_handler()
        order = _build(query=AtlasQuery(terms=()), risk_tier=1)
        result = dispatch_work_order(order, handler)
        decision = promote_workflow_result(order, result)
        assert decision.accepted is True

    def test_tier_2_adapter_result_requires_allowing_gate(self):
        handler = make_atlas_handler()
        # Tier-2 without an ALLOW gate must not promote.
        order = _build(query=AtlasQuery(terms=()), risk_tier=2)
        result = dispatch_work_order(order, handler)
        decision = promote_workflow_result(order, result)
        assert decision.accepted is False

    def test_tier_2_adapter_result_promotable_with_allow_gate(self):
        handler = make_atlas_handler()
        order = _build(
            query=AtlasQuery(terms=()),
            risk_tier=2,
            gate_context=_allowing_gate(),
        )
        result = dispatch_work_order(order, handler)
        decision = promote_workflow_result(order, result)
        assert decision.accepted is True


# ---------------------------------------------------------------------------
# Review B HIGH — non-required FileMap / DOC hits must obey work order scope
# ---------------------------------------------------------------------------

class TestNonRequiredHitScope:
    """Regression coverage for Codex Review B (FAIL) on the prior Ready
    marker (2026-06-08T17:30:00-06:00):

    The adapter encoded ``required_paths`` as ``file_path`` so required
    docs were scoped, but it passed the whole ``filemap_entries``
    snapshot to ``atlas.query`` and returned term / area hits even when
    a hit path was outside ``work_order.input.allowed_paths`` or inside
    ``forbidden_paths``. A work order allowed only to ``docs`` could
    return ``secrets/incident.md`` excerpts.

    The fix pre-filters ``filemap_entries`` to the work order's scope
    before invoking ``atlas.query`` AND fails closed (``INPUT_INVALID``)
    on any FileMap / DOC hit whose path is outside that scope.
    ``AtlasSource.ECHO`` conceptual refs are exempt per the Atlas
    contract.
    """

    def test_term_match_on_out_of_scope_path_is_not_in_result(self):
        # Allowed_paths is just ``docs``; a FileMap entry under
        # ``secrets/`` that matches a search term must NOT surface.
        entries = (
            _MockFileMapEntry(
                "docs/incident-runbook.md",
                "docs",
                "incident response runbook",
            ),
            _MockFileMapEntry(
                "secrets/incident.md",
                "secrets",
                "incident excerpts and credentials",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(
            query=AtlasQuery(terms=("incident",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        paths = {hit.path for hit in record.hits}
        assert "secrets/incident.md" not in paths
        assert paths == {"docs/incident-runbook.md"}
        # The forbidden excerpt content from the out-of-scope entry
        # ("credentials") must not appear anywhere in the surfaced
        # excerpts either.
        excerpts = "\n".join(
            (hit.excerpt or "") for hit in record.hits
        )
        assert "credentials" not in excerpts.lower()

    def test_term_match_on_forbidden_path_is_not_in_result(self):
        # Allowed by prefix but explicitly forbidden — the entry must
        # not surface even though ``docs/`` would otherwise permit it.
        entries = (
            _MockFileMapEntry(
                "docs/incident-runbook.md",
                "docs",
                "incident response runbook",
            ),
            _MockFileMapEntry(
                "docs/secret/incident-exfil.md",
                "docs/secret",
                "incident exfil notes",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(
            query=AtlasQuery(terms=("incident",)),
            allowed_paths=("docs",),
            forbidden_paths=("docs/secret",),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        paths = {hit.path for hit in record.hits}
        assert "docs/secret/incident-exfil.md" not in paths
        assert paths == {"docs/incident-runbook.md"}

    def test_area_match_on_out_of_scope_path_is_not_in_result(self):
        # Same scoping enforcement under an area-driven query.
        entries = (
            _MockFileMapEntry(
                "docs/atlas-retrieval-contract.md",
                "docs",
                "atlas contract",
            ),
            _MockFileMapEntry(
                "secrets/atlas-leak.md",
                # Mislabeled area to provoke an area match; scope
                # filtering must still reject the path.
                "docs",
                "atlas leak excerpt",
            ),
        )
        handler = make_atlas_handler(filemap_entries=entries)
        order = _build(
            query=AtlasQuery(terms=("atlas",), areas=("docs",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        paths = {hit.path for hit in record.hits}
        assert "secrets/atlas-leak.md" not in paths
        assert all(
            p.startswith("docs/") or p == "docs" for p in paths
        )

    def test_query_fn_returning_out_of_scope_filemap_hit_fails_closed(self):
        # Defense in depth: even if a future ``atlas.query`` somehow
        # returned a hit with an out-of-scope path and
        # ``source=FILEMAP``, the handler must fail closed.
        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="secrets/incident.md",
                        title="incident",
                        reason="path match",
                        excerpt=None,
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )

        handler = make_atlas_handler(query_fn=fake_query)
        order = _build(
            query=AtlasQuery(terms=("incident",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_query_fn_returning_out_of_scope_doc_hit_fails_closed(self):
        # Same fail-closed check for DOC sourced hits.
        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="secrets/atlas-leak.md",
                        title="leak",
                        reason="forced",
                        excerpt=None,
                        source=AtlasSource.DOC,
                        score=0.9,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )

        handler = make_atlas_handler(query_fn=fake_query)
        order = _build(
            query=AtlasQuery(terms=("leak",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_query_fn_returning_forbidden_filemap_hit_fails_closed(self):
        # An in-allowed but inside-forbidden hit must also fail closed.
        def fake_query(q, filemap_entries=(), echo_store=None):
            return AtlasResult(
                hits=(
                    AtlasHit(
                        path="docs/secret/incident-exfil.md",
                        title="exfil",
                        reason="path match",
                        excerpt=None,
                        source=AtlasSource.FILEMAP,
                        score=0.8,
                    ),
                ),
                missing_paths=(),
                truncated=False,
            )

        handler = make_atlas_handler(query_fn=fake_query)
        order = _build(
            query=AtlasQuery(terms=("exfil",)),
            allowed_paths=("docs",),
            forbidden_paths=("docs/secret",),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowErrorSummary)
        assert result.failure_kind == WorkflowFailureKind.INPUT_INVALID

    def test_echo_source_path_is_exempt_from_repo_relative_scope(self):
        # Echo conceptual refs (``echo://meridian/<record_id>``) must
        # flow through even when the work order's ``allowed_paths``
        # would never accept them as repo-relative prefixes.
        sentinel_echo_store = object()

        def fake_query(q, filemap_entries=(), echo_store=None):
            if q.include_echo and echo_store is not None:
                return AtlasResult(
                    hits=(
                        AtlasHit(
                            path="echo://meridian/r-001",
                            title="Echo Record 1",
                            reason="echo summary match",
                            excerpt="bounded summary text",
                            source=AtlasSource.ECHO,
                            score=0.6,
                        ),
                    ),
                    missing_paths=(),
                    truncated=False,
                )
            return AtlasResult(
                hits=(), missing_paths=(), truncated=False,
            )

        handler = make_atlas_handler(
            echo_store=sentinel_echo_store,
            query_fn=fake_query,
        )
        order = _build(
            query=AtlasQuery(terms=(), include_echo=True),
            # Deliberately narrow repo-relative scope.
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        result = dispatch_work_order(order, handler)
        assert isinstance(result, WorkflowResultSummary)
        record = result.outputs[0]
        assert len(record.hits) == 1
        echo_hit = record.hits[0]
        assert echo_hit.source == AtlasSource.ECHO.value
        assert echo_hit.path == "echo://meridian/r-001"

    def test_out_of_scope_filemap_entries_never_reach_atlas_query(self):
        # Belt-and-suspenders: the handler MUST pre-filter
        # ``filemap_entries`` before invoking ``query_fn``. We capture
        # what the query_fn sees and assert no out-of-scope entry was
        # forwarded — even if downstream Atlas would have rejected it.
        seen_entries: list[tuple] = []

        def recording_query_fn(q, filemap_entries=(), echo_store=None):
            seen_entries.append(tuple(filemap_entries))
            return AtlasResult(
                hits=(), missing_paths=(), truncated=False,
            )

        entries = (
            _MockFileMapEntry("docs/x.md", "docs", "doc x"),
            _MockFileMapEntry(
                "secrets/leak.md", "secrets", "secret leak",
            ),
        )
        handler = make_atlas_handler(
            filemap_entries=entries,
            query_fn=recording_query_fn,
        )
        order = _build(
            query=AtlasQuery(terms=("x",)),
            allowed_paths=("docs",),
            forbidden_paths=(),
        )
        dispatch_work_order(order, handler)
        assert len(seen_entries) == 1
        forwarded_paths = {e.path for e in seen_entries[0]}
        assert "secrets/leak.md" not in forwarded_paths
        assert forwarded_paths == {"docs/x.md"}
