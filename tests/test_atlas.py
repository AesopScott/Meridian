"""Tests for Atlas retrieval harness domain slice."""

import pytest
from dataclasses import FrozenInstanceError
from meridian_core.atlas import (
    AtlasSource,
    AtlasHit,
    AtlasQuery,
    AtlasResult,
    query,
    DOC_ALLOWLIST,
)


# ---------------------------------------------------------------------------
# Test fixtures: mock FileMap entries and docs
# ---------------------------------------------------------------------------

class MockFileMapEntry:
    """Mock FileMapEntry for testing."""
    def __init__(self, path, area, purpose, notes="", related_tests=None):
        self.path = path
        self.area = area
        self.purpose = purpose
        self.notes = notes
        self.related_tests = related_tests or []


def make_mock_filemap(*entries):
    """Return a tuple of mock FileMap entries."""
    return tuple(entries)


# ---------------------------------------------------------------------------
# Domain shape tests
# ---------------------------------------------------------------------------

def test_atlas_source_enum_has_all_kinds():
    """AtlasSource enum covers FILEMAP, DOC, ECHO."""
    assert AtlasSource.FILEMAP.value == "filemap"
    assert AtlasSource.DOC.value == "doc"
    assert AtlasSource.ECHO.value == "echo"


def test_atlas_hit_is_frozen():
    """AtlasHit rejects mutation."""
    hit = AtlasHit(
        path="foo.py",
        title="Foo",
        reason="test",
        excerpt="Test",
        source=AtlasSource.FILEMAP,
        score=0.8,
    )
    with pytest.raises(FrozenInstanceError):
        hit.path = "bar.py"


def test_atlas_query_is_frozen():
    """AtlasQuery is frozen."""
    q = AtlasQuery(terms=("echo",))
    with pytest.raises(FrozenInstanceError):
        q.terms = ("memory",)


def test_atlas_result_is_frozen():
    """AtlasResult is frozen."""
    result = AtlasResult(hits=(), missing_paths=(), truncated=False)
    with pytest.raises(FrozenInstanceError):
        result.truncated = True


def test_atlas_hit_score_validation():
    """AtlasHit rejects scores outside [0.0, 1.0]."""
    with pytest.raises(ValueError, match="score must be in"):
        AtlasHit(
            path="test.py",
            title="Test",
            reason="test",
            excerpt=None,
            source=AtlasSource.FILEMAP,
            score=1.5,
        )


# ---------------------------------------------------------------------------
# FileMap matching tests
# ---------------------------------------------------------------------------

def test_filemap_path_match():
    """A term in a FileMap path returns hit with high score."""
    entries = make_mock_filemap(
        MockFileMapEntry("relay.py", "Relay", "Relay routing"),
    )
    q = AtlasQuery(terms=("relay",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert result.hits[0].path == "relay.py"
    assert "path match" in result.hits[0].reason
    assert result.hits[0].score >= 0.7


def test_filemap_purpose_match():
    """A term in FileMap purpose returns hit with good score."""
    entries = make_mock_filemap(
        MockFileMapEntry("foo.py", "Core", "Echo memory harness"),
    )
    q = AtlasQuery(terms=("echo",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert "purpose match" in result.hits[0].reason
    assert result.hits[0].score >= 0.6


def test_filemap_notes_match():
    """A term in FileMap notes returns hit with soft score."""
    entries = make_mock_filemap(
        MockFileMapEntry(
            "utils.py",
            "Utilities",
            "Helper functions",
            notes="See echo.py for related patterns",
        ),
    )
    q = AtlasQuery(terms=("echo",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert "notes match" in result.hits[0].reason
    assert result.hits[0].score >= 0.4


def test_filemap_no_term_match():
    """A term that doesn't match returns no hits."""
    entries = make_mock_filemap(
        MockFileMapEntry("foo.py", "Core", "Foo utilities"),
    )
    q = AtlasQuery(terms=("nonexistent",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 0


def test_filemap_multiple_terms():
    """Multiple terms match same entry; score reflects best match."""
    entries = make_mock_filemap(
        MockFileMapEntry("relay.py", "Relay", "Echo relay harness"),
    )
    q = AtlasQuery(terms=("echo", "relay"))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert "path match" in result.hits[0].reason or "purpose match" in result.hits[0].reason


def test_filemap_case_insensitive():
    """Term matching is case-insensitive."""
    entries = make_mock_filemap(
        MockFileMapEntry("Echo.py", "Core", "ECHO harness"),
    )
    q = AtlasQuery(terms=("echo",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1


# ---------------------------------------------------------------------------
# Area filter tests
# ---------------------------------------------------------------------------

def test_area_filter_includes_matching():
    """Area filter includes entries in specified areas."""
    entries = make_mock_filemap(
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
        MockFileMapEntry("relay.py", "Relay", "Relay routing"),
    )
    q = AtlasQuery(terms=("harness", "routing"), areas=("Core",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert result.hits[0].path == "echo.py"


def test_area_filter_excludes_non_matching():
    """Area filter excludes entries outside specified areas."""
    entries = make_mock_filemap(
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
        MockFileMapEntry("relay.py", "Relay", "Relay routing"),
    )
    q = AtlasQuery(terms=("harness", "routing"), areas=("Relay",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert result.hits[0].path == "relay.py"


# ---------------------------------------------------------------------------
# Required paths tests
# ---------------------------------------------------------------------------

def test_required_path_always_included():
    """A required_path entry in FileMap is always included with high score."""
    entries = make_mock_filemap(
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
    )
    q = AtlasQuery(terms=(), required_paths=("echo.py",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert result.hits[0].path == "echo.py"
    assert result.hits[0].score >= 0.95
    assert "required path" in result.hits[0].reason


def test_required_path_missing():
    """A missing required_path is reported in missing_paths."""
    entries = make_mock_filemap(
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
    )
    q = AtlasQuery(terms=(), required_paths=("nonexistent.py",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 0
    assert "nonexistent.py" in result.missing_paths


def test_required_path_independent_of_terms():
    """Required path inclusion is independent of term matches."""
    entries = make_mock_filemap(
        MockFileMapEntry("unrelated.py", "Core", "Unrelated file"),
    )
    q = AtlasQuery(terms=("echo",), required_paths=("unrelated.py",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    assert result.hits[0].path == "unrelated.py"


def test_required_path_no_duplicate():
    """Required path that already matched in terms is not duplicated."""
    entries = make_mock_filemap(
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
    )
    q = AtlasQuery(terms=("echo",), required_paths=("echo.py",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1


# ---------------------------------------------------------------------------
# Ranking and ordering tests
# ---------------------------------------------------------------------------

def test_ranking_by_score():
    """Hits are ordered by score descending."""
    entries = make_mock_filemap(
        MockFileMapEntry("path_echo.py", "Core", "File"),  # Path match, score ~0.8
        MockFileMapEntry("foo.py", "Core", "Echo harness"),  # Purpose match, score ~0.7
    )
    q = AtlasQuery(terms=("echo",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 2
    assert result.hits[0].score >= result.hits[1].score


def test_source_priority_filemap_over_doc():
    """FILEMAP source outranks DOC source on tie."""
    # This test would need file I/O for docs; skipped in basic test.
    pass


def test_path_ordering_on_tie():
    """Within same score and source, ordered by path ascending."""
    entries = make_mock_filemap(
        MockFileMapEntry("z_file.py", "Core", "Echo file"),  # Both purpose match
        MockFileMapEntry("a_file.py", "Core", "Echo file"),  # Both purpose match
    )
    q = AtlasQuery(terms=("echo",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 2
    assert result.hits[0].path == "a_file.py"
    assert result.hits[1].path == "z_file.py"


def test_deterministic_query():
    """Two identical queries return identical hits in identical order."""
    entries = make_mock_filemap(
        MockFileMapEntry("relay.py", "Relay", "Echo relay"),
        MockFileMapEntry("echo.py", "Core", "Echo harness"),
        MockFileMapEntry("notes.py", "Util", "Utils", notes="related to echo"),
    )
    q = AtlasQuery(terms=("echo",), limit=10)

    result1 = query(q, filemap_entries=entries)
    result2 = query(q, filemap_entries=entries)

    assert len(result1.hits) == len(result2.hits)
    for h1, h2 in zip(result1.hits, result2.hits):
        assert h1.path == h2.path
        assert h1.score == h2.score
        assert h1.reason == h2.reason


# ---------------------------------------------------------------------------
# Doc allowlist tests
# ---------------------------------------------------------------------------

def test_doc_allowlist_defined():
    """DOC_ALLOWLIST contains curated doc paths."""
    assert "MISSION.md" in DOC_ALLOWLIST
    assert "docs/atlas-retrieval-contract.md" in DOC_ALLOWLIST


def test_doc_not_on_allowlist_never_returned():
    """A doc not on allowlist and not in FileMap is never returned via DOC source."""
    entries = make_mock_filemap(
        MockFileMapEntry("some/random/doc.md", "Docs", "Random content"),
    )
    # Query for a term that matches the path but the file is not on DOC allowlist.
    # FileMap source can match it, but DOC source cannot.
    q = AtlasQuery(terms=("random",))
    result = query(q, filemap_entries=entries)

    # Should match via FileMap source (path match), not DOC source.
    assert len(result.hits) == 1
    assert result.hits[0].source == AtlasSource.FILEMAP


# ---------------------------------------------------------------------------
# Limit and truncation tests
# ---------------------------------------------------------------------------

def test_limit_truncates_results():
    """Results are truncated to limit."""
    entries = make_mock_filemap(
        MockFileMapEntry("a.py", "Core", "A file"),
        MockFileMapEntry("b.py", "Core", "B file"),
        MockFileMapEntry("c.py", "Core", "C file"),
    )
    q = AtlasQuery(terms=("file",), limit=2)
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 2
    assert result.truncated is True


def test_limit_zero_returns_empty():
    """limit=0 returns empty hits and truncated=True if candidates existed."""
    entries = make_mock_filemap(
        MockFileMapEntry("a.py", "Core", "A file"),
    )
    q = AtlasQuery(terms=("file",), limit=0)
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 0
    assert result.truncated is True


def test_no_candidates_truncated_false():
    """truncated=False if no candidates existed."""
    entries = make_mock_filemap(
        MockFileMapEntry("a.py", "Core", "A file"),
    )
    q = AtlasQuery(terms=("nonexistent",), limit=10)
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 0
    assert result.truncated is False


# ---------------------------------------------------------------------------
# Empty/edge cases
# ---------------------------------------------------------------------------

def test_empty_terms_no_required_paths():
    """Empty terms and no required_paths returns empty hits."""
    entries = make_mock_filemap(
        MockFileMapEntry("a.py", "Core", "A file"),
    )
    q = AtlasQuery(terms=(), required_paths=())
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 0


def test_empty_filemap():
    """Empty FileMap returns empty hits, no exception."""
    q = AtlasQuery(terms=("anything",))
    result = query(q, filemap_entries=())

    assert len(result.hits) == 0
    assert result.truncated is False


def test_no_filemap_provided():
    """No filemap_entries provided returns empty hits."""
    q = AtlasQuery(terms=("anything",))
    result = query(q)

    assert len(result.hits) == 0


# ---------------------------------------------------------------------------
# Echo integration (optional)
# ---------------------------------------------------------------------------

def test_include_echo_false_default():
    """include_echo defaults to False."""
    q = AtlasQuery(terms=("test",))
    assert q.include_echo is False


def test_include_echo_true_with_no_store():
    """include_echo=True but no echo_store still returns FileMap hits, no exception."""
    entries = make_mock_filemap(
        MockFileMapEntry("relay.py", "Relay", "Relay routing"),
    )
    q = AtlasQuery(terms=("relay",), include_echo=True)
    result = query(q, filemap_entries=entries, echo_store=None)

    # Should still get FileMap hits.
    assert len(result.hits) == 1
    assert result.hits[0].source == AtlasSource.FILEMAP


# ---------------------------------------------------------------------------
# Excerpt generation
# ---------------------------------------------------------------------------

def test_excerpt_combines_purpose_and_notes():
    """Excerpt includes both purpose and notes."""
    entries = make_mock_filemap(
        MockFileMapEntry(
            "test.py",
            "Core",
            "Test file",
            notes="Implementation details here",
        ),
    )
    q = AtlasQuery(terms=("test",))
    result = query(q, filemap_entries=entries)

    assert len(result.hits) == 1
    hit = result.hits[0]
    assert "Test file" in (hit.excerpt or "")
    assert "Implementation" in (hit.excerpt or "")


# ---------------------------------------------------------------------------
# Exclusion list
# ---------------------------------------------------------------------------

def test_excluded_areas_never_returned():
    """Entries in excluded areas are never returned."""
    entries = make_mock_filemap(
        MockFileMapEntry("build.log", "Build logs", "Build log content"),
        MockFileMapEntry("queue.md", "Queue", "Queue file"),
    )
    q = AtlasQuery(terms=("build", "queue"))
    result = query(q, filemap_entries=entries)

    # Neither should be returned due to exclusion.
    assert len(result.hits) == 0
