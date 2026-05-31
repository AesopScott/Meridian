# Bifrost Preview and Electron App Package API Policy

## Overview

Bifrost owns preview-generation and Electron app-shell implementation. This note documents the intentional boundary between Bifrost's UI harness surface and Meridian Core's package-root exports.

**Key principle:** Bifrost UI functions and app-entry concepts stay in the ifrost namespace, not meridian_core.__all__.

## What Bifrost Exports

The ifrost/__init__.py module provides a stable UI harness surface:

- **View-model generation:** CockpitViewModel, HarnessCard, InstrumentBand, LaneRow, ProgressEvent (domain objects for UI state)
- **Rendering:** ender_cockpit_html, sample_cockpit_view_model (UI harness functions)
- **Conversion:** iew_model_from_snapshot (Bifrost → UI state adapter)

These names are intentional public surface under ifrost, and callers should import directly from the Bifrost package:

```python
from bifrost import render_cockpit_html, sample_cockpit_view_model, CockpitViewModel
```

## Why Bifrost Imports Stay in ifrost Namespace

### 1. UI Harness, Not Core Domain

Bifrost is a UI rendering layer for development and debugging. It's not part of Meridian Core's stable domain model:

- **Core domains** (e.g., RiskTier, RelayRoute, CouncilPlan) are abstract decision models; callers need them from Meridian itself.
- **Bifrost domains** (e.g., HarnessCard, InstrumentBand) are UI-specific; Electron app code imports from ifrost directly, not through meridian_core.

### 2. Electron App Ownership

Build 5 owns the Electron app shell and ifrost/preview.py implementation. The app entry-point belongs in app configuration (package.json, app shell startup code), not in Python root exports.

- **Electron commands** (e.g., menu items, ipc handlers) are decoupled from Meridian Core's Python package.
- **Preview generation** will expose a small stable helper only after Build 5 lands it and the boundary is proven in use.

### 3. Avoid File-Writing Exports

Bifrost preview generation may include file I/O helpers (e.g., writing cockpit snapshots, exporting view models). File-writing and I/O operations should stay local to Bifrost, not leak into meridian_core.__all__ as if they were core domain operations.

## Future Preview Additions

When Build 5 lands preview-generation enhancements:

1. Add the helper to ifrost/__init__.py under __all__.
2. If the helper should be callable from external tools (not just the app), document it in ifrost docs.
3. **Do not** add it to meridian_core.__all__ unless it becomes a stable, core-domain-level abstraction (very rare).

## Cross-Reference

See docs/package-api-surface-note.md for the full package export policy and criteria for root-export stability.
