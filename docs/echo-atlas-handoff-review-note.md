# Echo-to-Atlas Handoff Review Note

**Date:** 2026-06-09  
**Reviewer:** Build 1  
**Status:** Complete — ready for integration testing and Prime runtime wiring  

## Summary

Echo Memory Harness and Atlas Retrieval Harness are implemented and contractually aligned. Both harnesses are operational and ready to be wired into Prime's context-building layer.

## Completed Work

### Echo Memory Harness (meridian_core/echo.py)
- ✅ MemoryRecord frozen dataclass with project/kind/importance/pinning/tags/supersession fields
- ✅ MemoryKind enum: DECISION, FACT, PLAN, GATE_OUTCOME, STANDING_INSTRUCTION, NOTE
- ✅ MemoryQuery with project filtering, kind filtering, tag filtering, since/limit
- ✅ Deterministic ranking: project > pinning > importance > recency
- ✅ Failure-soft behavior: empty store, unknown projects, corrupt records skipped
- ✅ 21 tests passing; domain contract satisfied

### Atlas Retrieval Harness (meridian_core/atlas.py)
- ✅ AtlasHit frozen dataclass with path/title/reason/excerpt/source/score fields
- ✅ AtlasSource enum: FILEMAP, DOC, ECHO
- ✅ AtlasQuery with terms/areas/required_paths/include_echo/limit
- ✅ DOC_ALLOWLIST hardcoded: MISSION.md, docs/atlas-retrieval-contract.md, docs/echo-memory-contract.md, docs/cognition-policy-contract.md, docs/relay-dispatch-contract.md
- ✅ Deterministic ranking: required_paths (0.99) > path match (0.8) > purpose match (0.7) > notes match (0.5); source priority FILEMAP > DOC > ECHO
- ✅ Failure-soft behavior: empty queries, missing FileMap, excluded areas
- ✅ 33 tests passing; domain contract satisfied

### Handoff Contract (docs/echo-atlas-handoff-contract.md)
- ✅ Defines cooperation boundary and query semantics
- ✅ Documents Echo vs. Atlas query patterns
- ✅ Covers memory freshness vs. retrieval confidence trade-off
- ✅ Specifies Echo-Atlas mismatch detection and gap reporting

## Gaps and Follow-Up Work

### Runtime Objects Needed for Prime Integration

1. **Echo Store Persistence & Lifecycle**
   - Echo tests use in-memory store; production needs file-backed or database-backed durability
   - MemoryQuery needs to be exposed as a public API client in Echo module
   - Add Echo lifecycle: initialization, periodic persistence, schema migration if needed

2. **Atlas Source Providers**
   - FileMap integration is mocked in tests; needs live FileMap client wired in
   - DOC allowlist is hardcoded; should become configuration-driven
   - Add Atlas lifecycle: FileMap refresh on HEAD change, allowlist reload on config change

3. **Prime Composition Layer**
   - No Prime class yet wires both harnesses together
   - Needs composition logic: query Echo for decisions, query Atlas for code, merge results
   - Needs handling of Echo-Atlas mismatches (log and report to Build 3)

4. **Relay Integration**
   - Atlas.query needs to be exposed to Relay for context injection
   - Relay dispatch contract needs to be updated to specify when to use Echo vs. Atlas
   - SessionEnd and session-scoped context caching are not yet wired

### Known Limitations (V2 First Wave Out of Scope)

Per the contract, these are deferred to later waves:
- Real-time Echo indexing in Atlas (Echo fold-in disabled by default)
- Automatic gap detection (Build 3 owns FileMap registration)
- Semantic understanding of Echo records (substring matching only)
- Cross-project queries (each query scoped to one project)
- Transitive reasoning (no Echo→Atlas or Atlas→Echo callbacks)

## How Prime Should Use Echo vs. Atlas

### Query Echo When:
- Recalling a past decision or standing instruction
- Checking a gate outcome or review result
- Looking up a plan or project-specific context
- Need temporal understanding (what was decided when, by whom, why)

### Query Atlas When:
- Finding a file by name or purpose
- Checking a contract document
- Locating related tests or implementation files
- Need spatial understanding (what code implements X, where is doc Y)

### Query Both When:
- Planning a feature (need decisions + code locations)
- Debugging a failure (need instructions + relevant code)
- Validating a design (check decisions, find contract, trace implementation)

## Integration Checklist

Before Prime can go live with Echo/Atlas:

- [ ] Wire FileMap client into Atlas initialization
- [ ] Make DOC_ALLOWLIST configurable
- [ ] Add Echo persistence (file or database)
- [ ] Expose Echo.query() and Atlas.query() as public APIs
- [ ] Create Prime composition layer (PrimeContextBuilder or similar)
- [ ] Add Echo-Atlas mismatch logging to Build 3 reporting
- [ ] Update Relay dispatch contract to reference Echo/Atlas patterns
- [ ] Add session-scoped context caching to Relay
- [ ] Test Echo/Atlas integration end-to-end with Prime
- [ ] Document Prime's context-building workflow in protocol contracts

## Recommendation

**Go forward with Prime runtime wiring.** Both harnesses are solid and the contract is clear. Focus next work on:
1. Wiring FileMap into Atlas (Build 3 responsibility)
2. Creating the Prime composition layer (Prime lane responsibility)
3. Exposing query APIs for Relay integration (Relay lane responsibility)

The separation of concerns (Echo = decisions, Atlas = code) is clean and enables independent evolution.
