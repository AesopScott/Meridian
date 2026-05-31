# Package API Surface Note

Meridian should expose stable, intentional package-root imports from `meridian_core.__init__`.

Do not automatically export every class from every module. Root exports should be reserved for:

- stable domain objects callers are expected to use directly
- primary builder/loader functions
- small enums that are part of public decision contracts

Prefer module-level imports for experimental or internal helpers.

## Current Export Direction

Already exported (representative sample by domain):

```python
# Progress intention / Compass
from meridian_core import build_progress_intention, ProgressIntention
from meridian_core import MissionObjectiveLine, ObjectiveStage

# Mission boot
from meridian_core import load_mission, find_mission_file, Mission, MissionLoadError

# Wake sequence
from meridian_core import build_wake_brief

# Mission objectives
from meridian_core import get_mission_objectives, format_mission_objectives_text

# Risk tier engine
from meridian_core import assess_tier, assess_blocked_action, RiskTier

# Relay routing
from meridian_core import route_from_tier, route_from_assessment, RelayRoute

# Aegis / proof harness
from meridian_core import AegisEvidence, ProofTrail, evidence_from_cross_check

# Review Console
from meridian_core import ReviewConsoleItem, ReviewConsoleQueue, make_approval_gate
from meridian_core import make_prompt_metrics_finding

# Build and maturity registry
from meridian_core import HarnessBuild, BuildRegistry, make_initial_registry

# File map
from meridian_core import FileMap, FileArea, make_default_map

# Council cognition
from meridian_core import CouncilPlan, council_plan_for_tier

# Relay prompt budget
from meridian_core import PromptBudgetPlan, prompt_budget_for_risk_tier

# Relay prompt metrics
from meridian_core import PromptMetricSample, PromptMetricSummary, summarize_prompt_metrics

# Prompt packet (added Build 2 commit f2f69ff)
from meridian_core import PromptPacket, PromptPacketValidationError, build_prompt_packet
```

## Why PromptPacket Exports Are Safe (as of f2f69ff)

Three properties make `PromptPacket`, `PromptPacketValidationError`, and `build_prompt_packet` safe public surface:

1. **Validated on construction** â€” all validation runs in `PromptPacket.__post_init__`, so a successfully constructed object is always in a valid state. Invalid inputs raise `PromptPacketValidationError` before the object exists.
2. **Immutable lineage** â€” `source_lineage` is copied to a `MappingProxyType` on construction; callers cannot mutate internal state through the original dict.
3. **Clean payload boundary** â€” `model_payload()` exposes only `serialized_prompt`. Packet metadata (tokens, lineage, construction time, tier) never leaks into the text sent to a model.

## What Stays Internal

Private validation helpers (`_validate_*`) and sub-exception types should remain module-level imports, not root exports, until their hierarchy is stable across a review cycle.

**Relay dispatch internals** â€” `assemble_relay_packet`, `RelayDispatchLane`, `RelayDispatchPlan`, and `build_relay_dispatch_plan` are module-level imports only. See `docs/relay-package-api-policy-note.md` for the full reasoning and the proof required before any root export.

## V2 Package Surface

V2 introduces four new harnesses (Echo, Atlas, Session Lifecycle, Bifrost) plus Prime Autonomy. Each harness will have stable domain objects that become root exports once proof review is complete.

For V2 export roadmap and status, see docs/v2-package-api-surface-note.md.

## Candidates for Future Export

No V0/V1 names are currently pending export. All known stable domain objects are already in `__all__`.

Review any new names as a deliberate public API decision before adding to `__all__`.
