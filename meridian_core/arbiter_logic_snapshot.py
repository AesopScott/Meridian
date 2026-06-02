"""Backend snapshot for Arbiter Review Console logic shown in the harness UI."""

from __future__ import annotations

import json

from .review_console import (
    ReviewConsoleAction,
    ReviewConsoleItemStatus,
    ReviewConsoleItemType,
    ReviewConsoleQueue,
    ReviewConsoleSeverity,
    make_approval_gate,
    make_cross_check_item,
    make_plan_review_item,
    make_prompt_metrics_finding,
    make_system_finding,
)
from .prompt_metrics import PromptMetricSummary, PromptPerformanceStatus

SNAPSHOT_VERSION = "arbiter-review-console-v1"


def _enum_rows(enum_type: type) -> list[dict[str, str]]:
    return [{"key": item.name.lower(), "value": item.value} for item in enum_type]


def _item_rows() -> list[dict[str, str]]:
    items = [
        make_cross_check_item("arbiter-cross-check", "Cross-check finding", "evidence"),
        make_plan_review_item("arbiter-plan", "Plan review", "proposed plan"),
        make_approval_gate("arbiter-gate", "Approval gate", "requires user decision"),
        make_system_finding("arbiter-system", "System finding", "diagnostic"),
    ]
    return [
        {
            "key": item.item_type.value,
            "value": (
                f"promptable={item.promptable}; "
                f"requires_response={item.requires_response}; "
                f"automatic={item.is_automatic}; "
                f"actions={','.join(action.value for action in item.suggested_actions)}"
            ),
        }
        for item in items
    ]


def _queue_rows() -> list[dict[str, str]]:
    queue = ReviewConsoleQueue()
    queue.enqueue(make_system_finding("system", "System note", "informational"))
    queue.enqueue(make_approval_gate("gate", "Gate", "decision needed"))
    queue.enqueue(make_cross_check_item("cross", "Cross-check", "inspectable"))
    gate_ids = [item.id for item in queue.pending_gates()]
    info_ids = [item.id for item in queue.informational()]
    response = queue.respond("gate", ReviewConsoleAction.APPROVE, "visible approval")
    queue.acknowledge("cross")
    return [
        {"key": "pending order", "value": "insertion sequence; no hidden priority reshuffle"},
        {"key": "pending gates", "value": ", ".join(gate_ids)},
        {"key": "informational", "value": ", ".join(info_ids)},
        {"key": "gate response", "value": f"{response.action.value} -> {queue.require('gate').status.value}"},
        {"key": "acknowledge response", "value": queue.require("cross").status.value},
    ]


def _prompt_metrics_rows() -> list[dict[str, str]]:
    summary = PromptMetricSummary(
        sample_count=3,
        avg_prompt_tokens=420.0,
        avg_construction_time_ms=18.5,
        avg_total_response_time_ms=310.0,
        avg_time_to_first_token_ms=None,
        avg_overhead_delta_ms=42.0,
        status=PromptPerformanceStatus.WATCH,
    )
    item = make_prompt_metrics_finding("prompt-metrics", summary)
    return [
        {"key": "item type", "value": item.item_type.value},
        {"key": "severity", "value": item.severity.value},
        {"key": "promptable", "value": str(item.promptable).lower()},
        {"key": "requires response", "value": str(item.requires_response).lower()},
        {"key": "content", "value": item.content},
    ]


def arbiter_logic_snapshot() -> dict:
    """Return Arbiter's display-only Review Console logic snapshot."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.arbiter_logic_snapshot.arbiter_logic_snapshot",
        "harness": "Arbiter / Reviews",
        "summary": (
            "Arbiter owns promptable review items, approval gates, finding disposition, "
            "and deterministic Review Console queue visibility without moving code or clearing reviews from the UI."
        ),
        "capabilitySections": [
            {
                "title": "Arbiter Job",
                "summary": "Separate review visibility from execution so Prime can expose decisions without inventing clearance.",
                "rows": [
                    {"key": "owns", "value": "review item shape, promptability, allowed actions, gate visibility, response status"},
                    {"key": "does not own", "value": "branch movement, shared main writes, cherry-picks, review pass fabrication"},
                    {"key": "drift guard", "value": "Bifrost renders backend Review Console truth and never mutates review state from this panel"},
                ],
            },
            {
                "title": "Review Item Shape",
                "summary": "Every surfaced item has typed identity, severity, promptability, response need, actions, status, and sequence.",
                "rows": _item_rows(),
            },
            {
                "title": "Item Type Logic",
                "summary": "Review Console item types define why the item exists before any response is requested.",
                "rows": _enum_rows(ReviewConsoleItemType),
            },
            {
                "title": "Severity and Status Logic",
                "summary": "Severity describes risk; status describes disposition. They are separate signals.",
                "rows": [
                    {"key": "severities", "value": ", ".join(item.value for item in ReviewConsoleSeverity)},
                    {"key": "statuses", "value": ", ".join(item.value for item in ReviewConsoleItemStatus)},
                    {"key": "actions", "value": ", ".join(item.value for item in ReviewConsoleAction)},
                ],
            },
            {
                "title": "Pending Gate Logic",
                "summary": "Only pending items that require response block Prime from proceeding.",
                "rows": _queue_rows(),
            },
            {
                "title": "Prompt Metrics Finding Logic",
                "summary": "Prompt metrics become automatic system findings; they inform review but do not ask the user to approve.",
                "rows": _prompt_metrics_rows(),
            },
            {
                "title": "Runtime Boundary",
                "summary": "The Arbiter panel is display-only until a separate write-through Review Console backend exists.",
                "rows": [
                    {"key": "display", "value": "backend snapshot only"},
                    {"key": "blocked", "value": "no approve/reject/modify controls are emitted by this runtime logic panel"},
                    {"key": "review proof", "value": "review pass/finding provenance must come from review lanes, not this UI"},
                ],
            },
        ],
    }


def main() -> None:
    print(json.dumps(arbiter_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
