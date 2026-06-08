"""Display-only Autonomy/Release snapshot backed by Prime autonomy.

This module intentionally exposes release posture, not release controls. It
wraps the reviewed Prime autonomy non-authority export so the UI can show a
safe snapshot without adding deployment, account, prompt, response, process, or
filesystem visibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from meridian_core.model_adapter import (
    bind_deepseek_validation_disposition,
    deepseek_candidate_metadata_preset,
)
from meridian_core.prime_autonomy import (
    DeepSeekValidationRuntimeStateExport,
    build_deepseek_validation_runtime_state_export,
)

SNAPSHOT_VERSION = "release-autonomy-display-v1"
SNAPSHOT_SOURCE = (
    "meridian_core.release_autonomy_snapshot.release_autonomy_snapshot"
)

_DISPLAY_ONLY_GUARDRAILS: tuple[str, ...] = (
    "display_only",
    "no_release_execution_controls",
    "no_deployment_buttons",
    "no_credentials_or_account_probe",
    "no_raw_prompts_or_responses",
    "no_raw_evidence_bodies",
    "no_raw_worker_chat",
    "no_pids",
    "no_absolute_or_local_filesystem_paths",
)


@dataclass(frozen=True)
class ReleaseAutonomySnapshot:
    """Safe Release harness projection of Prime autonomy non-authority state."""

    generated_at: datetime
    prime_export: DeepSeekValidationRuntimeStateExport
    release_ready: bool = False
    display_only: bool = True
    mutation_authorized: bool = False
    release_execution_authorized: bool = False
    deployment_authorized: bool = False
    credential_probe_authorized: bool = False
    account_probe_authorized: bool = False
    release_controls_visible: bool = False
    deployment_controls_visible: bool = False
    raw_prompt_visible: bool = False
    raw_response_visible: bool = False
    raw_evidence_body_visible: bool = False
    raw_worker_chat_visible: bool = False
    pids_visible: bool = False
    raw_filesystem_paths_visible: bool = False
    guardrails: tuple[str, ...] = field(default_factory=lambda: _DISPLAY_ONLY_GUARDRAILS)

    def __post_init__(self) -> None:
        if not self.display_only:
            raise ValueError("ReleaseAutonomySnapshot must be display-only")
        forbidden_flags = {
            "release_ready": self.release_ready,
            "mutation_authorized": self.mutation_authorized,
            "release_execution_authorized": self.release_execution_authorized,
            "deployment_authorized": self.deployment_authorized,
            "credential_probe_authorized": self.credential_probe_authorized,
            "account_probe_authorized": self.account_probe_authorized,
            "release_controls_visible": self.release_controls_visible,
            "deployment_controls_visible": self.deployment_controls_visible,
            "raw_prompt_visible": self.raw_prompt_visible,
            "raw_response_visible": self.raw_response_visible,
            "raw_evidence_body_visible": self.raw_evidence_body_visible,
            "raw_worker_chat_visible": self.raw_worker_chat_visible,
            "pids_visible": self.pids_visible,
            "raw_filesystem_paths_visible": self.raw_filesystem_paths_visible,
        }
        enabled = [name for name, value in forbidden_flags.items() if value]
        if enabled:
            raise ValueError(
                "ReleaseAutonomySnapshot cannot enable unsafe release fields: "
                + ", ".join(enabled)
            )
        if self.prime_export.ready_for_execution:
            raise ValueError("Prime autonomy export must remain non-executable")
        if not self.prime_export.human_gate_required:
            raise ValueError("Prime autonomy export must require a human gate")
        for marker in _DISPLAY_ONLY_GUARDRAILS:
            if marker not in self.guardrails:
                raise ValueError(f"ReleaseAutonomySnapshot missing guardrail: {marker}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe, UI-safe Release harness snapshot."""

        return {
            "ok": True,
            "version": SNAPSHOT_VERSION,
            "source": SNAPSHOT_SOURCE,
            "harness": "Autonomy / Release",
            "summary": (
                "Release harness is display-only. Prime autonomy contributes "
                "non-authority posture and blockers; no release or deployment "
                "execution is exposed."
            ),
            "generated_at": self.generated_at.isoformat(),
            "display_only": self.display_only,
            "mutation_authorized": self.mutation_authorized,
            "release_execution_authorized": self.release_execution_authorized,
            "deployment_authorized": self.deployment_authorized,
            "credential_probe_authorized": self.credential_probe_authorized,
            "account_probe_authorized": self.account_probe_authorized,
            "release_controls_visible": self.release_controls_visible,
            "deployment_controls_visible": self.deployment_controls_visible,
            "raw_prompt_visible": self.raw_prompt_visible,
            "raw_response_visible": self.raw_response_visible,
            "raw_evidence_body_visible": self.raw_evidence_body_visible,
            "raw_worker_chat_visible": self.raw_worker_chat_visible,
            "pids_visible": self.pids_visible,
            "raw_filesystem_paths_visible": self.raw_filesystem_paths_visible,
            "release_posture": {
                "state": "blocked_display_only",
                "release_ready": self.release_ready,
                "human_gate_required": self.prime_export.human_gate_required,
                "ready_for_execution": self.prime_export.ready_for_execution,
                "prime_action_type": self.prime_export.prime_action_type,
                "prime_confidence": self.prime_export.prime_confidence,
                "prime_risk_tier": self.prime_export.prime_risk_tier,
                "prime_target_harness": self.prime_export.prime_target_harness,
                "prime_target_lane": self.prime_export.prime_target_lane,
                "prime_target_project": self.prime_export.prime_target_project,
            },
            "authority_boundary": {
                "autonomous_implementation_authorized": (
                    self.prime_export.autonomous_implementation_authorized
                ),
                "review_clearing_authorized": (
                    self.prime_export.review_clearing_authorized
                ),
                "branch_movement_authorized": (
                    self.prime_export.branch_movement_authorized
                ),
                "live_coding_authority_authorized": (
                    self.prime_export.live_coding_authority_authorized
                ),
                "relay_bypass_authorized": self.prime_export.relay_bypass_authorized,
            },
            "validation_projection": {
                "validation_level": self.prime_export.validation_level,
                "direct_dispatch_id": self.prime_export.direct_dispatch_id,
                "variant_label_count": len(self.prime_export.variant_labels),
                "transport_cleared": self.prime_export.transport_cleared,
                "serialization_only": self.prime_export.serialization_only,
                "validation_evidence_ref": self.prime_export.validation_evidence_ref,
                "external_review_evidence_ref": (
                    self.prime_export.external_review_evidence_ref or "none"
                ),
            },
            "blockers": sorted(
                set(self.prime_export.no_authority_blockers)
                | set(self.prime_export.prime_blockers)
                | {
                    "release_display_only_no_execution",
                    "release_display_only_no_deployment",
                    "release_display_only_no_credentials_or_account_probe",
                }
            ),
            "beacon_advisory": {
                "harness_id": self.prime_export.beacon_harness_id,
                "advisory_type": self.prime_export.beacon_advisory_type,
                "blocker_count": len(self.prime_export.beacon_blockers),
                "evidence_count": len(self.prime_export.beacon_evidence),
            },
            "guardrails": list(self.guardrails),
        }


def release_autonomy_snapshot(*, now: datetime | None = None) -> dict[str, Any]:
    """Build the display-only Autonomy/Release snapshot for the bridge/UI."""

    generated_at = _as_utc(now or datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc))
    disposition = bind_deepseek_validation_disposition(
        deepseek_candidate_metadata_preset("fast")
    )
    if disposition is None:
        raise RuntimeError("DeepSeek validation disposition unavailable")
    prime_export = build_deepseek_validation_runtime_state_export(
        disposition,
        now=generated_at,
    )
    return ReleaseAutonomySnapshot(
        generated_at=generated_at,
        prime_export=prime_export,
    ).to_dict()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def main() -> None:
    import json

    print(json.dumps(release_autonomy_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
