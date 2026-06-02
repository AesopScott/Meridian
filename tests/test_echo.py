import pytest
from datetime import datetime, timezone
from meridian_core.echo import (
    MemoryKind, MemorySource, MemoryRecord, MemoryQuery, MemoryHit, EchoRepository
)


@pytest.fixture
def repo():
    return EchoRepository()


def make_record(record_id, summary, created_at_str, importance=3, pinned=False, tags=()):
    created = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
    return MemoryRecord(
        record_id=record_id,
        project="meridian",
        kind=MemoryKind.DECISION,
        summary=summary,
        body="test body",
        source=MemorySource.PRIME,
        created_at=created,
        importance=importance,
        pinned=pinned,
        tags=tags,
    )


class TestDomainShape:
    def test_memory_record_frozen(self):
        record = make_record("rec1", "Test decision", "2026-05-31T12:00:00Z")
        with pytest.raises(AttributeError):
            record.importance = 4

    def test_memory_kind_enum(self):
        assert MemoryKind.DECISION.value == "decision"
        assert MemoryKind.FACT.value == "fact"
        assert MemoryKind.PLAN.value == "plan"
        assert MemoryKind.GATE_OUTCOME.value == "gate_outcome"
        assert MemoryKind.STANDING_INSTRUCTION.value == "standing_instruction"
        assert MemoryKind.NOTE.value == "note"

    def test_memory_source_enum(self):
        assert MemorySource.PRIME.value == "prime"
        assert MemorySource.USER.value == "user"
        assert MemorySource.REVIEW_CONSOLE.value == "review_console"
        assert MemorySource.WORKER.value == "worker"
        assert MemorySource.IMPORT.value == "import"

    def test_record_importance_validation(self):
        with pytest.raises(ValueError):
            created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
            MemoryRecord(
                record_id="rec1",
                project="meridian",
                kind=MemoryKind.DECISION,
                summary="Test",
                body="Test",
                source=MemorySource.PRIME,
                created_at=created,
                importance=0,
                pinned=False,
                tags=(),
            )


class TestAddAndQuery:
    def test_add_then_query(self, repo):
        record = make_record("rec1", "Test decision", "2026-05-31T12:00:00Z")
        repo.add(record)
        query = MemoryQuery(project="meridian")
        hits = repo.query(query)
        assert len(hits) == 1
        assert hits[0].record.record_id == "rec1"

    def test_query_no_matching_project(self, repo):
        record = make_record("rec1", "Test", "2026-05-31T12:00:00Z")
        repo.add(record)
        query = MemoryQuery(project="polaris")
        hits = repo.query(query)
        assert len(hits) == 0

    def test_query_unknown_project_no_error(self, repo):
        query = MemoryQuery(project="unknown")
        hits = repo.query(query)
        assert len(hits) == 0

    def test_query_by_kind(self, repo):
        created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Decision", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=False, tags=(),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.FACT,
            summary="Fact", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=False, tags=(),
        )
        repo.add(rec1)
        repo.add(rec2)
        query = MemoryQuery(project="meridian", kinds=(MemoryKind.DECISION,))
        hits = repo.query(query)
        assert len(hits) == 1
        assert hits[0].record.kind == MemoryKind.DECISION

    def test_query_by_tags(self, repo):
        created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Decision", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=False, tags=("user", "important"),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.FACT,
            summary="Fact", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=False, tags=("other",),
        )
        repo.add(rec1)
        repo.add(rec2)
        query = MemoryQuery(project="meridian", tags=("user",))
        hits = repo.query(query)
        assert len(hits) == 1
        assert "user" in hits[0].record.tags

    def test_query_since_excludes_old_unpinned(self, repo):
        old_created = datetime.fromisoformat("2026-05-30T12:00:00Z".replace('Z', '+00:00'))
        new_created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Old", body="...", source=MemorySource.PRIME,
            created_at=old_created, importance=3, pinned=False, tags=(),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="New", body="...", source=MemorySource.PRIME,
            created_at=new_created, importance=3, pinned=False, tags=(),
        )
        repo.add(rec1)
        repo.add(rec2)
        since = datetime.fromisoformat("2026-05-31T00:00:00Z".replace('Z', '+00:00'))
        query = MemoryQuery(project="meridian", since=since)
        hits = repo.query(query)
        assert len(hits) == 1
        assert hits[0].record.summary == "New"

    def test_query_since_includes_pinned(self, repo):
        old_created = datetime.fromisoformat("2026-05-30T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Pinned old", body="...", source=MemorySource.PRIME,
            created_at=old_created, importance=3, pinned=True, tags=(),
        )
        repo.add(rec1)
        since = datetime.fromisoformat("2026-05-31T00:00:00Z".replace('Z', '+00:00'))
        query = MemoryQuery(project="meridian", since=since)
        hits = repo.query(query)
        assert len(hits) == 1


class TestRanking:
    def test_pinned_outranks_unpinned(self, repo):
        created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Unpinned", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=False, tags=(),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="Pinned", body="...", source=MemorySource.PRIME,
            created_at=created, importance=3, pinned=True, tags=(),
        )
        repo.add(rec1)
        repo.add(rec2)
        hits = repo.query(MemoryQuery(project="meridian"))
        assert hits[0].record.record_id == "rec2"

    def test_newer_outranks_older(self, repo):
        old_created = datetime.fromisoformat("2026-05-30T12:00:00Z".replace('Z', '+00:00'))
        new_created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Old", body="...", source=MemorySource.PRIME,
            created_at=old_created, importance=3, pinned=False, tags=(),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="New", body="...", source=MemorySource.PRIME,
            created_at=new_created, importance=3, pinned=False, tags=(),
        )
        repo.add(rec1)
        repo.add(rec2)
        hits = repo.query(MemoryQuery(project="meridian"))
        assert hits[0].record.record_id == "rec2"

    def test_higher_importance_outranks_lower(self, repo):
        created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        rec1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Low", body="...", source=MemorySource.PRIME,
            created_at=created, importance=2, pinned=False, tags=(),
        )
        rec2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="High", body="...", source=MemorySource.PRIME,
            created_at=created, importance=5, pinned=False, tags=(),
        )
        repo.add(rec1)
        repo.add(rec2)
        hits = repo.query(MemoryQuery(project="meridian"))
        assert hits[0].record.record_id == "rec2"

    def test_score_in_range(self, repo):
        record = make_record("rec1", "Test", "2026-05-31T12:00:00Z")
        repo.add(record)
        hits = repo.query(MemoryQuery(project="meridian"))
        assert 0.0 <= hits[0].score <= 1.0

    def test_deterministic_order(self, repo):
        for i in range(5):
            created = datetime.fromisoformat(f"2026-05-31T{i:02d}:00:00Z".replace('Z', '+00:00'))
            record = MemoryRecord(
                record_id=f"rec{i}", project="meridian", kind=MemoryKind.DECISION,
                summary=f"Record {i}", body="...", source=MemorySource.PRIME,
                created_at=created, importance=3, pinned=False, tags=(),
            )
            repo.add(record)
        query = MemoryQuery(project="meridian")
        hits1 = repo.query(query)
        hits2 = repo.query(query)
        assert [h.record.record_id for h in hits1] == [h.record.record_id for h in hits2]


class TestSupersession:
    def test_superseded_excluded_by_default(self, repo):
        old_created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        new_created = datetime.fromisoformat("2026-05-31T13:00:00Z".replace('Z', '+00:00'))
        record1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Old", body="...", source=MemorySource.PRIME,
            created_at=old_created, importance=3, pinned=False, tags=(),
        )
        record2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="New", body="...", source=MemorySource.PRIME,
            created_at=new_created, importance=3, pinned=False, tags=(),
        )
        repo.add(record1)
        repo.supersede("rec1", record2)
        hits = repo.query(MemoryQuery(project="meridian"))
        assert len(hits) == 1
        assert hits[0].record.record_id == "rec2"

    def test_superseded_included_on_request(self, repo):
        old_created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        new_created = datetime.fromisoformat("2026-05-31T13:00:00Z".replace('Z', '+00:00'))
        record1 = MemoryRecord(
            record_id="rec1", project="meridian", kind=MemoryKind.DECISION,
            summary="Old", body="...", source=MemorySource.PRIME,
            created_at=old_created, importance=3, pinned=False, tags=(),
        )
        record2 = MemoryRecord(
            record_id="rec2", project="meridian", kind=MemoryKind.DECISION,
            summary="New", body="...", source=MemorySource.PRIME,
            created_at=new_created, importance=3, pinned=False, tags=(),
        )
        repo.add(record1)
        repo.supersede("rec1", record2)
        hits = repo.query(MemoryQuery(project="meridian", include_superseded=True))
        assert len(hits) == 2


class TestLimits:
    def test_limit_zero_returns_empty(self, repo):
        record = make_record("rec1", "Test", "2026-05-31T12:00:00Z")
        repo.add(record)
        hits = repo.query(MemoryQuery(project="meridian", limit=0))
        assert len(hits) == 0

    def test_limit_larger_than_hard_cap_truncated(self, repo):
        created = datetime.fromisoformat("2026-05-31T12:00:00Z".replace('Z', '+00:00'))
        for i in range(30):
            record = MemoryRecord(
                record_id=f"rec{i}", project="meridian", kind=MemoryKind.DECISION,
                summary=f"Record {i}", body="...", source=MemorySource.PRIME,
                created_at=created, importance=3, pinned=False, tags=(),
            )
            repo.add(record)
        hits = repo.query(MemoryQuery(project="meridian", limit=100))
        assert len(hits) == repo.HARD_LIMIT

    def test_empty_store_returns_empty(self, repo):
        hits = repo.query(MemoryQuery(project="meridian"))
        assert len(hits) == 0


class TestFailureSoftCorruptRecords:
    def test_query_normalizes_naive_created_at(self, repo):
        naive_created = datetime.fromisoformat("2026-05-31T12:00:00")
        aware_created = datetime.fromisoformat("2026-05-31T13:00:00+00:00")
        repo.add(
            MemoryRecord(
                record_id="naive",
                project="meridian",
                kind=MemoryKind.DECISION,
                summary="Naive timestamp",
                body="...",
                source=MemorySource.IMPORT,
                created_at=naive_created,
                importance=3,
                pinned=False,
                tags=(),
            )
        )
        repo.add(
            MemoryRecord(
                record_id="aware",
                project="meridian",
                kind=MemoryKind.DECISION,
                summary="Aware timestamp",
                body="...",
                source=MemorySource.PRIME,
                created_at=aware_created,
                importance=3,
                pinned=False,
                tags=(),
            )
        )

        hits = repo.query(MemoryQuery(project="meridian"))

        assert [hit.record.record_id for hit in hits] == ["aware", "naive"]

    def test_query_since_handles_naive_created_at(self, repo):
        naive_created = datetime.fromisoformat("2026-05-31T12:00:00")
        repo.add(
            MemoryRecord(
                record_id="naive",
                project="meridian",
                kind=MemoryKind.DECISION,
                summary="Naive timestamp",
                body="...",
                source=MemorySource.IMPORT,
                created_at=naive_created,
                importance=3,
                pinned=False,
                tags=(),
            )
        )

        hits = repo.query(
            MemoryQuery(
                project="meridian",
                since=datetime.fromisoformat("2026-05-31T11:00:00+00:00"),
            )
        )

        assert len(hits) == 1
        assert hits[0].reason.endswith("recent")
