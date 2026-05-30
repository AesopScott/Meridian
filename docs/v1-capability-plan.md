# Meridian V1 Capability Plan

**Status:** Architecture plan — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Source:** `docs/v0-v1-progress-tracker.md`, `docs/v0-build-readiness-map.md`, `docs/prime-orchestration-state-model.md`
**Purpose:** Turn the 12 V1 tracker items into a coherent build sequence, assign ownership, surface risk areas, and name the first 10 commit-sized slices.

---

## V1 Definition

V1 begins after Prime can wake, report status, dispatch one worker through Relay, show review/gate items, and enforce proof gates (V0 complete).

V1 turns that CLI-capable Prime into a **cockpit-backed, memory-backed, multi-lane orchestrator** that can coordinate work across days without Scott prompting the next step.

### V1 Success Test

Prime wakes autonomously, recalls relevant context from Echo + Atlas, dispatches a real worker session through Relay, Aegis verifies proof, Relay clears the dispatch, Bifrost shows harness status, and Prime decides the next move — all without a human prompt. A full session lifecycle completes: **spawn → execute → Aegis verify → Relay clear → Bifrost display → Prime continues**.

Scott's role in V1: judgment calls, gate approvals, direction changes. Not prompt-by-prompt steering.

---

## What Must Wait for V0 to Complete

These V1 capabilities depend on working V0 dispatch infrastructure and cannot be meaningfully implemented until V0 gates are cleared:

| Capability | V0 dependency |
|---|---|
| Session lifecycle harness | Working `relay_executor.py` dispatch |
| Bifrost live UI implementation | Domain objects + harness events from working wiring |
| Dynamic RTDSG Cognition runtime | End-to-end Aegis proof gates + session lifecycle |
| Multi-user / multi-Meridian federation | Stable single-Meridian V1 first |
| Model harness adapters (account-based path) | Working API dispatch compartmentalized cleanly |

**Gate:** Do not begin runtime implementation on any of the above until `docs/v0-build-readiness-map.md` shows all 6 V0 gate items as Built.

---

## What Can Be Designed in Parallel Now

These items have no runtime V0 dependency — design work and domain model definition can proceed concurrently with V0 build:

| Capability | Parallel work available |
|---|---|
| Echo memory store | Schema, `MemoryEntry` / `MemoryStore` interface, eviction policy, write-verify protocol |
| Atlas retrieval / RAG harness | Query interface design, FileMap integration spec, scoring model |
| Bifrost cockpit shell | Scaffold design is done; implementation scaffold can start (no live data binding yet) |
| Dynamic RTDSG Cognition | Spec and decision-tree design; runtime wiring waits for V0 |
| Model harness adapters (public API path) | API-first design can be specified independently of account-based automation path |

**Rule:** Design-only slices (docs + domain models) are Build 4 territory. Runtime implementation slices belong to the builder lanes named in the ownership table below.

---

## Capability Dependency Order

```
V0 complete (all 6 gate items Built)
  │
  ├── Echo memory store         (domain model → persistence layer)
  │     └── Atlas retrieval    (needs Echo for memory-backed queries)
  │           └── Multi-lane orchestrator loop  (Prime needs memory + retrieval)
  │
  ├── Session lifecycle harness  (spawn/steer/wait/stop/archive)
  │     └── Dynamic RTDSG Cognition runtime  (needs lifecycle + Aegis proof gates)
  │
  ├── Bifrost cockpit scaffold   (shell only, no live data)
  │     └── Bifrost ReviewConsoleQueue binding  (live queue panel)
  │           └── Bifrost full live UI  (all panels: status, progress, proof)
  │
  ├── Model harness adapters
  │     ├── Public API path (first)
  │     └── Account-based automation path (after public path is stable)
  │
  └── Multi-user / federation   (last — depends on stable V1)
```

---

## Recommended Builder Lane Ownership

| Capability | Primary lane | Secondary |
|---|---|---|
| Echo memory store domain model | Build 2 (domain/API) | Build 4 design |
| Echo persistence layer | Build 2 | — |
| Atlas FileMap query interface | Build 3 (FileMap) | Build 4 design |
| Atlas retrieval implementation | Build 3 | — |
| Session lifecycle harness | Build 1 (runtime) | — |
| Bifrost cockpit scaffold | Build 5 (progress/proof) | — |
| Bifrost → ReviewConsoleQueue binding | Build 5 | — |
| Bifrost full live UI | Build 5 | — |
| Dynamic RTDSG Cognition spec | Build 4 | — |
| Dynamic RTDSG Cognition runtime | Build 1 | — |
| Model harness adapters | Build 1 | — |
| Multi-user / federation design | Build 4 | — |
| Multi-lane orchestrator loop | Build 1 | Build 4 design |

---

## Risk Areas

### 1. Model Weakness Without Memory

Prime's ability to orchestrate across sessions degrades rapidly without Echo + Atlas. A session that can't recall what the previous session decided will repeat mistakes or contradict earlier commitments. **Echo + Atlas must land early in V1** — before the multi-lane orchestrator loop, not after.

Mitigation: Build Echo domain model in parallel with V0 build. Do not start the orchestrator loop until Echo persistence is live.

### 2. Prompt Drag

As lanes accumulate context (FileMap, queue files, build notes, Obsidian), prompt sizes bloat. At V1 scale — multiple active lanes, long session histories — unchecked prompt size will hit model limits and degrade quality. Echo compression (summarize + evict) and Atlas selective retrieval (top-N relevant, not full FileMap) are load-bearing.

Mitigation: Design Echo with a TTL-based eviction policy from the start. Atlas retrieval must score and truncate, not dump full context.

### 3. Account-Based Automation Constraints

The account-based automation path (browser automation, Anthropic console access) is fragile, platform-dependent, and subject to policy change. It must live behind a clean boundary — the model harness adapter interface — so Prime's orchestration logic never hard-depends on it.

Mitigation: Public API path ships first. Account-based path is a second adapter implementation behind the same interface. Prime never calls it directly; only the adapter does.

### 4. Memory Correctness

Stale or contradicted memory in Echo = wrong decisions by Prime. Echo must support write-verify (confirm entry is correct before Prime acts on it) and contradiction detection (flag when a new memory entry conflicts with an existing one).

Mitigation: Echo's domain model must include a `verified` flag and a `contradicts` field. Prime queries `verified` entries first. Contradicted entries route to Review Console as CROSS_CHECK items before Prime uses them.

### 5. UI Sprawl

Bifrost wants to show everything: status, proof, progress, queue, session history, memory, Atlas queries. Without a strict surface contract, the cockpit becomes noise and Scott has to read a dashboard to find decisions.

Mitigation: Enforce the V0 surface rule into V1 — the orchestrator thread stays clean (decisions/intentions only), the review console gets evidence/status. Bifrost panels map directly to those two surfaces. Anything that doesn't fit one of those two goes to an archive panel, not the main cockpit.

---

## First 10 Commit-Sized V1 Slices

These are ordered by dependency. Slices 1–4 can begin concurrently with V0 build (design/domain only). Slices 5–10 require V0 complete.

| Slice | Description | Lane | File(s) |
|---|---|---|---|
| 1 | Echo memory store domain model — `MemoryEntry`, `MemoryStore` interface, eviction policy | Build 2 | `meridian_core/echo.py` |
| 2 | Atlas FileMap query interface design brief | Build 4 | `docs/atlas-query-interface-brief.md` |
| 3 | Echo persistence layer — flat-file V0 echo (`~/.meridian/echo.json`) | Build 2 | `meridian_core/echo_store.py` |
| 4 | Dynamic RTDSG Cognition spec (decision engine design, not runtime) | Build 4 | `docs/rtdsg-cognition-spec.md` |
| 5 | Session lifecycle harness — `SessionRecord`, `spawn_session()`, `archive_session()` | Build 1 | `meridian_core/session.py` |
| 6 | Atlas retrieval implementation — top-N FileMap lookup, query scoring | Build 3 | `meridian_core/atlas.py` |
| 7 | Bifrost cockpit scaffold — shell app, panel layout, no live data | Build 5 | `bifrost/` |
| 8 | Bifrost → ReviewConsoleQueue binding — live queue panel with `pending()` and `pending_gates()` | Build 5 | `bifrost/review_panel.py` |
| 9 | Model harness adapter interface — public API path first, account-based path as second impl | Build 1 | `meridian_core/model_adapter.py` |
| 10 | Multi-lane orchestrator loop — Prime polls all lane queues and dispatches based on Relay state | Build 1 | `meridian_core/orchestrator.py` |

---

## V1 Readiness Gate

V1 is shippable when:

1. Prime wakes and recalls prior session context via Echo + Atlas without Scott summarizing it.
2. Prime dispatches a worker through Relay, Aegis verifies the output, and Relay clears — without Scott approving each step.
3. Bifrost cockpit shows current harness state (all lanes) without Scott running `prime_status` in a terminal.
4. A session lifecycle runs end-to-end (spawn → work → verify → archive) with no dropped state.
5. Review Console gate items appear in Bifrost and Scott can approve them from the UI, not the CLI.

---

## What This Plan Is Not

- An implementation spec for any individual slice — those belong in builder lane active tasks.
- A Bifrost UI design — that is `docs/bifrost-cockpit-queue-status-brief.md`.
- An Echo memory schema — that is slice 1 above, owned by Build 2.
- A complete Atlas design — that is slice 2 above, owned by Build 4.

---

## Cross-References

- V0/V1 tracker: `docs/v0-v1-progress-tracker.md`
- V0 capability gaps: `docs/v0-build-readiness-map.md`
- Prime orchestration state model: `docs/prime-orchestration-state-model.md`
- Prime status console: `docs/prime-status-console-cli-brief.md`
- Review Console surface contract: `docs/review-console-surface-contract.md`
- Bifrost cockpit brief: `docs/bifrost-cockpit-queue-status-brief.md`
