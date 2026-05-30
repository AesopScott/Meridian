# Live Codex Reviews C Queue

This file is the standing queue for a third specialized Codex Reviews session.

Review C exists because review capacity became the bottleneck. It is a bounded specialist lane, not a duplicate of Review A or Review B.

## Role

Codex Reviews C owns V0 runtime-gate review slices assigned by Prime/Codex when Review A is overloaded.

Default split:

- Review A (`docs/live-codex-reviews.md`) owns broad runtime, package API, tests, behavior, and code-level regression reviews.
- Review B (`docs/live-codex-reviews-2.md`) owns docs, architecture, FileMap, Bifrost, and strategic consistency reviews.
- Review C owns explicitly delegated V0 gate reviews: Mission Boot, Review Console visibility, Relay executor skeletons, Aegis/Relay gate wires, and narrow runtime readiness checks.

Review C must declare scope before reviewing. It must not silently broaden into Review A or Review B territory.

## Rules

- Always pull latest `origin/main` before reviewing.
- Do not implement product code.
- Do not edit runtime files, package exports, or tests.
- Own only this review queue plus repair routing into the relevant build queue when actionable findings are found.
- Review completed build slices by commit hash.
- Inspect the target diff and directly necessary supporting files only.
- Run targeted tests for runtime slices.
- Record proofs for every review pass. A pass without proof is not a clearance.
- If there are actionable findings, write a repair Active Task back into the original build lane queue.
- CRITICAL and HIGH findings block the lane until repaired.
- MEDIUM findings should usually be repaired before more work unless intentionally deferred.
- LOW findings may be deferred, but must be recorded.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build` when a review finds or clears important V0 gate issues.

## Review Inputs

Poll these files:

- `docs/live-build-1.md`
- `docs/live-build-2.md`
- `docs/live-codex-reviews.md`

Look for:

- `Ready for Codex Review`
- V0 gate commits awaiting review
- cadence-paused Build 1 or Build 2 work
- repair tasks waiting for verification
- scope notes from Review A that delegate work to Review C

## Checkpoint Ledger

| Build lane | Last reviewed commit | Last reviewed task | Review status | Pending finding / repair | Next action |
| --- | --- | --- | --- | --- | --- |
| Build 1 | d2820d2 | WorkerLaneState domain model reviewed by Review A Round 2 | passed | none for Review C | review delegated Relay executor skeleton |
| Build 2 | 46e4eb3 | Relay package API policy note reviewed by Review A Round 2 | passed | none for Review C | review delegated V0 CLI gate commits |

## Review Round Scope

Before starting each review round, write the scope here.

```text
YYYY-MM-DD HH:MM TZ - Round C<n> scope
Build lanes: <Build 1, Build 2>
Commit range(s): <Build 1 abc; Build 2 def..ghi>
Allowed review files: <diff files only or named supporting files>
Tests to run: <targeted tests>
Out of scope: <areas explicitly not reviewed>
Reason: <delegated review, cadence review, repair verification>
```

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Codex Reviews C checked queue; status: idle/running/blocked; notes: <short note>
```

## Review Log

Append one entry per reviewed slice.

```text
YYYY-MM-DD HH:MM TZ - Reviewed Build <n> commit <hash>; result: pass/finding/blocked; tests: <summary>; notes: <short note>
```

## Proof Log

Append proof entries here before marking a slice passed.

```text
YYYY-MM-DD HH:MM TZ - Proof for Build <n> commit <hash>; proof type: diff/test/reference/manual; evidence: <short reproducible evidence>; result: pass/fail/deferred
```

Minimum proof expectations:

- Runtime/code slices: targeted tests plus diff inspection.
- CLI slices: focused CLI tests plus deterministic output inspection.
- Review Console slices: status/type/provenance inspection plus targeted tests.
- Relay executor slices: dispatch-boundary tests proving only lane payload text reaches the injected callable.
- Repair verification: original finding, repair commit, and test/reference evidence that the finding is closed.

## Findings

Append findings here before routing repairs.

```text
YYYY-MM-DD HH:MM TZ - Build <n> commit <hash>; severity: CRITICAL/HIGH/MEDIUM/LOW; file: <path>; finding: <short note>; action: clear/defer/repair-task-written
```

## Repair Routing Log

Append entries when writing repair work into a build lane.

```text
YYYY-MM-DD HH:MM TZ - Routed repair to Build <n>; queue: docs/live-build-<n>.md; finding: <short note>; status: pending
```

## Active Task

Current Active Task:

Goal: perform Codex Reviews C Round C1, delegated V0 runtime-gate review.

Scope:

- Build 1 commit `190e527` - V0 Relay executor skeleton.
- Build 2 commit `e800c03` - V0 `prime_wake` CLI surface.
- Build 2 commit `989366f` - V0 `prime_console`, `prime_status`, and `route_to_console` CLI visibility surface.
- Include queue marker commits only as provenance, not product scope.

Required proof:

- For Build 1 `190e527`, inspect `meridian_core/relay_executor.py` and `tests/test_relay_executor.py`.
- Run `python -m pytest tests/test_relay_executor.py -q`.
- Confirm the executor forwards only lane payload text to the injected callable.
- Confirm no vendor/API/account automation was introduced.
- Confirm exceptions are captured per lane and do not stop other lanes.
- For Build 2 `e800c03`, inspect the CLI diff and tests.
- Run the focused CLI tests covering `prime_wake`.
- Confirm mission load failures surface clearly.
- Confirm wake output is deterministic and suitable for the non-orchestrator/system surface.
- Confirm no persistence or Bifrost UI was introduced.
- For Build 2 `989366f`, inspect `meridian_core/cli.py`, `meridian_core/review_console.py`, and `tests/test_cli.py`.
- Run the focused CLI and Review Console tests touched by the slice.
- Confirm `route_to_console()` does not create durable persistence or bypass existing Review Console status/type semantics.
- Confirm `prime_console` and `prime_status` output is deterministic and suitable for V0 CLI visibility.

Output:

- Declare Round C1 scope in Review Round Scope.
- Update Checkpoint Ledger.
- Update Review Log.
- Update Proof Log.
- Record findings, if any.
- Route repairs to Build 1 or Build 2 if actionable.
- If clean, mark Round C1 complete and note that Build 2 cadence is cleared for the three-commit window ending at `989366f`.
