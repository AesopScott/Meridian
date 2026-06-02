"""Backend snapshot for Federation Runtime Logic shown in the harness UI."""

from __future__ import annotations

import json

SNAPSHOT_VERSION = "federation-runtime-v1"


def federation_logic_snapshot() -> dict:
    """Return the Federation capability list used by Bifrost's visible harness."""
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.federation_logic_snapshot.federation_logic_snapshot",
        "harness": "Federation / Network",
        "status": "horizon-only",
        "summary": (
            "Federation defines how one Meridian may eventually discover and request bounded work "
            "from another Meridian. It is consent-first, typed-packet-only, and not a live V2 network runtime."
        ),
        "sourceRefs": [
            "docs/federation-harness-horizon.md",
            "docs/v2-progress-tracker.md",
            "docs/v3-parking-lot.md",
        ],
        "capabilitySections": [
            {
                "title": "Federation Job",
                "summary": "Connect Meridian instances through bounded, consented work handoffs without sharing unsafe state.",
                "rows": [
                    {"key": "owns", "value": "discovery boundaries, consent state, typed handoff packets, refusal/blocker vocabulary"},
                    {"key": "does not own", "value": "raw memory sharing, shared worktrees, shared branches, account credentials, hidden remote execution"},
                    {"key": "scope", "value": "planning-only in V2; runtime networking remains future work"},
                ],
            },
            {
                "title": "Discovery Consent Logic",
                "summary": "Discovery is allowed only through explicit project/user consent and does not imply trust.",
                "rows": [
                    {"key": "safe data", "value": "instance name, user-approved project alias, supported harness capabilities, schema versions"},
                    {"key": "unsafe data", "value": "raw memory stores, raw queue files, worker transcripts, credentials, vendor account state"},
                    {"key": "trust rule", "value": "known instance is not a trusted instance until policy, consent, and proof gates agree"},
                ],
            },
            {
                "title": "Permission Boundary Logic",
                "summary": "Each cross-Meridian action must preserve user, project, and local execution boundaries.",
                "rows": [
                    {"key": "required", "value": "requesting Meridian, responding Meridian, project scope, requested action, allowed files or surfaces"},
                    {"key": "proof", "value": "expected proof packet and human gate when required by risk or policy"},
                    {"key": "blocked", "value": "silent branch movement, shared worktree, hidden account automation, implicit memory import"},
                ],
            },
            {
                "title": "Typed Handoff Logic",
                "summary": "Prime-to-Prime handoffs use small structured packets instead of raw transcripts.",
                "rows": [
                    {"key": "ProjectSummary", "value": "bounded context, current objective, risk tier, active constraints"},
                    {"key": "TaskRequest", "value": "requested work, allowed files, expected output, proof commands"},
                    {"key": "ProofPacket", "value": "evidence, tests, render checks, review verdicts, or blocked reason"},
                    {"key": "ReviewResult", "value": "severity-ordered findings, repair routing, clearance state"},
                    {"key": "RefusalOrBlocker", "value": "why the remote Meridian cannot or should not act"},
                ],
            },
            {
                "title": "Cross-Harness Relationship Logic",
                "summary": "Federation depends on existing harness contracts rather than bypassing them.",
                "rows": [
                    {"key": "Prime", "value": "requests remote work and accepts typed results only"},
                    {"key": "Workflow", "value": "provides bounded work-order shape for remote dispatch"},
                    {"key": "Aegis", "value": "gates risk, proof, permission, and unsafe shared-state attempts"},
                    {"key": "Bifrost", "value": "renders known instances, permission state, handoffs, proof packets, blockers, and events"},
                    {"key": "Vulcan", "value": "keeps local session lifecycle authority for any responding instance"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "This panel is display-only and does not discover instances, authenticate, dispatch, or mutate remote/local state.",
                "rows": [
                    {"key": "display", "value": "backend snapshot only"},
                    {"key": "blocked", "value": "no network protocol, no authentication runtime, no remote execution, no shared mutable state"},
                    {"key": "future backend", "value": "federation networking and identity/trust model remain V3 horizon work"},
                ],
            },
        ],
        "runtimeFlags": {
            "networkProtocol": False,
            "authenticationRuntime": False,
            "remoteExecution": False,
            "sharedMutableState": False,
            "displayOnly": True,
        },
    }


def main() -> None:
    print(json.dumps(federation_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
