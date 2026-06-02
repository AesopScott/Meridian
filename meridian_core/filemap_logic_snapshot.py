"""Backend snapshot for Charon/FileMap logic shown in the harness UI."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .filemap import FileArea, make_default_map

SNAPSHOT_VERSION = "charon-filemap-v1"


def filemap_logic_snapshot() -> dict[str, Any]:
    """Return the Charon capability list used by Bifrost's visible harness."""
    filemap = make_default_map()
    entries = filemap.all_entries()
    area_counts = Counter(entry.area for entry in entries)
    entries_with_tests = filemap.with_tests()
    top_areas = sorted(area_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    required_paths = (
        "MISSION.md",
        "context.md",
        "docs/FileMap.md",
        "meridian_core/filemap.py",
        "tests/test_filemap.py",
        "index.html",
        "scripts/meridian-model-bridge.js",
    )
    required_status = [
        {"key": path, "value": "registered" if filemap.get(path) else "missing"}
        for path in required_paths
    ]

    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.filemap_logic_snapshot.filemap_logic_snapshot",
        "harness": "Charon / FileMap",
        "summary": (
            "Charon owns FileMap discoverability: stable path lookup, area grouping, "
            "related-test visibility, and compact memory injection summaries."
        ),
        "totals": {
            "entries": len(entries),
            "areas": len(area_counts),
            "entriesWithTests": len(entries_with_tests),
        },
        "areaCounts": [
            {"key": area, "value": str(count)}
            for area, count in sorted(area_counts.items())
        ],
        "capabilitySections": [
            {
                "title": "Charon Job",
                "summary": "Keep important Meridian files findable by path and architecture area.",
                "rows": [
                    {"key": "owns", "value": "FileMap entries, path lookup, area grouping, related tests, injection summaries"},
                    {"key": "does not own", "value": "file mutation, branch movement, review acceptance, runtime execution"},
                    {"key": "drift guard", "value": "new significant files must be registered and covered by required-path tests"},
                ],
            },
            {
                "title": "Registry Shape Logic",
                "summary": "Charon exposes the deterministic size and coverage shape of the default FileMap.",
                "rows": [
                    {"key": "entries", "value": str(len(entries))},
                    {"key": "areas", "value": str(len(area_counts))},
                    {"key": "entries with tests", "value": str(len(entries_with_tests))},
                    {"key": "sort order", "value": "entries and area views sort stably by path"},
                ],
            },
            {
                "title": "Lookup Logic",
                "summary": "Registered paths can be read safely without rediscovering the repo.",
                "rows": [
                    {"key": "get", "value": "returns an entry or none for optional lookup"},
                    {"key": "require", "value": "raises a visible missing-entry error for required lookup"},
                    {"key": "all entries", "value": "returns every registered path in deterministic order"},
                ],
            },
            {
                "title": "Required Path Coverage",
                "summary": "Core boot, FileMap, UI, and bridge paths remain registered.",
                "rows": required_status,
            },
            {
                "title": "Area Coverage Logic",
                "summary": "Charon shows which architecture areas have the most registered files.",
                "rows": [
                    {"key": area, "value": str(count)}
                    for area, count in top_areas
                ],
            },
            {
                "title": "Test Visibility Logic",
                "summary": "Charon keeps related tests visible for source and document entries.",
                "rows": [
                    {"key": "with tests", "value": str(len(entries_with_tests))},
                    {"key": "test source", "value": "FileMapEntry.related_tests"},
                    {"key": "coverage proof", "value": "tests/test_filemap.py verifies required path registration"},
                ],
            },
            {
                "title": "Memory Injection Logic",
                "summary": "FileMap summaries can seed session memory without dumping raw files.",
                "rows": [
                    {"key": "summary method", "value": "injection_summary(area=None)"},
                    {"key": "area filter", "value": "optional exact-area filtering"},
                    {"key": "output", "value": "path, purpose, related tests, and notes only"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "Charon is a lookup and discoverability harness, not a writer.",
                "rows": [
                    {"key": "no writes", "value": "does not edit files, move branches, approve reviews, or execute commands"},
                    {"key": "safe output", "value": "serializable metadata derived from FileMap entries"},
                    {"key": "future work", "value": "live FileMap health can feed Prime after review gates are explicit"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(filemap_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
