# FileMap V2/V3 Discoverability Audit

**Owner:** Build 3 / FileMap
**Purpose:** Keep Prime from losing important V2/V3 architecture context at wake by listing which planning, contract, and horizon files must be discoverable through `meridian_core/filemap.py`.
**Scope:** Docs-only audit. This file records follow-up tasks; it does not authorize runtime edits.

## Rule

Every V2/V3 architecture file that changes Prime behavior, harness ownership, provider trust, session lifecycle, Bifrost cockpit behavior, or V3 intake must be discoverable in the runtime FileMap before Prime can rely on it during orchestration.

## Current Coverage

- [x] `docs/v2-detailed-build-plan.md` - V2 roadmap and build sequencing.
- [x] `docs/v2-progress-tracker.md` - countable V2 status source.
- [x] `docs/agentic-ai-framework-checklist.md` - V3 entry point and framework checklist.
- [x] `docs/v3-parking-lot.md` - V3 horizon parking lot.
- [x] `docs/federation-harness-horizon.md` - Federation planning/horizon contract.
- [x] `docs/workflow-subagent-harness-contract.md` - workflow/sub-agent contract baseline.
- [x] `docs/session-lifecycle-v2-contract.md` - session lifecycle contract baseline.
- [x] `docs/session-card-queue-activation-contract.md` - Q-mode/session card product contract.
- [x] `docs/deepseek-provider-validation-gate.md` - DeepSeek provider trust gate.

## Follow-Up FileMap Tasks

- [ ] Register `docs/workflows-subagent-harness-architecture.md`.
  - Reason: this is the architecture note for using workflow/sub-agent contexts to prevent Prime's orchestrator context from filling with harness working memory.
  - Recommended owner: Build 3.
  - Recommended files: `meridian_core/filemap.py`, `tests/test_filemap.py`, `docs/filemap-v2-v3-discoverability-audit.md`, and optionally `docs/FileMap.md` if the human-readable mirror is in scope.

## Pending Upstream Outputs

These files are expected from queued work but do not exist yet, so they are not FileMap misses today:

- [ ] `docs/bifrost-voice-command-contract.md` - Build 5 active task.
- [ ] `docs/bifrost-balance-payload-surface-contract.md` - Build 5 next candidate.
- [ ] `docs/workflow-subagent-usage-checklist.md` - Build 4 active task.
- [ ] `docs/deepseek-validation-benchmark-plan.md` - Build 4 next candidate.
- [ ] `docs/session-lifecycle-implementation-checklist.md` - Build 2 active task.

## Prime Wake Implication

Until the follow-up FileMap task is complete, Prime can still find the workflow contract baseline, but it may miss the newer architecture note that explains why harness work should move into bounded workflow/sub-agent contexts. That is a V2 orchestration-quality gap, not a runtime blocker.

## Completion Criteria

This audit is complete when it is committed, review-routed, and followed by a small Build 3 FileMap registration task for the listed miss. Do not silently bundle future missing files into unrelated runtime work.
