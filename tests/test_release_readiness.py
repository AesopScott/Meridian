"""Tests for V2.5 internal release readiness packaging proof."""

from __future__ import annotations

from meridian_core.release_readiness import (
    ProofPackageEvidence,
    ProofPackageStatus,
    ReleaseReadinessClassification,
    RollbackGate,
    RollbackGateState,
    build_release_readiness_snapshot,
)


NOW = 10_000


def _proof(
    requirement: str = "backend pytest proof",
    *,
    captured_at_seconds: int | None = NOW - 60,
    max_age_seconds: int = 600,
    content_digest: str = "sha256:abc123",
    present: bool = True,
) -> ProofPackageEvidence:
    return ProofPackageEvidence(
        proof_ref=f"proof:{requirement.replace(' ', '-')}",
        requirement=requirement,
        captured_at_seconds=captured_at_seconds,
        max_age_seconds=max_age_seconds,
        content_digest=content_digest,
        present=present,
    )


def _closed_gate(label: str = "rollback plan reviewed") -> RollbackGate:
    return RollbackGate(
        gate_id=f"rollback:{label.replace(' ', '-')}",
        label=label,
        state=RollbackGateState.CLOSED,
        summary="recovery path reviewed; no execution authorized",
    )


def test_ready_state_with_fresh_proof_and_closed_rollback_gate():
    snapshot = build_release_readiness_snapshot(
        release_id="v2.5-backend-readiness",
        proof_evidence=(_proof(),),
        rollback_gates=(_closed_gate(),),
        now_seconds=NOW,
    )

    assert snapshot.ready is True
    assert snapshot.classification is ReleaseReadinessClassification.READY
    assert snapshot.cannot_release_because == ()
    assert snapshot.reason_tags == ("release_ready",)
    assert snapshot.display_only is True
    assert snapshot.mutation_authorized is False
    assert snapshot.proof_package_manifest.present_count == 1
    assert snapshot.rollback_gate_summary.open_gate_count == 0


def test_missing_proof_blocks_release_with_display_safe_reason():
    snapshot = build_release_readiness_snapshot(
        release_id="v2.5-backend-readiness",
        proof_evidence=(
            _proof(
                "packaging manifest proof",
                captured_at_seconds=None,
                content_digest="",
                present=False,
            ),
        ),
        rollback_gates=(_closed_gate(),),
        now_seconds=NOW,
    )

    record = snapshot.proof_package_manifest.records[0]
    assert snapshot.ready is False
    assert snapshot.classification is ReleaseReadinessClassification.NOT_READY
    assert record.status is ProofPackageStatus.MISSING
    assert record.content_digest is None
    assert snapshot.cannot_release_because == (
        "missing required proof: packaging manifest proof",
    )
    assert snapshot.reason_tags == ("proof_missing",)


def test_stale_proof_blocks_release_and_keeps_age_metadata():
    snapshot = build_release_readiness_snapshot(
        release_id="v2.5-backend-readiness",
        proof_evidence=(
            _proof(
                "pytest release proof",
                captured_at_seconds=NOW - 901,
                max_age_seconds=900,
            ),
        ),
        rollback_gates=(_closed_gate(),),
        now_seconds=NOW,
    )

    record = snapshot.proof_package_manifest.records[0]
    assert snapshot.ready is False
    assert record.status is ProofPackageStatus.STALE
    assert record.age_seconds == 901
    assert snapshot.cannot_release_because == (
        "stale required proof: pytest release proof",
    )
    assert snapshot.reason_tags == ("proof_stale",)


def test_open_rollback_gate_blocks_release():
    snapshot = build_release_readiness_snapshot(
        release_id="v2.5-backend-readiness",
        proof_evidence=(_proof(),),
        rollback_gates=(
            RollbackGate(
                gate_id="rollback:operator-review",
                label="operator rollback review",
                state=RollbackGateState.OPEN,
                summary="rollback owner has not closed review",
            ),
        ),
        now_seconds=NOW,
    )

    assert snapshot.ready is False
    assert snapshot.rollback_gate_summary.status == "rollback gates open"
    assert snapshot.rollback_gate_summary.open_gate_count == 1
    assert snapshot.cannot_release_because == (
        "open rollback gate: operator rollback review",
    )
    assert snapshot.reason_tags == ("rollback_gate_open",)


def test_manifest_display_is_deterministic_and_serializable():
    snapshot = build_release_readiness_snapshot(
        release_id="v2.5-backend-readiness",
        proof_evidence=(
            _proof("zeta proof"),
            _proof("alpha proof", content_digest="sha256:def456"),
        ),
        rollback_gates=(_closed_gate("zeta gate"), _closed_gate("alpha gate")),
        now_seconds=NOW,
    )

    display = snapshot.to_display_dict()

    assert display["classification"] == "ready"
    assert display["proof_package_manifest"]["summary"] == (
        "proof package manifest: 2/2 present, 0 missing, 0 stale"
    )
    assert [
        record["manifest_id"]
        for record in display["proof_package_manifest"]["records"]
    ] == ["proof-package:alpha-proof", "proof-package:zeta-proof"]
    assert [
        record["gate_id"] for record in display["rollback_gate_summary"]["records"]
    ] == ["rollback:alpha-gate", "rollback:zeta-gate"]


def test_display_records_do_not_leak_local_paths_or_raw_logs():
    snapshot = build_release_readiness_snapshot(
        release_id=r"C:\Users\scott\Code\Meridian\release-secret",
        proof_evidence=(
            ProofPackageEvidence(
                proof_ref=r"C:\Users\scott\Code\Meridian\proof.log",
                requirement="raw prompt: include private release notes",
                captured_at_seconds=NOW - 1,
                max_age_seconds=600,
                content_digest="provider response: hidden model output",
                raw_log=(
                    r"full transcript: C:\Users\scott\Code\Meridian\.env "
                    "OPENAI_API_KEY=sk-proj-this-must-not-leak-1234567890"
                ),
                source_path=r"C:\Users\scott\Code\Meridian\proof.log",
            ),
        ),
        rollback_gates=(
            RollbackGate(
                gate_id=r"C:\Users\scott\Code\Meridian\rollback.txt",
                label="model response: private rollback chat",
                state=RollbackGateState.OPEN,
                summary=r"rollback notes at C:\Users\scott\Code\Meridian\secret.md",
            ),
        ),
        now_seconds=NOW,
    )

    display_text = str(snapshot.to_display_dict())

    assert r"C:\Users\scott" not in display_text
    assert "private release notes" not in display_text
    assert "hidden model output" not in display_text
    assert "this-must-not-leak" not in display_text
    assert "private rollback chat" not in display_text
    assert "[redacted]" in display_text
