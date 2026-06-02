"""Prime runtime decision contract and context assembly.

This module is backend-only. It defines the typed packet Prime can expose to
Bifrost later without letting the UI invent orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class PrimeDecisionStatus(Enum):
    """Executable state for Prime's next runtime decision."""

    EXECUTABLE = "executable"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass(frozen=True)
class PrimeSourceRef:
    """A backend source Prime used to assemble its decision context."""

    harness: str
    source: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "harness": self.harness,
            "source": self.source,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class PrimeProof:
    """Visible proof item for Prime's no-drift audit trail."""

    question: str
    answer: str
    source: str
    invalidates_when: str

    def to_dict(self) -> dict[str, str]:
        return {
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "invalidatesWhen": self.invalidates_when,
        }


@dataclass(frozen=True)
class PrimeRuntimeContext:
    """Backend context packet Prime consumes before choosing an action."""

    project_id: str
    project_summary: str
    session_state: str
    relay_route_summary: str
    risk_summary: str
    source_refs: tuple[PrimeSourceRef, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "projectSummary": self.project_summary,
            "sessionState": self.session_state,
            "relayRouteSummary": self.relay_route_summary,
            "riskSummary": self.risk_summary,
            "sourceRefs": [source.to_dict() for source in self.source_refs],
        }


@dataclass(frozen=True)
class PrimeDecision:
    """The single backend decision object Prime exposes per interaction."""

    decision_id: str
    status: PrimeDecisionStatus
    owner_harness: str
    action: str
    why: str
    risk: str
    context: PrimeRuntimeContext
    proof: tuple[PrimeProof, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    visible_to_scott: tuple[str, ...] = field(default_factory=tuple)

    def is_executable(self) -> bool:
        return self.status == PrimeDecisionStatus.EXECUTABLE and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "status": self.status.value,
            "ownerHarness": self.owner_harness,
            "action": self.action,
            "why": self.why,
            "risk": self.risk,
            "context": self.context.to_dict(),
            "proof": [item.to_dict() for item in self.proof],
            "blockers": list(self.blockers),
            "visibleToScott": list(self.visible_to_scott),
            "executable": self.is_executable(),
        }


def _first_section_summary(snapshot: Mapping[str, Any], fallback: str) -> str:
    sections = snapshot.get("capabilitySections")
    if isinstance(sections, list) and sections:
        section = sections[0]
        if isinstance(section, Mapping):
            summary = section.get("summary")
            if isinstance(summary, str) and summary:
                return summary
    summary = snapshot.get("summary")
    return summary if isinstance(summary, str) and summary else fallback


def assemble_prime_runtime_context(
    *,
    compass_snapshot: Mapping[str, Any],
    vulcan_snapshot: Mapping[str, Any],
    relay_snapshot: Mapping[str, Any],
    project_id: str = "Meridian",
    risk_summary: str = "Aegis proof/risk gate unavailable; treat as safe read-only until wired.",
) -> PrimeRuntimeContext:
    """Assemble Prime context from backend harness snapshots only."""

    compass_source = str(compass_snapshot.get("source") or "unknown")
    vulcan_source = str(vulcan_snapshot.get("source") or "unknown")
    relay_source = str(relay_snapshot.get("source") or "unknown")

    return PrimeRuntimeContext(
        project_id=project_id,
        project_summary=_first_section_summary(
            compass_snapshot,
            "Compass project context unavailable.",
        ),
        session_state=_first_section_summary(
            vulcan_snapshot,
            "Vulcan session lifecycle unavailable.",
        ),
        relay_route_summary=_first_section_summary(
            relay_snapshot,
            "Relay model route unavailable.",
        ),
        risk_summary=risk_summary,
        source_refs=(
            PrimeSourceRef("Compass", compass_source, "project bounds and scope"),
            PrimeSourceRef("Vulcan", vulcan_source, "session lifecycle state"),
            PrimeSourceRef("Relay", relay_source, "model route and access logic"),
            PrimeSourceRef("Aegis", "pending", "proof/risk gate placeholder"),
        ),
    )


def make_prime_decision(
    *,
    context: PrimeRuntimeContext,
    owner_harness: str = "Prime",
    action: str = "inspect_context",
    why: str = "Prime can inspect assembled backend context before UI rendering.",
    risk: str = "safe_read_only",
    status: PrimeDecisionStatus = PrimeDecisionStatus.EXECUTABLE,
    blockers: tuple[str, ...] = (),
) -> PrimeDecision:
    """Create a deterministic Prime decision with visible proof."""

    proof = (
        PrimeProof(
            question="Which harness owns the project boundary?",
            answer="Compass supplies project bounds before Prime selects an action.",
            source="Compass",
            invalidates_when="Prime acts without a Compass project source ref.",
        ),
        PrimeProof(
            question="Which harness owns runtime session lifecycle?",
            answer="Vulcan supplies session lifecycle before Prime routes execution.",
            source="Vulcan",
            invalidates_when="Prime changes session state without a Vulcan source ref.",
        ),
        PrimeProof(
            question="Which harness owns model access and routing?",
            answer="Relay supplies model route logic before Prime can ask a model.",
            source="Relay",
            invalidates_when="Prime selects a model/vendor without Relay evidence.",
        ),
    )
    final_status = PrimeDecisionStatus.BLOCKED if blockers else status
    return PrimeDecision(
        decision_id="prime-runtime-decision-v1",
        status=final_status,
        owner_harness=owner_harness,
        action=action,
        why=why,
        risk=risk,
        context=context,
        proof=proof,
        blockers=blockers,
        visible_to_scott=(
            "Prime decision status",
            "owning harness",
            "backend source refs",
            "proof questions and answers",
            "blockers before execution",
        ),
    )
