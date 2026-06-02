"""Backend snapshot for Aegis proof-gate logic shown in the harness UI."""

SNAPSHOT_VERSION = "aegis-runtime-logic-v1"


def aegis_logic_snapshot() -> dict:
    """Return the Aegis capability list used by Bifrost's visible harness."""
    return {
        "ok": True,
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.aegis_logic_snapshot.aegis_logic_snapshot",
        "harness": "Aegis",
        "summary": "Aegis owns proof gates, policy advisory outcomes, evidence safety, and human-gate visibility. It does not route models, execute commands, or approve itself.",
        "capabilitySections": [
            {
                "title": "Aegis Job",
                "summary": "Convert risk and proof state into visible allow, warn, demote, block, or human-gate outcomes.",
                "rows": [
                    {"key": "owns", "value": "proof gates, evidence severity, advisory decisions, waiver/approval visibility, fail-closed metadata checks"},
                    {"key": "does not own", "value": "model routing, provider calls, command execution, review self-clearance, branch or worktree movement"},
                    {"key": "drift guard", "value": "Aegis decisions must expose evidence refs and blockers rather than hidden rationale"},
                ],
            },
            {
                "title": "Proof Gate Logic",
                "summary": "ProofTrail and AegisEvidence decide whether proof is clean, warning-only, blocking, or escalated.",
                "rows": [
                    {"key": "blocking rule", "value": "error, critical, failed, missing, unsafe, or escalated evidence blocks the related action"},
                    {"key": "allow rule", "value": "allow only when required evidence is present, scoped, non-raw, and non-duplicated"},
                    {"key": "human gate", "value": "high-risk or policy-sensitive action can require explicit human approval before execution"},
                    {"key": "waiver visibility", "value": "waivers must stay scoped and visible; they do not erase underlying risk"},
                ],
            },
            {
                "title": "PromptPacket Policy Logic",
                "summary": "PromptPacket metadata is checked before Relay dispatch can trust a model payload.",
                "rows": [
                    {"key": "required fields", "value": "packet id, packet hash, budget ref, source-lineage refs, Aegis evidence ids, proof requirement"},
                    {"key": "unsafe fields", "value": "raw prompt, raw source text, credentials, account identifiers, process/session-control state"},
                    {"key": "decisions", "value": "allow, warn, demote, block, or human_gate"},
                    {"key": "fail closed", "value": "missing or unsafe metadata blocks before provider transport"},
                ],
            },
            {
                "title": "Prompt Payload Meter Logic",
                "summary": "Aegis evaluates prompt-payload visibility so Bifrost and Prime can see prompt drag before dispatch risk grows.",
                "rows": [
                    {"key": "required telemetry", "value": "payload label, token estimate, budget percent, growth delta, q-mode drag state, route refs"},
                    {"key": "degraded", "value": "unexpected growth, over-budget labels, missing evidence, or unsafe refs degrade or block"},
                    {"key": "display boundary", "value": "Bifrost displays advisory state; Relay and Aegis own computation"},
                ],
            },
            {
                "title": "Provider Result Validation Logic",
                "summary": "Provider-returned metadata cannot promote trust or clear review without structured validation evidence.",
                "rows": [
                    {"key": "checks", "value": "provider id, model id, route kind, trust state, telemetry availability, external review state"},
                    {"key": "blocked evidence", "value": "raw provider response, raw model output, credentials, account state, branch/worktree or push data"},
                    {"key": "trust rule", "value": "successful output alone never upgrades provider trust or review status"},
                ],
            },
            {
                "title": "Command Staging UI Review Logic",
                "summary": "Aegis keeps future live-control command staging display-safe until review and permission gates are explicit.",
                "rows": [
                    {"key": "required visibility", "value": "target, operation, readiness, executability, permission state, review requirement, blockers"},
                    {"key": "blocked by default", "value": "restart, resteer, transfer, archive, and recovery commands stay non-executable without gates"},
                    {"key": "Bifrost role", "value": "render staged command proof and recovery advisory state without executing it"},
                ],
            },
            {
                "title": "Runtime Boundary Logic",
                "summary": "Aegis is a proof and advisory harness, not an automation executor.",
                "rows": [
                    {"key": "safe outputs", "value": "structured decisions, blockers, warnings, evidence refs, missing field lists, redacted display dictionaries"},
                    {"key": "unsafe outputs", "value": "raw prompts, raw provider responses, credentials, hidden session commands, direct filesystem or git mutation"},
                    {"key": "Prime binding", "value": "Prime consumes Aegis aggregate risk as context; Prime still resolves owner and user-visible intent"},
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(aegis_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
