"""Tests for V2.5 tool and browser dry-run contracts."""

from __future__ import annotations

import builtins
import subprocess

from meridian_core.dry_run_contracts import (
    BrowserNavigationInput,
    DryRunReviewState,
    DryRunSeverity,
    ScreenshotEvidenceInput,
    ToolActionInput,
    ToolFailureInput,
    VisualDiffInput,
    VisualDiffStatus,
    build_browser_evidence,
    build_tool_dry_run_plan,
)


def test_tool_dry_run_does_not_execute_tools_io_or_external_mutation(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run contracts must not execute side effects")

    monkeypatch.setattr(builtins, "open", fail_if_called)
    monkeypatch.setattr(subprocess, "run", fail_if_called)

    plan = build_tool_dry_run_plan(
        "plan:non-execution",
        (
            ToolActionInput(
                tool_name="shell",
                action_label="would run command",
                target_ref="artifact:repo",
                mutation_kind="write",
                reversible=True,
            ),
        ),
    )

    display = plan.to_display_dict()
    assert display["dry_run_only"] is True
    assert display["reversible_actions"][0]["would_execute"] is False
    assert display["reversible_actions"][0]["external_mutation_blocked"] is True


def test_reversible_action_plan_is_display_ready_with_review_affordance():
    plan = build_tool_dry_run_plan(
        "plan:repair-preview",
        (
            ToolActionInput(
                tool_name="apply_patch",
                action_label="update backend contract",
                target_ref="artifact:dry-run-contract",
                mutation_kind="file_patch",
                reversible=True,
                rollback_plan_ref="rollback:dry-run-contract",
            ),
        ),
    )

    action = plan.reversible_actions[0]
    assert action.reversible is True
    assert action.rollback_plan_ref == "rollback:dry-run-contract"
    assert plan.review.state is DryRunReviewState.READY
    assert plan.review.can_approve is True
    assert plan.review.requires_human_review is False
    assert plan.to_display_dict()["reversible_actions"][0]["mutation_kind"] == "file_patch"


def test_unsafe_navigation_is_blocked_without_echoing_target_url():
    unsafe_url = "javascript:fetch('https://example.test/private?token=super-secret-token-123456')"
    plan = build_tool_dry_run_plan(
        "plan:unsafe-navigation",
        (),
        navigations=(
            BrowserNavigationInput(
                request_id="nav:private-token",
                requested_url=unsafe_url,
            ),
        ),
    )

    display = plan.to_display_dict()
    assert plan.safe_navigation.status is DryRunReviewState.BLOCKED
    assert plan.safe_navigation.blocked_schemes == ("javascript",)
    assert display["safe_navigation"]["warning_count"] == 1
    assert "blocked by dry-run policy" in display["safe_navigation"]["warnings"][0]
    assert "super-secret-token" not in str(display)
    assert "javascript:fetch" not in str(display)


def test_browser_evidence_displays_screenshot_links_and_visual_diff_shape():
    evidence = build_browser_evidence(
        "browser-evidence:checkout",
        navigations=(
            BrowserNavigationInput(
                request_id="nav:checkout",
                requested_url="https://example.test/checkout",
            ),
        ),
        screenshots=(
            ScreenshotEvidenceInput(
                evidence_ref="screenshot:checkout-desktop",
                thumbnail_ref="thumbnail:checkout-desktop",
                viewport_label="desktop",
            ),
        ),
        visual_diff=VisualDiffInput(
            baseline_ref="visual:baseline",
            candidate_ref="visual:candidate",
            diff_ref="visual:diff",
            changed_region_count=2,
            threshold=0.05,
        ),
    )

    display = evidence.to_display_dict()
    assert evidence.dry_run_only is True
    assert display["screenshot_links"][0] == {
        "evidence_ref": "screenshot:checkout-desktop",
        "thumbnail_ref": "thumbnail:checkout-desktop",
        "viewport_label": "desktop",
        "raw_content_available": False,
    }
    assert evidence.visual_diff.status is VisualDiffStatus.CHANGED
    assert display["visual_diff"]["changed_region_count"] == 2
    assert display["review"]["state"] == "needs_review"


def test_tool_failure_routing_record_is_display_safe_and_deterministic():
    plan = build_tool_dry_run_plan(
        "plan:failure-routing",
        (),
        failure_routes=(
            ToolFailureInput(
                route_id="route:model-timeout",
                failure_kind="timeout",
                severity=DryRunSeverity.WARNING,
                retryable=True,
                next_route="retry_then_manual_review",
                evidence_ref="evidence:timeout-summary",
            ),
        ),
    )

    route = plan.failure_routing[0]
    assert route.severity is DryRunSeverity.WARNING
    assert route.retryable is True
    assert route.next_route == "retry_then_manual_review"
    assert route.to_display_dict() == {
        "route_ref": "route:model-timeout",
        "failure_kind": "timeout",
        "severity": "warning",
        "retryable": True,
        "next_route": "retry_then_manual_review",
        "evidence_ref": "evidence:timeout-summary",
    }


def test_display_records_do_not_leak_local_paths_raw_content_or_secret_values():
    raw_path = r"C:\Users\scott\Code\Meridian\.env"
    raw_content = "raw content: provider response includes password=hidden-value-123456"
    browser = build_browser_evidence(
        raw_path,
        screenshots=(
            ScreenshotEvidenceInput(
                evidence_ref=raw_path,
                thumbnail_ref=raw_content,
                viewport_label=raw_content,
            ),
        ),
        visual_diff=VisualDiffInput(
            baseline_ref=raw_path,
            candidate_ref=raw_content,
            diff_ref=r"C:\Users\scott\Code\Meridian\diff.png",
        ),
    )
    plan = build_tool_dry_run_plan(
        raw_path,
        (
            ToolActionInput(
                tool_name=raw_content,
                action_label=raw_content,
                target_ref=raw_path,
                rollback_plan_ref=raw_path,
            ),
        ),
        failure_routes=(
            ToolFailureInput(
                route_id=raw_path,
                failure_kind=raw_content,
                next_route=raw_content,
                evidence_ref=raw_path,
            ),
        ),
    )

    display_text = f"{browser.to_display_dict()} {plan.to_display_dict()}"
    assert r"C:\Users\scott" not in display_text
    assert "provider response" not in display_text
    assert "hidden-value" not in display_text
    assert "password=" not in display_text
    assert "raw content" not in display_text
    assert "browser-evidence:unsafe:" in display_text
    assert "target:unsafe:" in display_text
