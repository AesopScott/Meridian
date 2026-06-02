"""Backend snapshot for Echo memory logic shown in the harness UI."""

from __future__ import annotations

from meridian_core.echo import EchoRepository, MemoryKind, MemorySource

SNAPSHOT_VERSION = "echo-domain-v1"


def echo_logic_snapshot() -> dict:
    """Return the Echo capability list used by Bifrost's visible harness."""
    memory_kinds = [kind.value for kind in MemoryKind]
    memory_sources = [source.value for source in MemorySource]
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.echo_logic_snapshot.echo_logic_snapshot",
        "harness": "Echo",
        "summary": "Echo owns durable memory records, typed memory queries, deterministic ranking, supersession, and prompt-safe recall boundaries. This snapshot exposes the logic shape without opening a live memory store.",
        "limits": {
            "hardLimit": EchoRepository.HARD_LIMIT,
            "liveStoreOpened": False,
            "rawBodiesVisible": False,
        },
        "memoryKinds": memory_kinds,
        "memorySources": memory_sources,
        "capabilitySections": [
            {
                "title": "Echo Job",
                "summary": "Keep durable project memory queryable without turning hidden history into unbounded prompt context.",
                "rows": [
                    {"key": "owns", "value": "memory records, typed queries, deterministic ranking, pinning, supersession"},
                    {"key": "does not own", "value": "file retrieval, model routing, UI mutation, branch movement"},
                    {"key": "current operation", "value": "query-only domain logic; durable storage wiring remains future work"},
                ],
            },
            {
                "title": "Memory Record Shape",
                "summary": "Every Echo record is immutable and has explicit source, project, kind, timestamps, importance, tags, and supersession state.",
                "rows": [
                    {"key": "kinds", "value": ", ".join(memory_kinds)},
                    {"key": "sources", "value": ", ".join(memory_sources)},
                    {"key": "importance", "value": "1-5, validated at construction"},
                    {"key": "project", "value": "hard query boundary; records from other projects do not match"},
                ],
            },
            {
                "title": "Query Filter Logic",
                "summary": "Echo filters before ranking so Prime sees only records that match the requested project and constraints.",
                "rows": [
                    {"key": "hard filter", "value": "project id"},
                    {"key": "optional filters", "value": "kind, tags, since timestamp, superseded inclusion"},
                    {"key": "empty behavior", "value": "unknown project or empty repository returns no hits"},
                    {"key": "limit", "value": f"query limit is capped at {EchoRepository.HARD_LIMIT}"},
                ],
            },
            {
                "title": "Ranking Logic",
                "summary": "Echo ranks deterministically by pinning, importance, recency, timestamp, and record id.",
                "rows": [
                    {"key": "pinned", "value": "pinned records receive the strongest base score"},
                    {"key": "importance", "value": "higher importance raises score within the bounded range"},
                    {"key": "recency", "value": "recent records receive a soft boost unless a since filter is active"},
                    {"key": "ties", "value": "stable order by pinned state, importance, timestamp, and record id"},
                ],
            },
            {
                "title": "Supersession Logic",
                "summary": "Echo keeps replaced records addressable while hiding superseded records from normal recall.",
                "rows": [
                    {"key": "default", "value": "superseded records are excluded"},
                    {"key": "explicit inclusion", "value": "include_superseded allows audit/recovery queries"},
                    {"key": "write rule", "value": "supersede creates the replacement record and marks the old id"},
                ],
            },
            {
                "title": "Failure-Soft Logic",
                "summary": "Echo normalizes readable timestamps and skips invalid records instead of crashing a recall request.",
                "rows": [
                    {"key": "datetime handling", "value": "naive timestamps are normalized to UTC"},
                    {"key": "unknown record", "value": "single-record lookup returns none"},
                    {"key": "corrupt data", "value": "unreadable timestamps do not enter ranked hits"},
                ],
            },
            {
                "title": "Prompt Boundary Logic",
                "summary": "Echo exposes summaries and ranked reasons; raw memory text is not injected into a prompt by this snapshot.",
                "rows": [
                    {"key": "visible fields", "value": "record id, project, kind, summary, source, score, reason"},
                    {"key": "blocked fields", "value": "record text payload and hidden transcript replay"},
                    {"key": "handoff", "value": "Prime and Relay decide what visible recall context enters model prompts"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "Echo is a memory query harness, not an executor.",
                "rows": [
                    {"key": "live store opened", "value": "no"},
                    {"key": "writes from UI", "value": "blocked until durable storage and approval gates exist"},
                    {"key": "Prime integration", "value": "planned: feed live memory hits into Prime runtime packet"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(echo_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
