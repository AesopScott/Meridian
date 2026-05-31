# Echo-to-Atlas Retrieval Handoff Contract

**Status:** V2 first-wave contract — defines the cooperation boundary between Echo memory and Atlas retrieval.  
**Owner harnesses:** Echo (durable decisions) and Atlas (file/doc lookup).  
**Audience:** Prime, Echo, Atlas, Relay, Aegis, Build lanes.  
**Purpose:** Explain when Prime queries Echo vs. Atlas, how they complement each other, what each source guarantees, and how Prime composes their results without double-retrieval or stale-context risk.

---

## The Handoff: Who Answers What

Echo and Atlas both surface "what Prime should know," but from different sources and with different freshness guarantees.

| Question | Answer Source | Why |
|----------|---|---|
| "Did we decide X?" | Echo | Echo stores decisions; Atlas does not |
| "What's the plan for Y?" | Echo | Echo stores standing instructions; Atlas does not |
| "Which file handles Z?" | Atlas | Atlas queries FileMap; Echo does not catalog files |
| "What does the relay contract say?" | Atlas (DOC source) | Allowlist docs are always available; Echo may not have them |
| "Is there a past review gate result for this action?" | Echo | Echo stores gate outcomes; Atlas does not |

**Prime's job:** Compose both. Query Echo for standing context (decisions, plans, gates). Query Atlas for file/doc shape (where is the code, what does the contract say). Merge intelligently without assuming Echo and Atlas agree on freshness or scope.

---

## Query Inputs and Scope

### Echo Query

Prime sends a `MemoryQuery` with:
- `project` — the namespace (required for isolation).
- `kinds` — tuple of `MemoryKind` (e.g., `DECISION`, `PLAN`, `GATE_OUTCOME`).
- `tags` — optional filter on memory tags.
- `since` — optional lower bound on creation time.
- `limit` — max hits (default 25, hard cap 25).
- `include_superseded` — whether to include old/replaced records.

Echo returns `MemoryHit` objects with score, record, and reason.

### Atlas Query

Prime sends an `AtlasQuery` with:
- `terms` — tuple of search terms (Prime tokenizes; Atlas does substring matching).
- `areas` — optional FileMap area filter.
- `required_paths` — paths that must be in the hit set (e.g., contract docs).
- `include_echo` — bool (default false; experimental Echo fold-in).
- `project` — optional project key (for future Echo-aware features).
- `limit` — max hits (default 25, hard cap 25).

Atlas returns `AtlasHit` objects with path, title, reason, source (FILEMAP/DOC/ECHO), and score.

---

## Source Ranking and Freshness

### Echo: Authored Recency

Echo records are authored by Prime, Scott, workers, or the system. Their age and mutation history are explicit:
- **Freshness:** Latest record for a project/kind/tag wins; superseded records are ranked lower.
- **Mutation:** Records append-only; supersession is logged.
- **Confidence:** High—Echo records are intentional decisions, not inferred from code.

### Atlas: File/Doc State at HEAD

Atlas reads FileMap and the doc allowlist at query time. Their freshness matches the current `origin/main` state:
- **Freshness:** As fresh as the last commit; no staleness unless the FileMap entry itself is stale.
- **Mutation:** FileMap is mutated by Build 3; doc allowlist is code (reviewed as part of slices).
- **Confidence:** High for file presence/purpose; lower for relevance (substring matching, not semantic).

### Echo + Atlas Together

When Prime needs both:
1. Query Echo for standing context (plans, decisions, gates).
2. Query Atlas for file/doc shape (where is the code, what does the contract say).
3. **Do not assume they agree on freshness.** Echo might say "we decided to use FileX" but Atlas might not find FileX in FileMap (gap). Report this gap to Build 3 if it occurs.

---

## Memory Freshness vs. Retrieval Confidence

| Scenario | Echo | Atlas | Action |
|----------|------|-------|--------|
| "Use module X" decision exists; FileX is in FileMap. | High freshness | High confidence | Safe to proceed |
| "Use module X" decision exists; FileX is NOT in FileMap. | High freshness | Low confidence | Report FileMap gap to Build 3; check why FileX is missing |
| No decision exists; FileX is in FileMap with purpose. | No context | High confidence | FileMap entry is stale or standalone; confirm with Scott if needed |
| Neither Echo nor Atlas has context. | Missing | Missing | No context available; decide based on other signals |

---

## No-Result Behavior and Stale-Context Warnings

### Echo Returns Empty

If Echo has no records matching the query:
- **Expected:** Normal; Echo only stores what was explicitly written.
- **Action:** Do not treat empty Echo as "no decision was made." Empty Echo means "no record found matching these criteria." Ask Atlas for file/doc context and proceed.

### Atlas Returns Empty

If Atlas has no hits matching the terms:
- **Expected:** Normal; the file/doc may not be in FileMap or allowlist.
- **Action:** If the query included `required_paths`, report missing paths. Otherwise, refine the search terms or ask Echo for a reference.

### Stale-Context Warning: Echo-Atlas Mismatch

If Echo references a file that Atlas cannot find:
- **Trigger:** Echo returns a record naming "file X"; Atlas query for "X" returns no hits.
- **Action:** Record this gap; it may mean the file was deleted, renamed, or never registered in FileMap.
- **Owner:** Build 3 (FileMap lane) owns closing the gap.

---

## How Prime Composes Results

### Typical Flow

1. Prime receives a task (e.g., "advance project Y").
2. Prime queries Echo: `MemoryQuery(project="Y", kinds=(PLAN, DECISION))` to recall what was decided about Y.
3. Prime queries Atlas: `AtlasQuery(terms=("Y", "plan"), areas=("meridian_core",))` to find which files implement Y.
4. Prime merges the results: Echo says "Use module Z" (decision); Atlas finds the Z file (confidence).
5. Prime hands both to Relay for prompt injection (if policy permits).

### When to Query Only Echo

- Checking a gate outcome (did we pass the Aegis check for this action?).
- Recalling a standing instruction (do we have a rotation policy?).
- Looking up a past decision (why did we choose provider X?).

### When to Query Only Atlas

- Finding a file by name or purpose.
- Checking a contract doc (e.g., the Relay dispatch contract).
- Looking for related tests (FileMap `related_tests` field).

### When to Query Both

- Planning a feature change (need both decisions and code locations).
- Debugging a failure (need standing instructions and the relevant code).
- Validating a design (check decisions, find the contract doc, trace the implementation).

---

## No Collapsing: Two Harnesses, One Answer

Echo and Atlas are separate intentionally. **Do not merge them into a single "context retrieval" harness.** Each owns a domain:

- **Echo:** decisions, standing instructions, gate outcomes, plans, notes (temporal, authored, mutable).
- **Atlas:** file/doc shape, FileMap entries, code structure (spatial, derived from repo state, read-only per session).

Their separation lets Prime:
- Audit decisions separately from code changes.
- Update decisions without re-indexing code.
- Keep code changes independent of standing instructions.
- Replay historical decisions even after code refactors.

If Prime needs context that spans both domains, compose the results at the Prime layer. Do not try to make Atlas "smart" about Echo records or vice versa.

---

## Implementation: Thin Contract, Two Clients

This contract is a guide, not a protocol. Implementation:

1. **Echo client:** Prime calls `echo_store.query(MemoryQuery(...))` and gets back `tuple[MemoryHit, ...]`.
2. **Atlas client:** Prime calls `atlas.query(AtlasQuery(...))` and gets back `AtlasResult(hits, missing_paths, truncated)`.
3. **Composition:** Prime merges, filters, ranks the combined results based on its own logic. No callback from Echo to Atlas or vice versa.

---

## Out of Scope for V2 First Wave

- Real-time Echo indexing in Atlas (Echo fold-in is disabled by default; experimental if enabled).
- Automatic gap detection (Build 3 owns FileMap registration and gap closure).
- Semantic understanding of Echo records (Prime tokenizes; Atlas does substring matching).
- Cross-project queries (each query is scoped to one project).
- Transitive reasoning (Echo doesn't look up Atlas; Atlas doesn't evaluate Echo).

These belong to later V2 waves after the separation is proven in real Prime sessions.
