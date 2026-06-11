"""Tests for backend Voice I/O authority."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meridian_core.voice_io import (
    VoiceCommandFamily,
    VoiceCommandIntent,
    VoiceIntentFamily,
    VoiceMode,
    VoiceOutputStatus,
    VoicePrivacyLevel,
    VoiceProviderCapability,
    VoiceRuntimeState,
    VoiceTrustState,
    VoiceValidationError,
    apply_transcript_correction,
    build_voice_runtime_state,
    create_output_job,
    create_transcript_draft,
    interrupt_output_job,
    mute_output_job,
    normalize_voice_intent,
    recognize_voice_command_intent,
)


NOW = datetime(2026, 6, 10, 22, 30, tzinfo=timezone.utc)


def test_voice_runtime_state_defaults_fail_closed():
    state = VoiceRuntimeState()
    payload = state.to_dict()

    assert payload["display_only"] is True
    assert payload["mutation_authorized"] is False
    assert payload["microphone_authorized"] is False
    assert payload["speech_output_authorized"] is False
    assert payload["read_aloud_authorized"] is False
    assert payload["controls_disabled"] is True
    assert payload["raw_audio_included"] is False
    assert payload["raw_transcript_included"] is False
    assert payload["provider_response_included"] is False


def test_runtime_authorization_requires_available_matching_capability():
    unavailable = VoiceProviderCapability(
        provider_id="provider://voice/local",
        modes=(VoiceMode.ASR,),
        trust_state=VoiceTrustState.DISPLAY_ONLY,
        privacy_level=VoicePrivacyLevel.LOCAL_ONLY,
        evidence_refs=("proof://voice/display-only",),
    )
    state = build_voice_runtime_state(
        (unavailable,),
        microphone_authorized=True,
        speech_output_authorized=True,
        read_aloud_authorized=True,
        evidence_refs=("proof://voice/request",),
    )
    assert state.microphone_authorized is False
    assert state.speech_output_authorized is False
    assert state.controls_disabled is True

    asr = VoiceProviderCapability(
        provider_id="provider://voice/asr",
        modes=(VoiceMode.ASR,),
        trust_state=VoiceTrustState.AVAILABLE,
        privacy_level=VoicePrivacyLevel.LOCAL_ONLY,
    )
    tts = VoiceProviderCapability(
        provider_id="provider://voice/tts",
        modes=(VoiceMode.TTS,),
        trust_state=VoiceTrustState.AVAILABLE,
        privacy_level=VoicePrivacyLevel.LOCAL_ONLY,
        voice_refs=("voice://prime/default",),
    )
    enabled = build_voice_runtime_state(
        (asr, tts),
        microphone_authorized=True,
        speech_output_authorized=True,
        read_aloud_authorized=True,
        selected_voice_ref="voice://prime/default",
    )
    assert enabled.microphone_authorized is True
    assert enabled.speech_output_authorized is True
    assert enabled.read_aloud_authorized is True
    assert enabled.controls_disabled is False


def test_create_transcript_draft_stores_metadata_not_raw_text():
    draft = create_transcript_draft(
        draft_id="voice-draft-1",
        provider_ref="provider://voice/asr",
        transcript_text="Create a routine review checkpoint",
        confidence=0.91,
        created_at=NOW,
        evidence_refs=("proof://voice/asr-result",),
    )
    payload = draft.to_dict()

    assert payload["text_length"] == len("Create a routine review checkpoint")
    assert len(payload["text_hash"]) == 64
    assert "Create a routine" not in str(payload)
    assert payload["raw_transcript_included"] is False
    assert payload["prompt_submit_authorized"] is False


def test_transcript_correction_updates_hash_without_raw_text():
    draft = create_transcript_draft(
        draft_id="voice-draft-1",
        provider_ref="provider://voice/asr",
        transcript_text="run cross check",
        confidence=0.81,
        created_at=NOW,
    )
    corrected = apply_transcript_correction(
        draft,
        corrected_text="run crosscheck",
        evidence_refs=("proof://voice/correction",),
    )

    assert corrected.correction_count == 1
    assert corrected.text_hash != draft.text_hash
    assert corrected.to_dict()["raw_transcript_included"] is False
    assert corrected.evidence_refs[-1] == "proof://voice/correction"


def test_normalize_voice_intent_uses_injected_normalizer_and_confirmation_gate():
    draft = create_transcript_draft(
        draft_id="voice-draft-2",
        provider_ref="provider://voice/asr",
        transcript_text="rerun verification",
        confidence=0.76,
        created_at=NOW,
    )

    def normalizer(received):
        assert received is draft
        return VoiceCommandIntent(
            intent_id="voice-intent-1",
            family=VoiceIntentFamily.COMMAND,
            action="rerun-verification",
            target_ref="voice://intent/xck-rerun",
            confidence=0.76,
            requires_confirmation=False,
            evidence_refs=("proof://voice/intent",),
        )

    intent = normalize_voice_intent(draft, normalizer)

    assert intent.requires_confirmation is True
    assert intent.to_dict()["execution_authorized"] is False


def test_recognize_voice_command_intent_maps_harness_panel_commands_without_execution():
    intent = recognize_voice_command_intent(
        "Open Review Console",
        confidence=0.93,
        evidence_refs=("proof://voice/voc10",),
    )
    payload = intent.to_dict()

    assert intent.command_family is VoiceCommandFamily.HARNESS_PANEL
    assert intent.family is VoiceIntentFamily.COMMAND
    assert intent.action == "open"
    assert intent.target_ref == "voice://harness/review-console"
    assert intent.requires_confirmation is False
    assert payload["command_family"] == "harness_panel"
    assert payload["execution_authorized"] is False
    assert "Open Review Console" not in str(payload)


@pytest.mark.parametrize(
    ("phrase", "expected_action", "expected_target", "requires_confirmation"),
    (
        ("Switch to Polaris", "switch", "voice://project/polaris", True),
        ("Show build lanes", "focus", "voice://lane/build", False),
        ("Open Build 1", "focus", "voice://lane/build-1", False),
        ("Show Codex Reviews B", "focus", "voice://review/codex-b", False),
        ("What is blocked?", "ask", "voice://status/blocked", False),
        ("What is next?", "ask", "voice://status/next", False),
        ("Reset", "reset", "voice://surface/reset", True),
        ("Reload", "reload", "voice://surface/reload", True),
        ("Open filter", "open", "voice://surface/filter", False),
    ),
)
def test_recognize_voice_command_intent_maps_project_lane_commands(
    phrase,
    expected_action,
    expected_target,
    requires_confirmation,
):
    intent = recognize_voice_command_intent(phrase, confidence=0.9)

    assert intent.command_family is VoiceCommandFamily.PROJECT_LANE
    assert intent.action == expected_action
    assert intent.target_ref == expected_target
    assert intent.requires_confirmation is requires_confirmation
    assert intent.to_dict()["execution_authorized"] is False


@pytest.mark.parametrize(
    ("phrase", "family", "broad_family", "action", "target", "requires_confirmation"),
    (
        ("Start dictation", VoiceCommandFamily.DICTATION, VoiceIntentFamily.DICTATION, "start", "voice://dictation/session", False),
        ("Clear dictation", VoiceCommandFamily.DICTATION, VoiceIntentFamily.DICTATION, "clear", "voice://dictation/session", True),
        ("Send to Prime", VoiceCommandFamily.DICTATION, VoiceIntentFamily.DICTATION, "submit", "voice://dictation/prime-submit", True),
        ("Read Prime's answer", VoiceCommandFamily.SPEECH_OUTPUT, VoiceIntentFamily.CONTROL, "read", "voice://speech/prime-answer", False),
        ("Stop reading", VoiceCommandFamily.SPEECH_OUTPUT, VoiceIntentFamily.CONTROL, "stop", "voice://speech/current", True),
        ("Mute", VoiceCommandFamily.SPEECH_OUTPUT, VoiceIntentFamily.CONTROL, "mute", "voice://speech/output", True),
        ("Show proof", VoiceCommandFamily.PROOF, VoiceIntentFamily.COMMAND, "show", "voice://proof/current", False),
        ("What changed?", VoiceCommandFamily.PROOF, VoiceIntentFamily.COMMAND, "ask", "voice://proof/change-summary", False),
        ("Show the latest commit", VoiceCommandFamily.PROOF, VoiceIntentFamily.COMMAND, "show", "voice://proof/latest-commit", False),
        ("Run crosscheck", VoiceCommandFamily.PROOF, VoiceIntentFamily.COMMAND, "run-preview", "voice://proof/crosscheck", True),
        ("Run cross check", VoiceCommandFamily.PROOF, VoiceIntentFamily.COMMAND, "run-preview", "voice://proof/crosscheck", True),
    ),
)
def test_recognize_voice_command_intent_maps_dictation_speech_and_proof_commands(
    phrase,
    family,
    broad_family,
    action,
    target,
    requires_confirmation,
):
    intent = recognize_voice_command_intent(phrase, confidence=0.88)

    assert intent.command_family is family
    assert intent.family is broad_family
    assert intent.action == action
    assert intent.target_ref == target
    assert intent.requires_confirmation is requires_confirmation
    assert intent.to_dict()["execution_authorized"] is False


def test_recognize_voice_command_intent_unknown_is_preview_only_and_confirmation_gated():
    intent = recognize_voice_command_intent("Do the thing", confidence=0.67)
    payload = intent.to_dict()

    assert intent.command_family is VoiceCommandFamily.UNKNOWN
    assert intent.action == "unknown"
    assert intent.target_ref == "voice://command/unknown"
    assert intent.requires_confirmation is True
    assert payload["execution_authorized"] is False
    assert "Do the thing" not in str(payload)


def test_recognize_voice_command_intent_gates_low_confidence_known_commands():
    intent = recognize_voice_command_intent("Open Echo", confidence=0.1)

    assert intent.command_family is VoiceCommandFamily.HARNESS_PANEL
    assert intent.action == "open"
    assert intent.requires_confirmation is True
    assert intent.to_dict()["execution_authorized"] is False


def test_recognize_voice_command_intent_honors_custom_confirmation_threshold():
    intent = recognize_voice_command_intent(
        "Open Echo",
        confidence=0.9,
        confirmation_threshold=0.95,
    )

    assert intent.command_family is VoiceCommandFamily.HARNESS_PANEL
    assert intent.requires_confirmation is True
    assert intent.to_dict()["execution_authorized"] is False


def test_recognize_voice_command_intent_rejects_unsafe_phrase_and_bad_confidence():
    with pytest.raises(VoiceValidationError, match="phrase"):
        recognize_voice_command_intent(
            r"Open C:\Users\scott\secret.txt",
            confidence=0.9,
        )

    with pytest.raises(VoiceValidationError, match="confidence"):
        recognize_voice_command_intent("Open Echo", confidence=1.1)

    with pytest.raises(VoiceValidationError, match="confirmation_threshold"):
        recognize_voice_command_intent("Open Echo", confidence=0.9, confirmation_threshold=1.1)


def test_normalize_voice_intent_rejects_bad_normalizer_output():
    draft = create_transcript_draft(
        draft_id="voice-draft-3",
        provider_ref="provider://voice/asr",
        transcript_text="open settings",
        confidence=0.9,
        created_at=NOW,
    )

    with pytest.raises(VoiceValidationError, match="VoiceCommandIntent"):
        normalize_voice_intent(draft, lambda received: "not-intent")


@pytest.mark.parametrize("threshold", (-1, 1.1))
def test_normalize_voice_intent_rejects_invalid_confirmation_threshold(threshold):
    draft = create_transcript_draft(
        draft_id="voice-draft-4",
        provider_ref="provider://voice/asr",
        transcript_text="rerun verification",
        confidence=0.2,
        created_at=NOW,
    )

    with pytest.raises(VoiceValidationError, match="confirmation_threshold"):
        normalize_voice_intent(
            draft,
            lambda received: VoiceCommandIntent(
                intent_id="voice-intent-low-confidence",
                family=VoiceIntentFamily.COMMAND,
                action="rerun-verification",
                target_ref="voice://intent/xck-rerun",
                confidence=0.2,
                requires_confirmation=False,
            ),
            confirmation_threshold=threshold,
        )


def test_output_job_is_metadata_only_and_supports_mute_interrupt():
    job = create_output_job(
        job_id="voice-job-1",
        source_ref="voice://summary/prime",
        voice_ref="voice://prime/default",
        output_text="Checkpoint complete",
        created_at=NOW,
        evidence_refs=("proof://voice/output",),
    )
    payload = job.to_dict()

    assert job.status is VoiceOutputStatus.QUEUED
    assert payload["text_length"] == len("Checkpoint complete")
    assert "Checkpoint complete" not in str(payload)
    assert payload["audio_included"] is False
    assert payload["provider_response_included"] is False
    assert mute_output_job(job).status is VoiceOutputStatus.MUTED
    assert interrupt_output_job(job).status is VoiceOutputStatus.INTERRUPTED


@pytest.mark.parametrize(
    "unsafe_text",
    (
        "raw audio bytes",
        "raw transcript of worker chat",
        "serialized prompt payload",
        "provider response body",
        "token=abc123",
        r"C:\Users\scott\secret.wav",
        "../private/audio.wav",
    ),
)
def test_voice_text_inputs_reject_unsafe_content(unsafe_text):
    with pytest.raises(VoiceValidationError):
        create_transcript_draft(
            draft_id="voice-draft-unsafe",
            provider_ref="provider://voice/asr",
            transcript_text=unsafe_text,
            confidence=0.9,
            created_at=NOW,
        )

    with pytest.raises(VoiceValidationError):
        create_output_job(
            job_id="voice-job-unsafe",
            source_ref="voice://summary/prime",
            voice_ref="voice://prime/default",
            output_text=unsafe_text,
            created_at=NOW,
        )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "provider://../private/provider.json",
        "voice://./runtime/audio.wav",
        r"proof://C:\Users\scott\voice.txt",
    ),
)
def test_voice_refs_reject_path_payloads(unsafe_ref):
    with pytest.raises(VoiceValidationError, match="local paths"):
        VoiceProviderCapability(
            provider_id=unsafe_ref,
            modes=(VoiceMode.ASR,),
        )
