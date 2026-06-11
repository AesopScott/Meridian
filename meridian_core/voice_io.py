"""Backend Voice I/O authority boundary for Meridian V2.

This module owns typed, display-safe voice provider/runtime state. It does not
capture microphone input, play audio, call providers, wire UI controls, or send
prompts to Relay/Prime.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterable, Optional


SHORT_TEXT_MAX = 160
SUMMARY_MAX = 420
SAFE_REF_SCHEMES = (
    "proof://",
    "provider://",
    "review://",
    "task://",
    "voice://",
)
UNSAFE_TERMS = (
    "raw audio",
    "raw transcript",
    "raw prompt",
    "serialized prompt",
    "provider response",
    "worker chat",
    "api key",
    "secret",
    "credential",
    "token=",
)


class VoiceValidationError(ValueError):
    """Raised when voice authority input is unsafe or inconsistent."""


class VoiceMode(Enum):
    ASR = "asr"
    TTS = "tts"


class VoiceTrustState(Enum):
    UNAVAILABLE = "unavailable"
    DISPLAY_ONLY = "display_only"
    AVAILABLE = "available"


class VoicePrivacyLevel(Enum):
    LOCAL_ONLY = "local_only"
    PROVIDER_BOUND = "provider_bound"
    UNKNOWN = "unknown"


class VoiceIntentFamily(Enum):
    DICTATION = "dictation"
    COMMAND = "command"
    CONTROL = "control"


class VoiceOutputStatus(Enum):
    QUEUED = "queued"
    SPEAKING = "speaking"
    MUTED = "muted"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise VoiceValidationError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _looks_like_path(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if re.search(r"\b[\w.-]+[\\/][\w.-]+", value):
        return True
    return False


def _looks_like_uri_path_payload(value: str) -> bool:
    if re.search(r"^[A-Za-z]:[\\/]", value):
        return True
    if value.startswith(("/", "\\", "./", ".\\", "../", "..\\")):
        return True
    if "\\" in value:
        return True
    segments = [segment for segment in value.split("/") if segment]
    if any(segment in (".", "..") for segment in segments):
        return True
    if any(re.search(r"\.[A-Za-z0-9]{1,8}$", segment) for segment in segments):
        return True
    return False


def _safe_text(value: str, field: str, max_length: int = SHORT_TEXT_MAX) -> str:
    text = str(value).strip()
    if not text:
        raise VoiceValidationError(f"{field} must not be empty")
    if len(text) > max_length:
        raise VoiceValidationError(f"{field} is too long")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise VoiceValidationError(f"{field} contains unsafe content")
    if _looks_like_path(text):
        raise VoiceValidationError(f"{field} must not contain local paths")
    return text


def _safe_ref(value: str, field: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise VoiceValidationError(f"{field} must not be empty")
    if len(ref) > SHORT_TEXT_MAX:
        raise VoiceValidationError(f"{field} is too long")
    if not ref.startswith(SAFE_REF_SCHEMES):
        ref = _safe_text(ref, field)
        if "://" in ref:
            raise VoiceValidationError(f"{field} uses an unsupported URI scheme")
        return ref
    lowered = ref.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise VoiceValidationError(f"{field} contains unsafe content")
    payload = ref.split("://", 1)[1]
    if not payload or _looks_like_uri_path_payload(payload):
        raise VoiceValidationError(f"{field} must not contain local paths")
    return ref


def _safe_refs(values: Iterable[str], field: str) -> tuple[str, ...]:
    refs = tuple(_safe_ref(value, field) for value in values)
    if len(set(refs)) != len(refs):
        raise VoiceValidationError(f"{field} must not contain duplicates")
    return refs


def _hash_content(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VoiceProviderCapability:
    provider_id: str
    modes: tuple[VoiceMode, ...]
    trust_state: VoiceTrustState = VoiceTrustState.UNAVAILABLE
    privacy_level: VoicePrivacyLevel = VoicePrivacyLevel.UNKNOWN
    voice_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_ref(self.provider_id, "VoiceProviderCapability.provider_id")
        object.__setattr__(self, "modes", tuple(self.modes))
        if not self.modes:
            raise VoiceValidationError("VoiceProviderCapability.modes must not be empty")
        for mode in self.modes:
            if not isinstance(mode, VoiceMode):
                raise VoiceValidationError("modes must be VoiceMode")
        if not isinstance(self.trust_state, VoiceTrustState):
            raise VoiceValidationError("trust_state must be VoiceTrustState")
        if not isinstance(self.privacy_level, VoicePrivacyLevel):
            raise VoiceValidationError("privacy_level must be VoicePrivacyLevel")
        object.__setattr__(self, "voice_refs", _safe_refs(self.voice_refs, "VoiceProviderCapability.voice_refs"))
        object.__setattr__(
            self,
            "evidence_refs",
            _safe_refs(self.evidence_refs, "VoiceProviderCapability.evidence_refs"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "modes": tuple(mode.value for mode in self.modes),
            "trust_state": self.trust_state.value,
            "privacy_level": self.privacy_level.value,
            "voice_refs": self.voice_refs,
            "evidence_refs": self.evidence_refs,
        }


@dataclass(frozen=True)
class VoiceRuntimeState:
    capabilities: tuple[VoiceProviderCapability, ...] = ()
    microphone_authorized: bool = False
    speech_output_authorized: bool = False
    read_aloud_authorized: bool = False
    controls_disabled: bool = True
    selected_voice_ref: Optional[str] = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        for capability in self.capabilities:
            if not isinstance(capability, VoiceProviderCapability):
                raise VoiceValidationError("capabilities must be VoiceProviderCapability")
        if self.selected_voice_ref is not None:
            _safe_ref(self.selected_voice_ref, "VoiceRuntimeState.selected_voice_ref")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "VoiceRuntimeState.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "display_only": True,
            "mutation_authorized": False,
            "microphone_authorized": self.microphone_authorized,
            "speech_output_authorized": self.speech_output_authorized,
            "read_aloud_authorized": self.read_aloud_authorized,
            "controls_disabled": self.controls_disabled,
            "selected_voice_ref": self.selected_voice_ref,
            "capabilities": tuple(capability.to_dict() for capability in self.capabilities),
            "evidence_refs": self.evidence_refs,
            "raw_audio_included": False,
            "raw_transcript_included": False,
            "raw_prompt_included": False,
            "provider_response_included": False,
        }


def build_voice_runtime_state(
    capabilities: Iterable[VoiceProviderCapability] = (),
    *,
    microphone_authorized: bool = False,
    speech_output_authorized: bool = False,
    read_aloud_authorized: bool = False,
    selected_voice_ref: Optional[str] = None,
    evidence_refs: tuple[str, ...] = (),
) -> VoiceRuntimeState:
    """Build fail-closed runtime state from explicit provider capabilities."""
    caps = tuple(capabilities)
    has_asr = any(
        capability.trust_state is VoiceTrustState.AVAILABLE and VoiceMode.ASR in capability.modes
        for capability in caps
    )
    has_tts = any(
        capability.trust_state is VoiceTrustState.AVAILABLE and VoiceMode.TTS in capability.modes
        for capability in caps
    )
    mic = bool(microphone_authorized and has_asr)
    speech = bool(speech_output_authorized and has_tts)
    read_aloud = bool(read_aloud_authorized and speech)
    return VoiceRuntimeState(
        capabilities=caps,
        microphone_authorized=mic,
        speech_output_authorized=speech,
        read_aloud_authorized=read_aloud,
        controls_disabled=not (mic or speech),
        selected_voice_ref=selected_voice_ref,
        evidence_refs=evidence_refs,
    )


@dataclass(frozen=True)
class VoiceTranscriptDraft:
    draft_id: str
    provider_ref: str
    text_hash: str
    text_length: int
    confidence: float
    created_at: datetime
    correction_count: int = 0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.draft_id, "VoiceTranscriptDraft.draft_id")
        _safe_ref(self.provider_ref, "VoiceTranscriptDraft.provider_ref")
        _safe_text(self.text_hash, "VoiceTranscriptDraft.text_hash")
        if self.text_length < 1:
            raise VoiceValidationError("text_length must be positive")
        if not 0 <= self.confidence <= 1:
            raise VoiceValidationError("confidence must be between 0 and 1")
        _as_utc(self.created_at)
        if self.correction_count < 0:
            raise VoiceValidationError("correction_count must not be negative")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "VoiceTranscriptDraft.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "provider_ref": self.provider_ref,
            "text_hash": self.text_hash,
            "text_length": self.text_length,
            "confidence": self.confidence,
            "created_at": _as_utc(self.created_at).isoformat(),
            "correction_count": self.correction_count,
            "evidence_refs": self.evidence_refs,
            "raw_transcript_included": False,
            "prompt_submit_authorized": False,
        }


def create_transcript_draft(
    *,
    draft_id: str,
    provider_ref: str,
    transcript_text: str,
    confidence: float,
    created_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> VoiceTranscriptDraft:
    """Create transcript metadata without retaining or returning raw text."""
    text = str(transcript_text)
    if not text.strip():
        raise VoiceValidationError("transcript_text must not be empty")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise VoiceValidationError("transcript_text contains unsafe content")
    if _looks_like_path(text):
        raise VoiceValidationError("transcript_text must not contain local paths")
    return VoiceTranscriptDraft(
        draft_id=draft_id,
        provider_ref=provider_ref,
        text_hash=_hash_content(text),
        text_length=len(text),
        confidence=confidence,
        created_at=created_at,
        evidence_refs=evidence_refs,
    )


def apply_transcript_correction(
    draft: VoiceTranscriptDraft,
    *,
    corrected_text: str,
    evidence_refs: tuple[str, ...] = (),
) -> VoiceTranscriptDraft:
    """Return corrected transcript metadata without retaining raw corrected text."""
    corrected = create_transcript_draft(
        draft_id=draft.draft_id,
        provider_ref=draft.provider_ref,
        transcript_text=corrected_text,
        confidence=draft.confidence,
        created_at=draft.created_at,
        evidence_refs=draft.evidence_refs + evidence_refs,
    )
    return replace(corrected, correction_count=draft.correction_count + 1)


@dataclass(frozen=True)
class VoiceCommandIntent:
    intent_id: str
    family: VoiceIntentFamily
    action: str
    target_ref: str
    confidence: float
    requires_confirmation: bool
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.intent_id, "VoiceCommandIntent.intent_id")
        if not isinstance(self.family, VoiceIntentFamily):
            raise VoiceValidationError("family must be VoiceIntentFamily")
        _safe_text(self.action, "VoiceCommandIntent.action")
        _safe_ref(self.target_ref, "VoiceCommandIntent.target_ref")
        if not 0 <= self.confidence <= 1:
            raise VoiceValidationError("confidence must be between 0 and 1")
        if not isinstance(self.requires_confirmation, bool):
            raise VoiceValidationError("requires_confirmation must be bool")
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "VoiceCommandIntent.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "intent_id": self.intent_id,
            "family": self.family.value,
            "action": self.action,
            "target_ref": self.target_ref,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
            "evidence_refs": self.evidence_refs,
            "execution_authorized": False,
        }


VoiceIntentNormalizer = Callable[[VoiceTranscriptDraft], VoiceCommandIntent]


def normalize_voice_intent(
    draft: VoiceTranscriptDraft,
    normalizer: VoiceIntentNormalizer,
    *,
    confirmation_threshold: float = 0.82,
) -> VoiceCommandIntent:
    """Normalize transcript metadata through an injected local normalizer."""
    if not isinstance(draft, VoiceTranscriptDraft):
        raise VoiceValidationError("draft must be VoiceTranscriptDraft")
    if not callable(normalizer):
        raise VoiceValidationError("normalizer must be callable")
    if not 0 <= confirmation_threshold <= 1:
        raise VoiceValidationError("confirmation_threshold must be between 0 and 1")
    intent = normalizer(draft)
    if not isinstance(intent, VoiceCommandIntent):
        raise VoiceValidationError("normalizer must return VoiceCommandIntent")
    requires_confirmation = intent.requires_confirmation or intent.confidence < confirmation_threshold
    return replace(intent, requires_confirmation=requires_confirmation)


@dataclass(frozen=True)
class VoiceOutputJob:
    job_id: str
    source_ref: str
    voice_ref: str
    status: VoiceOutputStatus
    text_hash: str
    text_length: int
    created_at: datetime
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_text(self.job_id, "VoiceOutputJob.job_id")
        _safe_ref(self.source_ref, "VoiceOutputJob.source_ref")
        _safe_ref(self.voice_ref, "VoiceOutputJob.voice_ref")
        if not isinstance(self.status, VoiceOutputStatus):
            raise VoiceValidationError("status must be VoiceOutputStatus")
        _safe_text(self.text_hash, "VoiceOutputJob.text_hash")
        if self.text_length < 1:
            raise VoiceValidationError("text_length must be positive")
        _as_utc(self.created_at)
        object.__setattr__(self, "evidence_refs", _safe_refs(self.evidence_refs, "VoiceOutputJob.evidence_refs"))

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "source_ref": self.source_ref,
            "voice_ref": self.voice_ref,
            "status": self.status.value,
            "text_hash": self.text_hash,
            "text_length": self.text_length,
            "created_at": _as_utc(self.created_at).isoformat(),
            "evidence_refs": self.evidence_refs,
            "raw_prompt_included": False,
            "provider_response_included": False,
            "audio_included": False,
        }


def create_output_job(
    *,
    job_id: str,
    source_ref: str,
    voice_ref: str,
    output_text: str,
    created_at: datetime,
    evidence_refs: tuple[str, ...] = (),
) -> VoiceOutputJob:
    """Create a read-aloud job record without retaining output text or audio."""
    text = str(output_text)
    if not text.strip():
        raise VoiceValidationError("output_text must not be empty")
    lowered = text.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        raise VoiceValidationError("output_text contains unsafe content")
    if _looks_like_path(text):
        raise VoiceValidationError("output_text must not contain local paths")
    return VoiceOutputJob(
        job_id=job_id,
        source_ref=source_ref,
        voice_ref=voice_ref,
        status=VoiceOutputStatus.QUEUED,
        text_hash=_hash_content(text),
        text_length=len(text),
        created_at=created_at,
        evidence_refs=evidence_refs,
    )


def mute_output_job(job: VoiceOutputJob) -> VoiceOutputJob:
    return replace(job, status=VoiceOutputStatus.MUTED)


def interrupt_output_job(job: VoiceOutputJob) -> VoiceOutputJob:
    return replace(job, status=VoiceOutputStatus.INTERRUPTED)
