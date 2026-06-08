"""Backend snapshot for Compass project-context logic shown in the harness UI."""

from meridian_core.compass import (
    ProjectBoundsRequest,
    ProjectHandoffRequest,
    ProjectScopeCandidate,
    define_project,
    evaluate_cross_project_handoff,
    evaluate_project_bounds,
    evaluate_project_difference,
    evaluate_project_identity,
    evaluate_project_scope,
    project_difference_profile_from_definition,
    project_identity_candidate_from_definition,
)

SNAPSHOT_VERSION = "compass-domain-v1"


def _reviewed_runtime_sample() -> dict:
    """Build display-safe sample decisions from the reviewed Compass runtime."""
    project = define_project(
        project_id="meridian-v2",
        title="Meridian V2",
        outcome="Prime can coordinate V2 harness runtime without project drift.",
        context=(
            "Compass owns project identity and bearing.",
            "V2 runtime stays pure until reviewed.",
        ),
        artifacts=(
            "docs/v2-progress-tracker.md",
            "meridian_core/compass.py",
        ),
        objectives=(
            "Define project runtime identity.",
            "Keep repo, venture, and session relationships explicit.",
        ),
        tasks=(
            "Create pure domain object.",
            "Add deterministic serialization tests.",
        ),
        proof_trail=(
            "docs/harness-stage-checklist.md#Compass",
            "tests/test_compass.py",
        ),
        repo_refs=("repo:meridian",),
        venture_refs=("venture:meridian",),
        session_refs=("session:build-4-compass",),
    )
    target_project = define_project(
        project_id="meridian-ui-review",
        title="Meridian UI Review",
        outcome="Expose reviewed backend capabilities in the Electron UI.",
        context=("UI renders reviewed backend summaries only.",),
        artifacts=("index.html", "scripts/meridian-model-bridge.js"),
        objectives=("Keep Electron UI caught up with reviewed backend state.",),
        tasks=("Render display-only proof surfaces.",),
        proof_trail=("tests/test_bifrost_cockpit.py",),
        repo_refs=("repo:meridian",),
        venture_refs=("venture:meridian",),
        session_refs=("session:ui-catchup",),
    )
    scope_candidate = ProjectScopeCandidate(
        project_id="meridian-v2",
        subject_kind="artifact",
        subject_ref="meridian_core/compass.py",
        evidence_refs=("proof:scope-check",),
    )
    bounds_request = ProjectBoundsRequest(
        project_id="meridian-v2",
        request_kind="feature_change",
        request_ref="request:compass-runtime-panel",
        candidates=(scope_candidate,),
        repo_refs=("repo:meridian",),
        venture_refs=("venture:meridian",),
        session_refs=("session:build-4-compass",),
        evidence_refs=("proof:bounds-check",),
    )
    source_profile = project_difference_profile_from_definition(
        project,
        mission_bearing="Ship Meridian V2 project-boundary runtime.",
        memory_pins=("memory:compass-definition-runtime",),
        blockers=("blocker:none",),
        proof_expectations=("pytest:tests/test_compass.py",),
    )
    target_profile = project_difference_profile_from_definition(
        target_project,
        mission_bearing="Expose reviewed backend capability state in Electron.",
        memory_pins=("memory:electron-ui-catchup",),
        blockers=("blocker:none",),
        proof_expectations=("pytest:tests/test_bifrost_cockpit.py",),
    )
    handoff_request = ProjectHandoffRequest(
        source_project_id="meridian-v2",
        target_project_id="meridian-ui-review",
        reason_category="proof_packet",
        payload_type="proof_refs",
        payload_summary_refs=("proof-summary:compass-project-difference",),
        evidence_refs=("proof:cross-project-handoff",),
        approval_required=True,
        approval_refs=("approval:codex-review-cleared",),
        raw_context_blocked=True,
    )
    return {
        "project_definition": project.to_dict(),
        "identity": evaluate_project_identity(
            project_identity_candidate_from_definition(
                project,
                mission_bearing="Ship Meridian V2 project-boundary runtime.",
                evidence_refs=("proof:identity-check",),
            )
        ).to_dict(),
        "scope": evaluate_project_scope(project, scope_candidate).to_dict(),
        "bounds": evaluate_project_bounds(project, bounds_request).to_dict(),
        "difference": evaluate_project_difference(
            source_profile,
            target_profile,
            evidence_refs=("proof:project-difference",),
        ).to_dict(),
        "handoff": evaluate_cross_project_handoff(
            source_profile,
            target_profile,
            handoff_request,
        ).to_dict(),
    }


def compass_logic_snapshot() -> dict:
    """Return the Compass capability list used by Bifrost's visible harness."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.compass / meridian_core.compass_logic_snapshot",
        "harness": "Compass",
        "summary": "Compass owns project context, mission bearing, and portfolio boundary logic. Vulcan owns live session lifecycle and User Session target behavior.",
        "display_only": True,
        "mutation_authorized": False,
        "runtime_sample": _reviewed_runtime_sample(),
        "capabilitySections": [
            {
                "title": "Compass Job",
                "summary": "Keep Prime oriented to the selected project, mission bearing, and portfolio boundary.",
                "rows": [
                    {"key": "owns", "value": "project definition, project bounds, project scope, mission bearing, project-scoped surface focus"},
                    {"key": "does not own", "value": "model routing, User Session target routing, archive/delete actions"},
                    {"key": "drift guard", "value": "visible project context must match prompt metadata before Prime sends"},
                ],
            },
            {
                "title": "Project Definition Logic",
                "summary": "A project is a bounded body of work with its own outcome, context, artifacts, and proof trail.",
                "rows": [
                    {"key": "project", "value": "organized body of work with concrete outcome, local path/repo when applicable, initiatives, objectives, tasks, and next moves"},
                    {"key": "not a session", "value": "sessions are Vulcan runtime containers that may work on a project but do not define it"},
                    {"key": "not a repo", "value": "a repo/path can host one or more project efforts; filesystem location is evidence, not identity"},
                    {"key": "not a venture", "value": "a venture is a higher-level value/business/audience container that may contain projects"},
                ],
            },
            {
                "title": "Bounds and Scope Logic",
                "summary": "Compass decides what belongs inside a project and what must stay outside or be linked explicitly.",
                "rows": [
                    {"key": "inside bounds", "value": "mission, objectives, backlog, relevant memory, active artifacts, proof, open blockers, current risk posture"},
                    {"key": "outside bounds", "value": "other-project raw transcripts, unrelated repo state, vendor/account state, session lifecycle commands"},
                    {"key": "scope proof", "value": "project-scoped surfaces must name project id/title and evidence refs before acting"},
                    {"key": "ambiguity behavior", "value": "unclear scope becomes a visible Compass question, not hidden context mixing"},
                ],
            },
            {
                "title": "Project Difference Logic",
                "summary": "Compass distinguishes projects by purpose, artifacts, boundaries, active decisions, and proof expectations.",
                "rows": [
                    {"key": "identity", "value": "project id/title plus mission/bearing, not display label alone"},
                    {"key": "differentiators", "value": "objective set, acceptance criteria, memory pins, file/artifact roots, active blockers, proof requirements"},
                    {"key": "collision guard", "value": "same repo or same venture does not imply same project"},
                ],
            },
            {
                "title": "Cross-Project Communication Logic",
                "summary": "Projects may exchange summaries, decisions, and evidence, but not raw context by default.",
                "rows": [
                    {"key": "allowed", "value": "typed handoff summary, explicit evidence links, reusable decision, durable memory entry, dependency notice"},
                    {"key": "blocked by default", "value": "raw worker chat, hidden prompt replay, unrelated backlog import, automatic session retarget"},
                    {"key": "protocol", "value": "Compass marks source project, target project, reason, payload type, proof/evidence refs, and approval need"},
                    {"key": "review handoff", "value": "Aegis/Crosscheck may require proof before a project-to-project dependency becomes accepted context"},
                ],
            },
            {
                "title": "Project Selector Logic",
                "summary": "The Projects selector chooses Prime's project context without changing the User Session target.",
                "rows": [
                    {"key": "selector source", "value": "visible Prime panel Projects dropdown"},
                    {"key": "sort policy", "value": "placeholder first, real project names alphabetical"},
                    {"key": "persistence", "value": "meridian.session.project stores last selected project"},
                ],
            },
            {
                "title": "Prime Prompt Context",
                "summary": "Prime prompt dispatch carries the selected Compass project as metadata.",
                "rows": [
                    {"key": "payload field", "value": "projectContext"},
                    {"key": "recent-call field", "value": "projectContext"},
                    {"key": "default", "value": "Meridian when no explicit project is selected"},
                ],
            },
            {
                "title": "Portfolio Boundary",
                "summary": "Compass keeps project, repository, initiative, and venture concepts distinct.",
                "rows": [
                    {"key": "project", "value": "UI context selected for Prime and project-scoped surfaces"},
                    {"key": "repository", "value": "filesystem/git location; not automatically equal to project"},
                    {"key": "initiative/venture", "value": "higher-level portfolio concepts not selected by this dropdown"},
                ],
            },
            {
                "title": "Current Limits",
                "summary": "Compass is visible for project context and reviewed runtime decisions now; live project mutation and switch guards remain planned.",
                "rows": [
                    {"key": "not wired yet", "value": "dirty-switch confirmation, backlog/review surface refresh, live project mutation controls"},
                    {"key": "safe behavior", "value": "missing metadata is reported as unavailable rather than invented"},
                    {"key": "next proof", "value": "future Compass backend state should replace static project option seed when project registry is reviewed"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(compass_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
