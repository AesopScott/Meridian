"""Backend snapshot for Source/Git Runtime Logic shown in the harness UI."""

from __future__ import annotations

import json

SNAPSHOT_VERSION = "source-git-runtime-v1"


def source_git_logic_snapshot() -> dict:
    """Return the Source/Git capability list used by Bifrost's visible harness."""
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.source_git_logic_snapshot.source_git_logic_snapshot",
        "harness": "Source / Git",
        "status": "coordination-display-only",
        "summary": (
            "Source/Git owns visibility into branch, worktree, main-write, push, and movement gates. "
            "The visible panel documents the protocol; it does not commit, push, rebase, merge, reset, or move work."
        ),
        "sourceRefs": [
            "docs/main-write-coordination-handoff.md",
            "docs/main-write-coordination-ledger.md",
            "docs/ui-integration-checklist.md",
            "docs/harness-stage-checklist.md",
        ],
        "capabilitySections": [
            {
                "title": "Source/Git Job",
                "summary": "Make Git and worktree state legible without turning the cockpit into a mutation surface.",
                "rows": [
                    {"key": "owns", "value": "branch/worktree visibility, main-write gate status, path-limited lease state, proof and push status"},
                    {"key": "does not own", "value": "silent commits, pushes, merges, rebases, resets, stash-pop, cherry-picks, or cross-worktree movement"},
                    {"key": "display rule", "value": "show protocol state and blockers; actions stay outside this panel until a later approved backend exists"},
                ],
            },
            {
                "title": "Main Write Gate Logic",
                "summary": "Shared main writes require coordination before any movement or push can occur.",
                "rows": [
                    {"key": "intent", "value": "post exact requested action, base, path-limited scope, reason, proof, and duration"},
                    {"key": "ACK", "value": "wait for explicit ACK, denial, or narrower scope from the other lane"},
                    {"key": "lease", "value": "default window is 10 minutes after ACK unless the ledger says otherwise"},
                    {"key": "expired", "value": "post expired/aborted and request a fresh ACK before retrying"},
                ],
            },
            {
                "title": "Clean-State Logic",
                "summary": "Git movement is blocked unless shared main and affected worktrees are clean at the gate.",
                "rows": [
                    {"key": "shared main", "value": "on main, fetched from origin/main, no staged/dirty/untracked worker artifacts"},
                    {"key": "affected branch", "value": "clean before movement or handoff"},
                    {"key": "ledger", "value": "re-read immediately before every write attempt and stop on conflicting lease/blocker"},
                    {"key": "scope", "value": "perform only the approved path-limited action"},
                ],
            },
            {
                "title": "Completion Proof Logic",
                "summary": "Every approved movement must leave an auditable proof trail.",
                "rows": [
                    {"key": "commit", "value": "record commit hash or pushed hash after the write"},
                    {"key": "proof", "value": "record targeted tests, diff checks, status/rev-list, and any text/encoding scans"},
                    {"key": "files", "value": "record changed files and confirm they match approved scope"},
                    {"key": "final state", "value": "fetch and report final clean/aligned main status or blocker"},
                ],
            },
            {
                "title": "Cross-Harness Relationship Logic",
                "summary": "Source/Git enforces movement boundaries around other harness work instead of owning their implementation.",
                "rows": [
                    {"key": "Prime", "value": "may recommend movement, but the coordination gate controls shared-main writes"},
                    {"key": "Aegis", "value": "reviews proof, policy, and unsafe movement risk"},
                    {"key": "Bifrost", "value": "renders state and proof without performing Git mutations"},
                    {"key": "Vulcan", "value": "provides session/worktree state context for clean-state checks"},
                    {"key": "Charon", "value": "keeps FileMap scope visible when branch movement touches docs or runtime files"},
                ],
            },
            {
                "title": "Runtime Boundary",
                "summary": "This panel is display-only and cannot execute Git or filesystem movement.",
                "rows": [
                    {"key": "display", "value": "backend snapshot only"},
                    {"key": "blocked", "value": "no commit, no push, no merge, no rebase, no reset, no stash-pop, no cherry-pick"},
                    {"key": "future backend", "value": "native Source/Git runtime requires explicit approval objects, policy gates, and audit records before any action"},
                ],
            },
        ],
        "runtimeFlags": {
            "commit": False,
            "push": False,
            "merge": False,
            "rebase": False,
            "reset": False,
            "cherryPick": False,
            "stashPop": False,
            "displayOnly": True,
        },
    }


def main() -> None:
    print(json.dumps(source_git_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
