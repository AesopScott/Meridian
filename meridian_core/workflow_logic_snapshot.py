"""Backend snapshot for Workflow Runtime Logic shown in the harness UI."""

from __future__ import annotations

import json

from .session_lifecycle import SessionAction, WorkflowHeartbeatStatus, WorkflowResultKind

SNAPSHOT_VERSION = "workflow-runtime-v1"


def _enum_rows(enum_type: type) -> list[dict[str, str]]:
    return [{"key": item.name.lower(), "value": item.value} for item in enum_type]


def workflow_logic_snapshot() -> dict:
    """Return the Workflow capability list used by Bifrost's visible harness."""
    heartbeat_values = ", ".join(item.value for item in WorkflowHeartbeatStatus)
    result_values = ", ".join(item.value for item in WorkflowResultKind)
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.workflow_logic_snapshot.workflow_logic_snapshot",
        "harness": "Workflow / Sub-agents",
        "summary": (
            "Workflow owns bounded work-order execution shape, typed summaries, heartbeat visibility, "
            "restart/resteer advice, and prompt-drag boundaries. It returns structured results; it does not act as Prime."
        ),
        "sourceRefs": [
            "docs/workflow-subagent-harness-contract.md",
            "docs/workflows-subagent-harness-architecture.md",
            "meridian_core.session_lifecycle.summarize_workflow_work_order_recovery",
        ],
        "capabilitySections": [
            {
                "title": "Workflow Job",
                "summary": "Move bounded multi-step harness work into separate contexts and return typed summaries.",
                "rows": [
                    {"key": "owns", "value": "work orders, input packets, heartbeats, result summaries, error summaries, restart/resteer advice"},
                    {"key": "does not own", "value": "Prime deliberation, global state mutation, hidden tool escalation, raw transcript transfer"},
                    {"key": "drift guard", "value": "Prime coordinates; Workflow sub-agents execute bounded work and return structured evidence"},
                ],
            },
            {
                "title": "Work Order Logic",
                "summary": "A workflow starts only from a bounded, typed work order.",
                "rows": [
                    {"key": "required identity", "value": "work_order_id, harness, action, intent, expected_result_shape"},
                    {"key": "budget", "value": "risk tier, prompt budget, time budget, hard timeout"},
                    {"key": "scope", "value": "allowed tools, allowed paths, forbidden paths, gate context"},
                    {"key": "immutability", "value": "restart keeps the same work order; resteer creates a new one from structured guidance"},
                ],
            },
            {
                "title": "Input Boundary Logic",
                "summary": "The input packet is the only context a sub-agent receives.",
                "rows": [
                    {"key": "allowed", "value": "project, goal summary, typed inputs, allowed tools, allowed paths, gate context"},
                    {"key": "blocked", "value": "implicit Prime memory, raw user chat, unrelated project context, unlisted tools"},
                    {"key": "prompt budget", "value": "Relay budget plan caps context inside the sub-agent's own model calls"},
                ],
            },
            {
                "title": "Heartbeat and Result Logic",
                "summary": "Heartbeat is operational liveness; result/error summaries are the only final return shapes.",
                "rows": [
                    {"key": "heartbeat statuses", "value": heartbeat_values},
                    {"key": "result kinds", "value": result_values},
                    {"key": "success", "value": "WorkflowResultSummary with typed outputs, proof trail, tokens used, time used"},
                    {"key": "failure", "value": "WorkflowErrorSummary with typed failure kind, partial outputs, and optional resteer request"},
                ],
            },
            {
                "title": "Recovery Advice Logic",
                "summary": "Session Lifecycle currently provides display-safe workflow heartbeat/result recovery advice.",
                "rows": [
                    {"key": "fresh + pending", "value": "continue watching the bounded work order"},
                    {"key": "stale or missing", "value": "restart the same work order in a fresh bounded context"},
                    {"key": "succeeded", "value": "archive or record the typed result summary"},
                    {"key": "resteer requested", "value": "issue a new bounded work order from structured guidance"},
                    {"key": "gated/denied/error", "value": "route to human/Aegis gate before recovery proceeds"},
                ],
            },
            {
                "title": "Prompt-Drag Boundary",
                "summary": "Workflow protects Prime from raw intermediate context.",
                "rows": [
                    {"key": "never returns", "value": "raw transcripts, raw file content, raw search results, raw logs, heartbeat history"},
                    {"key": "eligible for Prime", "value": "summary, result shape, typed outputs, proof references when Aegis policy allows"},
                    {"key": "more context", "value": "issue a narrower follow-up work order instead of widening the result schema"},
                ],
            },
            {
                "title": "Cross-Harness Relationship Logic",
                "summary": "Workflow is a cross-cutting execution shape for bounded harness work.",
                "rows": [
                    {"key": "Prime", "value": "issues work orders, watches latest heartbeat line, accepts typed results"},
                    {"key": "Relay", "value": "carries prompt budgets and can run model dispatch inside bounded workflow contexts"},
                    {"key": "Aegis", "value": "gates proof, result promotion, and policy violations"},
                    {"key": "Bifrost", "value": "renders workflow status and result summaries without raw transcripts"},
                    {"key": "Vulcan", "value": "operates session lifecycle, restart, resteer, and recovery for workflow contexts"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "This panel is display-only and does not spawn, stop, restart, or resteer workflow sessions.",
                "rows": [
                    {"key": "display", "value": "backend snapshot only"},
                    {"key": "blocked", "value": "no workflow dispatch, no live session mutation, no durable promotion"},
                    {"key": "future backend", "value": "workflow_dispatch runtime remains V2 implementation work"},
                ],
            },
        ],
        "enumValues": {
            "heartbeat": _enum_rows(WorkflowHeartbeatStatus),
            "result": _enum_rows(WorkflowResultKind),
            "recoveryActions": _enum_rows(SessionAction),
        },
    }


def main() -> None:
    print(json.dumps(workflow_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
