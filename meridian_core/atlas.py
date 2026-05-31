"""Atlas: deterministic retrieval harness for Meridian.

Serves ranked, source-attributed hits over FileMap entries, curated docs,
and optionally Echo summaries. No embeddings, no broad crawl, no network I/O.
Fails soft on missing inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class AtlasSource(Enum):
    """Source of an Atlas hit."""
    FILEMAP = "filemap"
    DOC = "doc"
    ECHO = "echo"


@dataclass(frozen=True)
class AtlasHit:
    """A single retrieval result."""
    path: str
    title: str
    reason: str
    excerpt: Optional[str]
    source: AtlasSource
    score: float

    def __post_init__(self):
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")


@dataclass(frozen=True)
class AtlasQuery:
    """A typed query for Atlas."""
    terms: Tuple[str, ...]
    areas: Tuple[str, ...] = ()
    required_paths: Tuple[str, ...] = ()
    include_echo: bool = False
    project: Optional[str] = None
    limit: int = 25


@dataclass(frozen=True)
class AtlasResult:
    """The full retrieval response."""
    hits: Tuple[AtlasHit, ...]
    missing_paths: Tuple[str, ...]
    truncated: bool


# Allowlist of documentation files that are always retrievable.
# Add entries here for load-bearing contract docs, plans, and architecture briefs.
DOC_ALLOWLIST = (
    "MISSION.md",
    "docs/atlas-retrieval-contract.md",
    "docs/echo-memory-contract.md",
    "docs/cognition-policy-contract.md",
    "docs/relay-dispatch-contract.md",
)

# Areas that should not be surfaced in Atlas hits (e.g., queue/log files).
# These are reserved for operational records, not retrieval.
EXCLUDED_AREAS = (
    "Queue",
    "Build logs",
    "Session logs",
)


def query(
    q: AtlasQuery,
    filemap_entries: Tuple = (),
    echo_store=None,
) -> AtlasResult:
    """
    Execute a deterministic Atlas query over FileMap entries, docs, and optionally Echo.

    Args:
        q: AtlasQuery with terms, areas, required_paths, and limits.
        filemap_entries: Tuple of FileMapEntry objects (path, area, purpose, notes, related_tests).
        echo_store: Optional Echo repository for include_echo=True. If None, Echo hits are skipped.

    Returns:
        AtlasResult with ranked hits, missing_paths, and truncated flag.
    """
    hits = []
    missing_paths = []

    # Hard filter: exclude entries in reserved areas.
    def is_excluded(area: str) -> bool:
        return any(excluded.lower() in area.lower() for excluded in EXCLUDED_AREAS)

    # Gather FileMap candidates.
    for entry in filemap_entries:
        if is_excluded(entry.area):
            continue
        if q.areas and entry.area not in q.areas:
            continue
        hit = _make_filemap_hit(entry, q)
        if hit:
            hits.append(hit)

    # Gather DOC candidates (optional; only if terms match or required).
    # In first slice, only process if doc is in required_paths to avoid file I/O cost.
    for doc_path in DOC_ALLOWLIST:
        if doc_path not in q.required_paths:
            continue  # Skip doc lookup unless explicitly required.
        if q.areas and not _path_in_areas(doc_path, q.areas):
            continue
        hit = _make_doc_hit(doc_path, q)
        if hit:
            hits.append(hit)

    # Optionally gather Echo candidates.
    if q.include_echo and echo_store:
        echo_hits = _query_echo(q, echo_store)
        hits.extend(echo_hits)

    # Required paths: always included if they exist, regardless of term matches.
    for req_path in q.required_paths:
        # Check if already in hits.
        if any(h.path == req_path for h in hits):
            continue
        # Try to find in FileMap.
        found = False
        for entry in filemap_entries:
            if entry.path == req_path:
                hit = AtlasHit(
                    path=entry.path,
                    title=entry.purpose or Path(entry.path).name,
                    reason="required path",
                    excerpt=_make_excerpt(entry.purpose, entry.notes),
                    source=AtlasSource.FILEMAP,
                    score=0.99,  # Near-max, just below perfect 1.0
                )
                hits.append(hit)
                found = True
                break
        # Try to find in doc allowlist.
        if not found and req_path in DOC_ALLOWLIST:
            hit = _make_doc_hit(req_path, q, force=True)
            if hit:
                # Override score for required paths.
                hit = AtlasHit(
                    path=hit.path,
                    title=hit.title,
                    reason="required path",
                    excerpt=hit.excerpt,
                    source=hit.source,
                    score=0.99,
                )
                hits.append(hit)
                found = True
        # Record missing if not found.
        if not found:
            missing_paths.append(req_path)

    # Sort by score desc, then by source priority, then by path asc.
    hits.sort(
        key=lambda h: (
            -h.score,
            _source_priority(h.source),
            h.path,
        )
    )

    # Apply limit.
    truncated = len(hits) > q.limit
    if q.limit > 0:
        hits = hits[:q.limit]
    elif q.limit == 0:
        hits = []

    return AtlasResult(
        hits=tuple(hits),
        missing_paths=tuple(missing_paths),
        truncated=truncated,
    )


def _make_filemap_hit(entry, q: AtlasQuery) -> Optional[AtlasHit]:
    """Create an AtlasHit from a FileMap entry, or None if it doesn't match."""
    score = 0.0
    reason_parts = []

    # Check for term matches in path, purpose, and notes.
    path_lower = entry.path.lower()
    purpose_lower = (entry.purpose or "").lower()
    notes_lower = (entry.notes or "").lower()

    for term in q.terms:
        term_lower = term.lower()
        if term_lower in path_lower:
            score = max(score, 0.8)  # Strong match.
            reason_parts.append("path match")
        elif term_lower in purpose_lower:
            score = max(score, 0.7)  # Strong match.
            reason_parts.append("purpose match")
        elif term_lower in notes_lower:
            score = max(score, 0.5)  # Soft match.
            reason_parts.append("notes match")

    # If no terms match, skip it (no required-path inclusion in FileMap lookup).
    if score == 0.0:
        return None

    reason = ", ".join(reason_parts) if reason_parts else "matched"
    excerpt = _make_excerpt(entry.purpose, entry.notes)

    return AtlasHit(
        path=entry.path,
        title=entry.purpose or Path(entry.path).name,
        reason=reason,
        excerpt=excerpt,
        source=AtlasSource.FILEMAP,
        score=score,
    )


def _make_doc_hit(path: str, q: AtlasQuery, force: bool = False) -> Optional[AtlasHit]:
    """Create an AtlasHit from a doc on the allowlist, or None if it doesn't match."""
    if path not in DOC_ALLOWLIST:
        return None

    # Try to read the doc and extract first heading.
    try:
        doc_path = Path(path)
        if not doc_path.exists():
            return None
        content = doc_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    title = _extract_first_heading(content) or Path(path).name
    excerpt = _extract_excerpt(content)

    score = 0.0
    reason_parts = []

    if force:
        # Required path; already scored in _query_required_paths.
        score = 0.99
        reason_parts.append("required path")
    else:
        # Check for term matches in title and excerpt.
        title_lower = title.lower()
        excerpt_lower = excerpt.lower() if excerpt else ""

        for term in q.terms:
            term_lower = term.lower()
            if term_lower in title_lower:
                score = max(score, 0.7)  # Strong match.
                reason_parts.append("heading match")
            elif excerpt_lower and term_lower in excerpt_lower:
                score = max(score, 0.5)  # Soft match.
                reason_parts.append("excerpt match")

        # If no terms match, skip it.
        if score == 0.0:
            return None

    reason = ", ".join(reason_parts) if reason_parts else "matched"

    return AtlasHit(
        path=path,
        title=title,
        reason=reason,
        excerpt=excerpt,
        source=AtlasSource.DOC,
        score=score,
    )


def _query_echo(q: AtlasQuery, echo_store) -> list[AtlasHit]:
    """Query Echo and convert MemoryHit summaries to AtlasHit objects."""
    # This is optional in first slice; implement as stub that returns empty list.
    # Full implementation would:
    # - Create a MemoryQuery from q.terms and q.project
    # - Call echo_store.query()
    # - Convert MemoryHit -> AtlasHit with source=ECHO
    return []


def _path_in_areas(path: str, areas: Tuple[str, ...]) -> bool:
    """Check if a doc path matches any of the required areas (loose match)."""
    # For docs, extract area from path prefix (e.g., "docs/foo.md" -> "docs").
    path_lower = path.lower()
    for area in areas:
        area_lower = area.lower()
        if path_lower.startswith(area_lower + "/") or path_lower.startswith(area_lower):
            return True
    return False


def _make_excerpt(purpose: Optional[str], notes: Optional[str]) -> Optional[str]:
    """Combine purpose and notes into a short excerpt."""
    parts = []
    if purpose:
        parts.append(purpose)
    if notes:
        parts.append(notes)
    return " | ".join(parts) if parts else None


def _extract_first_heading(content: str) -> Optional[str]:
    """Extract the first markdown heading from content."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            # Remove # and leading/trailing whitespace.
            heading = line.lstrip("#").strip()
            return heading if heading else None
    return None


def _extract_excerpt(content: str) -> Optional[str]:
    """Extract an introductory excerpt (first non-heading paragraph)."""
    in_intro = False
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            in_intro = True
            continue
        if in_intro and line:
            return line[:200]  # First 200 chars of first paragraph.
    return None


def _source_priority(source: AtlasSource) -> int:
    """Return priority for tie-breaking (lower is better)."""
    return {
        AtlasSource.FILEMAP: 0,
        AtlasSource.DOC: 1,
        AtlasSource.ECHO: 2,
    }.get(source, 3)
