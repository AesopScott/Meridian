"""Backend snapshot for Compass project-context logic shown in the harness UI."""

SNAPSHOT_VERSION = "compass-domain-v1"


def compass_logic_snapshot() -> dict:
    """Return the Compass capability list used by Bifrost's visible harness."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.compass_logic_snapshot.compass_logic_snapshot",
        "harness": "Compass",
        "summary": "Compass owns project context, mission bearing, and portfolio boundary logic. Vulcan owns live session lifecycle and User Session target behavior.",
        "capabilitySections": [
            {
                "title": "Compass Job",
                "summary": "Keep Prime oriented to the selected project, mission bearing, and portfolio boundary.",
                "rows": [
                    {"key": "owns", "value": "active project context, mission bearing, project-scoped surface focus"},
                    {"key": "does not own", "value": "model routing, User Session target routing, archive/delete actions"},
                    {"key": "drift guard", "value": "visible project context must match prompt metadata before Prime sends"},
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
                "summary": "Compass is visible for project context now; deeper project metadata and switch guards remain planned.",
                "rows": [
                    {"key": "not wired yet", "value": "project metadata panel, dirty-switch confirmation, backlog/review surface refresh"},
                    {"key": "safe behavior", "value": "missing metadata is reported as unavailable rather than invented"},
                    {"key": "next proof", "value": "future Compass backend state should replace static project option seed"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(compass_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
