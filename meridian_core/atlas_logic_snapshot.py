"""Backend snapshot for Atlas retrieval logic shown in the harness UI."""

from __future__ import annotations

from meridian_core.atlas import DOC_ALLOWLIST, EXCLUDED_AREAS, AtlasSource

SNAPSHOT_VERSION = "atlas-domain-v1"


def atlas_logic_snapshot() -> dict:
    """Return the Atlas capability list used by Bifrost's visible harness."""
    sources = [source.value for source in AtlasSource]
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.atlas_logic_snapshot.atlas_logic_snapshot",
        "harness": "Atlas",
        "summary": "Atlas owns deterministic FileMap/docs-first retrieval, source-aware ranking, required-path coverage, and failure-soft missing-path reporting. This snapshot exposes the logic shape without crawling broadly or injecting hidden context.",
        "limits": {
            "docAllowlistCount": len(DOC_ALLOWLIST),
            "excludedAreaCount": len(EXCLUDED_AREAS),
            "broadCrawlEnabled": False,
            "networkEnabled": False,
            "hiddenPromptInjection": False,
        },
        "sources": sources,
        "docAllowlist": list(DOC_ALLOWLIST),
        "excludedAreas": list(EXCLUDED_AREAS),
        "capabilitySections": [
            {
                "title": "Atlas Job",
                "summary": "Find the right Meridian source context without pretending every file or memory record is automatically safe prompt context.",
                "rows": [
                    {"key": "owns", "value": "retrieval hits, source labels, excerpts, required paths, missing path reporting"},
                    {"key": "does not own", "value": "durable memory storage, model routing, live command execution, broad filesystem crawling"},
                    {"key": "current operation", "value": "deterministic retrieval only; no embeddings or network calls"},
                ],
            },
            {
                "title": "Retrieval Source Logic",
                "summary": "Atlas returns hits from explicit sources with source-aware ordering.",
                "rows": [
                    {"key": "sources", "value": ", ".join(sources)},
                    {"key": "FileMap source", "value": "registered entries with path, area, purpose, notes, and related tests"},
                    {"key": "doc source", "value": "allowlisted architecture and contract docs only"},
                    {"key": "Echo source", "value": "optional summaries when include_echo is true and a store is provided"},
                ],
            },
            {
                "title": "FileMap Ranking Logic",
                "summary": "FileMap hits match query terms against path, purpose, and notes before scoring.",
                "rows": [
                    {"key": "path match", "value": "strongest normal FileMap score"},
                    {"key": "purpose match", "value": "strong FileMap score"},
                    {"key": "notes match", "value": "soft FileMap score"},
                    {"key": "reserved areas", "value": ", ".join(EXCLUDED_AREAS)},
                ],
            },
            {
                "title": "Doc Allowlist Logic",
                "summary": "Atlas reads only allowlisted docs and only when the query explicitly requires them.",
                "rows": [
                    {"key": "allowlist count", "value": str(len(DOC_ALLOWLIST))},
                    {"key": "allowlist", "value": ", ".join(DOC_ALLOWLIST)},
                    {"key": "read policy", "value": "doc lookup is skipped unless the path is required"},
                    {"key": "failure behavior", "value": "missing or unreadable docs fail soft"},
                ],
            },
            {
                "title": "Required Path Logic",
                "summary": "Required paths are promoted into hits when known and reported as missing when unavailable.",
                "rows": [
                    {"key": "FileMap required path", "value": "included even with no term match"},
                    {"key": "doc required path", "value": "included only when allowlisted and readable"},
                    {"key": "missing path", "value": "recorded in missing_paths"},
                    {"key": "required score", "value": "0.99 to keep it near the top without claiming perfect relevance"},
                ],
            },
            {
                "title": "Ordering Logic",
                "summary": "Atlas sorts deterministically after all sources are collected.",
                "rows": [
                    {"key": "primary sort", "value": "score descending"},
                    {"key": "source priority", "value": "FileMap, docs, Echo"},
                    {"key": "tie breaker", "value": "path ascending"},
                    {"key": "truncation", "value": "result reports truncated when hits exceed the query limit"},
                ],
            },
            {
                "title": "Prompt Boundary Logic",
                "summary": "Atlas returns attributed excerpts and reasons; Prime and Relay still decide what visible context enters a model prompt.",
                "rows": [
                    {"key": "visible fields", "value": "path, title, reason, excerpt, source, score"},
                    {"key": "blocked behavior", "value": "hidden raw transcript replay and broad file dumps"},
                    {"key": "handoff", "value": "Echo supplies memory summaries; Atlas supplies retrieval hits; Aegis/Relay guard prompt payload"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "Atlas is a retrieval harness, not an executor.",
                "rows": [
                    {"key": "network", "value": "disabled"},
                    {"key": "broad crawl", "value": "disabled"},
                    {"key": "writes from UI", "value": "none"},
                    {"key": "Prime integration", "value": "planned: feed live retrieval hits into Prime runtime packet"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(atlas_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
