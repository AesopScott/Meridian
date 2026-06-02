"""Backend snapshot for Beacon heartbeat and liveness logic shown in the harness UI."""

SNAPSHOT_VERSION = "beacon-liveness-v1"


def beacon_logic_snapshot() -> dict:
    """Return the Beacon capability list used by Bifrost's visible harness."""
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.beacon_logic_snapshot.beacon_logic_snapshot",
        "harness": "Beacon",
        "summary": (
            "Beacon owns display-safe heartbeat, liveness, freshness, and advisory "
            "evidence. It observes runtime state; it does not restart, resteer, spawn, "
            "archive, or move work."
        ),
        "capabilitySections": [
            {
                "title": "Beacon Job",
                "summary": "Turn file freshness and session advisory summaries into visible liveness evidence.",
                "rows": [
                    {"key": "owns", "value": "heartbeat status, sentinel freshness, stale/missing blockers, advisory evidence"},
                    {"key": "does not own", "value": "session command execution, branch movement, worktree mutation, model routing"},
                    {"key": "drift guard", "value": "Beacon observations can block or advise, but cannot execute recovery"},
                ],
            },
            {
                "title": "Liveness Target Logic",
                "summary": "Beacon checks explicit file-backed targets and reports one heartbeat per target.",
                "rows": [
                    {"key": "target fields", "value": "harness id, sentinel path, stale-after seconds"},
                    {"key": "freshness", "value": "modified time compared with the current UTC check time"},
                    {"key": "negative threshold", "value": "invalid and rejected before any heartbeat is emitted"},
                ],
            },
            {
                "title": "Heartbeat Status Logic",
                "summary": "Beacon converts sentinel state into the shared Heartbeat domain model.",
                "rows": [
                    {"key": "alive", "value": "sentinel exists and age is within threshold"},
                    {"key": "stale", "value": "sentinel exists but age exceeds threshold; blocker records age and threshold"},
                    {"key": "failed", "value": "sentinel is missing; blocker records the missing path"},
                    {"key": "current work", "value": "display-safe sentinel path or liveness evidence reference"},
                ],
            },
            {
                "title": "Advisory Evidence Logic",
                "summary": "Beacon converts Vulcan session summaries into display-safe advisory packets.",
                "rows": [
                    {"key": "inputs", "value": "command plan, permission summary, workflow recovery, runtime export, readiness summary, staging record"},
                    {"key": "evidence", "value": "typed key/value facts such as permission state, action, readiness, command kind, and recovery note"},
                    {"key": "human gate", "value": "true when blockers, explicit approval, review gate, or recovery policy require it"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "Beacon is observational. Recovery remains Prime/Vulcan/Aegis-gated.",
                "rows": [
                    {"key": "no live actions", "value": "no restart, resteer, spawn, stop, archive, delete, branch move, or worktree move"},
                    {"key": "safe output", "value": "heartbeats and advisory evidence are serializable and display-only"},
                    {"key": "next backend boundary", "value": "Prime heartbeat input can consume Beacon status after Vulcan live state is ready"},
                ],
            },
            {
                "title": "Cross-Harness Relationship Logic",
                "summary": "Beacon supplies liveness truth without taking over other harness decisions.",
                "rows": [
                    {"key": "Prime", "value": "consumes heartbeat input before choosing orchestration action"},
                    {"key": "Vulcan", "value": "owns session lifecycle state and recovery command plans"},
                    {"key": "Aegis", "value": "gates risky recovery or command plans before execution"},
                    {"key": "Bifrost", "value": "renders Beacon observations without creating hidden controls"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(beacon_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
