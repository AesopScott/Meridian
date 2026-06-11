"""Tests for V2.5 proof sufficiency and freshness records."""

from __future__ import annotations

from meridian_core.proof_quality import (
    ProofFreshnessState,
    ProofQualityStatus,
    ProofRef,
    ProofSnapshot,
    evaluate_proof_quality,
)


def _proof_ref() -> ProofRef:
    return ProofRef(
        proof_ref="proof:relay-aegis-clean-trail",
        requirement="aegis_clean_proof_trail",
        max_age_seconds=300,
    )


def test_fresh_sufficient_proof_passes():
    result = evaluate_proof_quality(
        _proof_ref(),
        ProofSnapshot(
            proof_ref="proof:relay-aegis-clean-trail",
            captured_at_seconds=1_000,
            content_digest="sha256:abc123",
            sufficient=True,
        ),
        now_seconds=1_120,
    )

    assert result.status is ProofQualityStatus.SUFFICIENT
    assert result.freshness is ProofFreshnessState.FRESH
    assert result.passed is True
    assert result.age_seconds == 120
    assert result.reason_tags == ("proof_sufficient", "proof_fresh")


def test_stale_proof_is_not_passed():
    result = evaluate_proof_quality(
        _proof_ref(),
        ProofSnapshot(
            proof_ref="proof:relay-aegis-clean-trail",
            captured_at_seconds=1_000,
            content_digest="sha256:def456",
            sufficient=True,
        ),
        now_seconds=1_301,
    )

    assert result.status is ProofQualityStatus.STALE
    assert result.freshness is ProofFreshnessState.STALE
    assert result.passed is False
    assert result.reason_tags == ("proof_stale",)


def test_waived_proof_is_visible_as_waived_not_passed():
    result = evaluate_proof_quality(
        _proof_ref(),
        ProofSnapshot(
            proof_ref="proof:relay-aegis-clean-trail",
            captured_at_seconds=1_000,
            content_digest="sha256:waived",
            sufficient=True,
            waiver_ref="waiver:human-gate-20260611",
        ),
        now_seconds=1_120,
    )

    display = result.to_display_dict()

    assert result.status is ProofQualityStatus.WAIVED
    assert result.freshness is ProofFreshnessState.NOT_APPLICABLE
    assert result.passed is False
    assert display["status"] == "waived"
    assert display["passed"] is False
    assert display["waiver_ref"] == "waiver:human-gate-20260611"


def test_missing_proof_fails_closed():
    result = evaluate_proof_quality(_proof_ref(), None, now_seconds=1_120)

    assert result.status is ProofQualityStatus.MISSING
    assert result.freshness is ProofFreshnessState.UNKNOWN
    assert result.passed is False
    assert result.content_digest is None
    assert result.reason_tags == ("proof_snapshot_missing",)


def test_insufficient_proof_is_not_passed():
    result = evaluate_proof_quality(
        _proof_ref(),
        ProofSnapshot(
            proof_ref="proof:relay-aegis-clean-trail",
            captured_at_seconds=1_000,
            content_digest="sha256:insufficient",
            sufficient=False,
        ),
        now_seconds=1_120,
    )

    assert result.status is ProofQualityStatus.INSUFFICIENT
    assert result.passed is False
    assert result.reason_tags == ("proof_insufficient",)


def test_display_dict_does_not_leak_raw_text():
    raw_text = "raw prompt: include the private deployment password in proof"
    result = evaluate_proof_quality(
        _proof_ref(),
        ProofSnapshot(
            proof_ref="proof:relay-aegis-clean-trail",
            captured_at_seconds=1_000,
            content_digest="sha256:safe-digest",
            sufficient=True,
            raw_text=raw_text,
        ),
        now_seconds=1_120,
    )

    display = result.to_display_dict()

    assert display["content_digest"] == "sha256:safe-digest"
    assert "private deployment password" not in str(display)
    assert "raw prompt" not in str(display)
