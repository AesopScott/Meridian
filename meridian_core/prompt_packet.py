"""
Relay Prompt Packet domain model.

A PromptPacket is a validated, immutable bundle of prompt data ready for
dispatch to a worker model. Validation runs in __post_init__ — invalid
packets cannot be constructed, whether via build_prompt_packet() or directly.

Only serialized_prompt is ever sent to the model. All other fields are
metadata for Prime, Metrics, and logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .prompt_budget import PromptBudgetPlan


class PromptPacketValidationError(ValueError):
    """Raised when a PromptPacket fails one or more validation checks."""


@dataclass(frozen=True)
class PromptPacket:
    """
    Validated, immutable bundle of prompt data ready for Relay dispatch.

    Validation runs at construction time via __post_init__. source_lineage
    is always stored as an immutable MappingProxyType regardless of input type.
    Only serialized_prompt is sent to the model; all other fields are metadata.
    """

    packet_id: str
    serialized_prompt: str
    prompt_tokens: int
    budget: PromptBudgetPlan
    source_lineage: MappingProxyType  # str -> int, immutable; dict inputs converted
    construction_time_ms: float

    def __post_init__(self) -> None:
        # Convert source_lineage to immutable mapping (accepts dict or MappingProxyType)
        object.__setattr__(
            self,
            "source_lineage",
            MappingProxyType(dict(self.source_lineage)),
        )

        errors: list[str] = []

        if not isinstance(self.serialized_prompt, str):
            errors.append(
                f"Prompt must be a string, got {type(self.serialized_prompt).__name__}"
            )
        elif not self.serialized_prompt:
            errors.append("Prompt is empty or invalid type")

        if self.prompt_tokens < 0:
            errors.append(f"Prompt tokens {self.prompt_tokens} is negative")

        if self.prompt_tokens > self.budget.max_context_tokens:
            errors.append(
                f"Prompt {self.prompt_tokens} tokens exceeds budget {self.budget.max_context_tokens}"
            )

        for source, count in self.source_lineage.items():
            if source not in self.budget.allowed_sources:
                errors.append(f"Source '{source}' not in allowed_sources")
            if count < 0:
                errors.append(f"Lineage token count for '{source}' is negative")

        lineage_total = sum(self.source_lineage.values())
        if lineage_total > self.prompt_tokens:
            errors.append(
                f"Lineage {lineage_total} exceeds packet {self.prompt_tokens} tokens"
            )

        if self.construction_time_ms < 0:
            errors.append(f"Construction time {self.construction_time_ms} is negative")

        if errors:
            raise PromptPacketValidationError("; ".join(errors))

    def model_payload(self) -> str:
        """Return the model-facing prompt payload — only serialized_prompt, no metadata."""
        return self.serialized_prompt


def build_prompt_packet(
    *,
    packet_id: str,
    serialized_prompt: str,
    prompt_tokens: int,
    budget: PromptBudgetPlan,
    source_lineage: dict[str, int],
    construction_time_ms: float,
) -> PromptPacket:
    """
    Ergonomic helper to build a validated PromptPacket.

    Accepts a plain dict for source_lineage; the constructor converts it to
    an immutable MappingProxyType. Raises PromptPacketValidationError on
    any constraint violation.
    """
    return PromptPacket(
        packet_id=packet_id,
        serialized_prompt=serialized_prompt,
        prompt_tokens=prompt_tokens,
        budget=budget,
        source_lineage=source_lineage,
        construction_time_ms=construction_time_ms,
    )
