"""Backend snapshot for Vulcan Session Lifecycle logic shown in the harness UI."""

SNAPSHOT_VERSION = "vulcan-session-lifecycle-v1"


def vulcan_logic_snapshot() -> dict:
    """Return the Vulcan capability list used by Bifrost's visible harness."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot",
        "harness": "Vulcan / Session Lifecycle",
        "summary": "Vulcan owns live session lifecycle, User Session targets, stale target guards, and session grouping behavior.",
        "capabilitySections": [
            {
                "title": "Vulcan Job",
                "summary": "Keep session targets explicit, live, recoverable, and separate from Compass project context.",
                "rows": [
                    {"key": "owns", "value": "live session target list, target persistence, stale target guard, lifecycle grouping"},
                    {"key": "does not own", "value": "Prime project context, model/vendor routing, portfolio boundary"},
                    {"key": "drift guard", "value": "User prompts require a bridge-confirmed live session target before send"},
                ],
            },
            {
                "title": "User Session Independence",
                "summary": "Changing Compass project context does not select, clear, send to, or retarget a User Session.",
                "rows": [
                    {"key": "User target key", "value": "meridian.user-session.target.v1"},
                    {"key": "project key", "value": "meridian.session.project"},
                    {"key": "routing rule", "value": "User prompts require a bridge-confirmed live session target"},
                ],
            },
            {
                "title": "Project-Aware Session Grouping",
                "summary": "User Sessions remain grouped by project while the active Compass project is visibly marked.",
                "rows": [
                    {"key": "complete list", "value": "all routable live Meridian worktree sessions remain visible"},
                    {"key": "active marker", "value": "matching project optgroup is labeled active project"},
                    {"key": "empty project", "value": "status shows no live sessions for selected project without faking sessions"},
                ],
            },
            {
                "title": "Stale Target Guard",
                "summary": "Closed or unavailable targets are visible blockers, not silent reroutes.",
                "rows": [
                    {"key": "unavailable label", "value": "Selected session unavailable"},
                    {"key": "status text", "value": "selected session unavailable"},
                    {"key": "send behavior", "value": "blocked with readable target error"},
                ],
            },
            {
                "title": "Lifecycle Boundary",
                "summary": "Session lifecycle controls are separate from project selection and archive/delete actions.",
                "rows": [
                    {"key": "project switch", "value": "does not close, archive, delete, or stop a session"},
                    {"key": "reset/reload", "value": "preserve live worktree sessions and archive state"},
                    {"key": "future work", "value": "write-through close, archive-on-close, and stop-before-close remain explicit Vulcan items"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(vulcan_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
