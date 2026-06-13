# V1 Bifrost Cockpit Implementation Brief

**Status:** Product / implementation-oriented — no runtime code yet, but specifies what V1 will build
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Bifrost UI implementers, Prime runtime engineers, Beacon/Aegis/Compass integrators
**Source briefs (do not edit in this slice):**
- `docs/bifrost-session-queue-activation-brief.md` — activation policy + per-session Q mechanism
- `docs/bifrost-cockpit-queue-status-brief.md` — what queue/lane state is shown and where
- `docs/bifrost-v0-cockpit-layout-brief.md` — V0 cockpit composition
- `docs/bifrost-harness-dashboard-brief.md` — Harness dashboard surface
- `docs/bifrost-configurable-progress-surface-brief.md` — configurable Progress Surface (right-side feed)

V0 is CLI-first: `python -m meridian_core.cli` prints a wake brief, harness Go calls, and an inspectable text summary. V1 is the first **real** Bifrost cockpit — a Prime-centered, browser-rendered surface that turns the source briefs into the user's everyday experience of Meridian.

This brief specifies what V1 builds, what V1 does not build, and which UI slices land first.

---

## 1. V0 → V1 Inversion

V0 contributions V1 inherits without rebuilding:

- `meridian_core` domain objects: Compass bearing, Beacon heartbeat events, Risk Tier, Council plan, Aegis proof shape, Relay route, PromptPacket / PromptBudget, harness registry stubs.
- The five Bifrost source briefs above. The cockpit is composed by V1 from their contracts, not re-derived.
- CLI wake brief format. The audio-first NASA-style Go sequence (`bifrost-v0-cockpit-layout-brief.md` §8) is already shaped as ordered lines; V1 reads from the same source and renders to audio + visual instead of stdout.
- Backlog / queue file conventions for the live build lanes. The flat-file queues remain the durable substrate; V1 surfaces them, does not replace them.

V0 → V1 inversions V1 makes load-bearing:

| Concern | V0 today | V1 target |
|---|---|---|
| Primary surface | Terminal `print(...)` | Browser cockpit, Prime-centered |
| Driving the worker poll loop | A human pastes the strict polling command into each lane's CLI session | Prime owns the dispatch; lanes are subscribed runtime objects |
| Queue activation | Implicit (lane keeps polling because Scott told it to) | Explicit `Queue: ON / OFF / PAUSED / DEGRADED / BLOCKED` policy with a single global control |
| Progress & proof events | Scattered across `docs/live-build-N.md` and `docs/live-codex-reviews*.md` | Routed to the Progress Surface (right-side feed), with audit retained in the same flat files |
| Harness state | Inferred from the wake brief and ledger files | Rendered live from a typed harness registry, fed by Beacon heartbeats |
| Cross-lane coordination | Scott reads several queue files and routes manually | Prime sees every queue, dispatches, and surfaces only what needs Scott's eyes |

V1's success criterion is that Scott's day-to-day no longer requires reading raw `docs/live-build-N.md` content — he reads Prime, the Review Console, the Progress Surface, and the lane row strip.

---

## 2. Page / Screen Layout (V1)

V1 ships a single cockpit page. The layout descends directly from `docs/bifrost-v0-cockpit-layout-brief.md` (the design contract) and `docs/bifrost-configurable-progress-surface-brief.md` (which adds the right-side feed):

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Settings  Projects  Reset  Close  Cross Check  Backlog  Skills  [Harness●]  │
│  Search  Mission Objectives                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  Project: Meridian  ·  Bearing: V1 Cockpit  ·  Tier: 2  ·  Prime: online    │
│ ┌─────────────────────────────────────────┐ ┌────────┐ ┌──────────────────┐ │
│ │  [Orchestrator Queue]  [Review (3)]     │ │ Lanes  │ │ Progress  (all) ▾│ │
│ │                                          │ │ ────── │ │ ──────────────── │ │
│ │   Prime: Good morning, Scott.            │ │ B1 run │ │ 13:32  Build 5  │ │
│ │   Three items in the Review Console;     │ │ B2 pol │ │   running task  │ │
│ │   one needs your judgment.               │ │ B3 blk │ │ ──────────────── │ │
│ │                                          │ │ B4 idl │ │ 13:09  Reviews B │ │
│ │   [scrollable conversation]              │ │ B5 run │ │   a412e90 pass  │ │
│ │                                          │ │        │ │ ──────────────── │ │
│ │   ┌────────────────────────────────────┐ │ │ 5 tot. │ │ 12:48  Aegis    │ │
│ │   │ > _                                │ │ │ 1 attn │ │   proof 47/47   │ │
│ │   └────────────────────────────────────┘ │ │        │ │ ──────────────── │ │
│ └─────────────────────────────────────────┘ └────────┘ │ Filter Mute Pin   │ │
│                                                        └──────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Beacon ✓  Relay route ✓  Aegis ✓  Compass ✓  Queue ON  Tier 2  v1.0  13:32  │
└──────────────────────────────────────────────────────────────────────────────┘
```

The four content surfaces and one band, restated:

1. **Top nav** — Settings, Projects, Reset, Close, Cross Check, Backlog, Skills, Harness, Search, Mission Objectives. Harness carries a health glyph + count badge.
2. **Prime panel** (dominant, top/center) — Orchestrator Queue (default tab) + Review Console (badged tab).
3. **Lane side band** (right of Prime) — compressed per-lane rows from `bifrost-cockpit-queue-status-brief.md` §3.
4. **Progress Surface** (right of Lane band) — typed event feed from `bifrost-configurable-progress-surface-brief.md`.
5. **Bottom instrumentation band** — Beacon, Relay, Aegis, Compass, Queue state, Risk Tier, build number, clock.

The lane band and Progress Surface can be merged into a single right-side column at narrow viewport widths (≥ 1280 px keeps them separate; below that, lane band collapses to the top of the column).

---

## 3. Prime As The Main Conversation Surface

The Prime panel hosts two tabs in the same dominant zone (`bifrost-v0-cockpit-layout-brief.md` §3):

- **Orchestrator Queue** — Scott ↔ Prime conversation. Default tab on cockpit open. Persistent across sessions.
- **Review Console** — promptable review/gating surface for plans, cross-check, Codex review, Aegis proof, comparisons, artifacts.

V1 implementation contract:

- The Orchestrator Queue is the only place Scott types to Prime in V1.
- Prime's responses stream in; Bifrost shows tokens as they arrive, with a single steady cursor (no Polaris-style multi-card animation).
- Quick reply buttons (`Yes / No / Continue / Confirmed`) live under the input. Contextual buttons (`Approve / Hold / Retry / Transfer / Verify`) appear only when Prime poses a decision and disappear on response.
- A single header strip shows: project, bearing, risk tier, Prime status (`online / thinking / waiting on Scott / blocked`). The strip is the only cockpit element allowed to update at sub-second cadence outside of streaming tokens.
- The Review Console tab badge encodes count + max severity. Clicking a Review Console entry opens it as a card inside the tab; disposition controls (`approve / hold / reject / send back to lane`) act in-place.
- Tab state is per-project. Switching projects swaps both tabs' content.

Anti-rules carried from `bifrost-cockpit-queue-status-brief.md` §5 and `bifrost-v0-cockpit-layout-brief.md` §3:

- The Orchestrator Queue does not host worker heartbeats, routine review results, or progress events.
- The Review Console does not become a chat.
- No third tab in V1.

---

## 4. Non-Orchestrator / Review / System Prompt Surface

The Review Console is the second prompt surface (`docs/non-orchestrator-surface-naming.md` resolved the naming question). V1's implementation contract:

- Items arrive as typed objects, not formatted text. Each carries `source / category / severity / summary / artifact reference / disposition actions`.
- Items group by severity (highest first), then by lane, then by arrival time.
- Each item has at minimum three disposition actions: `approve`, `hold`, `send back to lane`. Higher-severity items may add `reject` and `escalate to Aegis`.
- A dispositioned item moves to a per-project history pane (collapsed by default) and produces a follow-up Progress Surface card.
- Items with proof artifacts (Aegis pass/fail, Codex review diff) open the artifact inline. The artifact viewer is one of the V1 UI slices (§10).
- The Review Console is the only place Prime asks Scott for irreversible / public / account-risking decisions. Each such item enters the Orchestrator Queue as one short summon line plus a link to the Review Console entry.

V1 explicitly does not:

- Re-implement the Polaris approval handler as chat.
- Auto-resolve items based on time-out. Dispositioning is Scott's; Prime may surface a hint that an item is stale.
- Allow direct edits to artifacts from the Review Console. Edits go through the originating lane.

---

## 5. Progress / Proof Right-Side Surface

The Progress Surface (right column, below the Lane band) renders typed events per `bifrost-configurable-progress-surface-brief.md`.

V1 contract:

- Eight V0 categories shipped: `routine progress / blocker / review result / proof summary / repair routed / completion / human gate / system health`. Producer-emitted, never inferred.
- Each card has: source, category, severity glyph, timestamp, summary, drilldown ref.
- Filter / Mute / Pin / Collapse / Severity threshold inline on each card and in a surface settings panel.
- Quiet mode globally (settings panel).
- Retention default: last 200 entries or last 24 hours. Older entries roll to `events.jsonl` / Vault.
- Burst suppression aggregates ≥ 8 same-category events within 30 seconds into a single rolled-up card.
- Codex Reviews lanes (`docs/live-codex-reviews.md`, `docs/live-codex-reviews-2.md`) emit `review result` and `repair routed` cards. Aegis emits `proof summary` cards.
- A `human gate` card mirrors a Review Console entry; clicking the card opens the Review Console tab to that entry.

V1 explicitly does not:

- Push notifications to external destinations (held for V2 per `bifrost-configurable-progress-surface-brief.md` §9).
- Allow Scott to chat into the Progress Surface. It is receive-only.
- Implement custom categories. The eight typed categories are the V1 set.

---

## 6. Harness Dashboard Entry Point

The Harness button in the top nav opens the dashboard per `docs/bifrost-harness-dashboard-brief.md`.

V1 contract:

- Dashboard opens as a routed destination. The bottom instrumentation band stays visible. The Prime panel pauses (does not unload) and resumes on close.
- Cards render in domain groups (cognition / knowledge / coordination / queue / planned) with a group dropdown.
- Each card shows the uniform field set: name, role one-liner, status (Beacon), maturity (registry), version, last heartbeat, recent event (one line), capability chips, active links, attention flag.
- Observation-only V1: no start / stop / restart / pause / threshold-edit / capability-toggle controls (`bifrost-harness-dashboard-brief.md` §4).
- Drilldown panel on click: recent events feed, capability docs, recent errors, recent routes for that harness.
- Planned harnesses appear as placeholder cards. Their presence is informative.

V1 implementation requires a typed **Harness Registry** to exist in `meridian_core`. The registry is the source of truth for maturity, capabilities, and role one-liners. Without it, the Harness button cannot ship.

---

## 7. Queue State And Worker / Session Visibility

The Lane side band renders compressed per-lane rows per `docs/bifrost-cockpit-queue-status-brief.md` §3.

V1 contract per lane row:

- Fields: `lane id | role | status | last poll | last commit | attention?`. No prose.
- Sorted: attention first, then running, then polling, then idle, then offline.
- Status is one of the canonical set: `idle / polling / running / blocked / needs review / needs human gate / stale / offline`.
- The status value comes from Beacon's heartbeat events for that lane, not from anything streamed inside the lane.
- The bottom of the band shows a one-line summary: `<count> total | <attention> need attention | <blocked> | <stale>`.
- Clicking a lane row opens a **lane detail panel** as an adjacent drilldown (does not replace Prime). Detail shows: current Active Task text, latest Read Checks / Write Log entries, last commit hash + diff link, reason for `blocked` / `stale` if applicable, backend `steering_mode`, lane diagnostic log, and the action set (force-poll / pause / resume / open queue file / transfer).

Worker / session visibility deliberately stays compressed. No worker-card grid as the default view, even when there are five lanes (`bifrost-cockpit-queue-status-brief.md` §10 / `bifrost-v0-cockpit-layout-brief.md` §6 / §10).

Queue activation surfaces in two places:

- The bottom instrumentation band carries one cell showing `Queue: ON / OFF / PAUSED / DEGRADED / BLOCKED` (`bifrost-cockpit-queue-status-brief.md` §2).
- Clicking the cell opens the global activation control with reason and last-changed-by.

The cockpit must distinguish "we chose to stop" from "we cannot start." `OFF` ≠ `BLOCKED` ≠ `DEGRADED`.

---

## 8. Prime-Owned Q Polling

The single biggest V0 → V1 inversion: today a human pastes the strict polling command into each lane to make it pull every 30 seconds. V1 retires that pattern.

V1 contract:

- **Prime owns dispatch.** Prime decides which lanes are polling, at what cadence, against which queue file, and when to force a poll outside the timer (`bifrost-session-queue-activation-brief.md` §7).
- **Per-session Q state is harness data**, not chat (`bifrost-session-queue-activation-brief.md` §3). Fields: `assigned_queue`, `polling_enabled`, `polling_state`, `last_poll_at`, `last_commit`, `pending_directive`, `steering_mode`.
- **Assignment is explicit and typed.** No inference from card titles. The session harness exposes `assign_queue(session_id, queue_ref)`; the UI calls that operation (`bifrost-session-queue-activation-brief.md` §6).
- **Force-poll fans out from a single button** in the global activation control. Per-backend `steering_mode` determines whether the directive lands as a system update, a directive message, a user-message injection, or a queued resume context. The fan-out reports per-lane acknowledgement.
- **Scott does not have a "poll now" button per lane card.** The lane detail panel offers force-poll for that single lane; the default flow is Prime initiates.
- **Global pause / resume** is a policy switch with audit. Pause preserves per-lane state; resume re-arms the timers. Both produce Progress Surface cards.

What this enables, beyond V0 ergonomics:

- Beacon can mark a lane `stale` and have Prime attempt force-poll → restart → reassign without Scott noticing, surfacing only escalation (`bifrost-cockpit-queue-status-brief.md` §8).
- Codex Reviews lanes can be dispatched by Prime on a different cadence than build lanes.
- New lanes register at session start and pick up assignment from Compass/objective state rather than from a hand-pasted instruction.

V1 explicitly does not:

- Replace the markdown queue files. They remain the durable audit substrate; the harness operates on them (`docs/live-build-queue-hygiene.md` § "structured object").
- Add per-card stop / restart / kill buttons to lane rows. Stop semantics must be heartbeat-confirmed first (`docs/polaris-ui-lessons-for-meridian.md`).

---

## 8A. Prompt / Session Engine Carry-Forward From Polaris

Do not reinvent the prompt/session capability when Bifrost grows the UI around live model sessions.

Polaris already has a working prompt/session engine for the model surfaces Scott actually uses:

- Max / Claude sessions
- Codex sessions
- OpenRouter sessions
- GPT sessions, even though Scott uses these less often

V1 should treat that engine as a proven harness capability to extract, wrap, or adapt. The Bifrost cockpit should provide better orchestration, queue assignment, visibility, and Prime-owned steering around it, not rebuild the prompt dispatch mechanics from scratch inside UI components.

Implementation implications:

- Keep prompt/session mechanics in the Model Harness / Session Harness boundary, not scattered through Bifrost view code.
- Reuse Polaris behavior for prompt submission, resume, transfer, quick replies, model selection, diagnostic logging, and session card output capture wherever it is stable.
- Preserve the existing differences between Max/Claude, Codex, OpenRouter, and GPT adapters instead of flattening them into a generic UI-only abstraction.
- Let Prime decide which adapter/harness receives a directive; let the adapter preserve the provider-specific mechanics.
- If a feature is already reliable in Polaris, the first Meridian version should wrap it and add state/proof/queue discipline around it.

V1 explicitly does not:

- Rewrite the prompt engine simply because the cockpit UI is new.
- Move provider-specific prompt mechanics into Bifrost components.
- Force GPT parity before Scott needs it.

---

## 9. What Should Be Configurable

V1 ships a settings surface (top-nav Settings button) and per-surface inline controls.

User-configurable in V1:

- **Project focus** — switches all per-project state (Orchestrator Queue, Review Console, lane band, Progress Surface, instrumentation cells where applicable).
- **Risk Tier override** — Prime proposes a tier; Scott may pin or override per session (`docs/meridian-pillars.md` Pillars 2 + 6 + 7).
- **Progress Surface** — Pin / Mute / Collapse / Filter / Redirect / Clear / Severity threshold (per-card); Quiet mode / Retention window / Default routing per category (global) (`bifrost-configurable-progress-surface-brief.md` §6).
- **Cockpit layout** — Lane band side (left / right). Progress Surface collapse-to-glyph. Bottom-band cell visibility within a fixed cap.
- **Model selector** — Visible role/model mapping; per-role override. Orchestrator may choose; Scott may pin.
- **Wake mode** — `full wake / fast wake / silent wake` (`bifrost-v0-cockpit-layout-brief.md` §8).
- **Quick replies** — Which contextual buttons appear and in what order.

Persistent across cockpit sessions:

- All Progress Surface routing overrides, mute lists, pins.
- Lane band side and Progress Surface collapse state.
- Wake mode.
- Project focus + last project.

Per-cockpit-session only (does not persist):

- Filter state on lane rows.
- Search query.
- Open drilldown panels.

V1 explicitly does not expose:

- Threshold editors for harness heartbeat windows.
- Capability toggles on harnesses.
- Routing reconfiguration between harnesses (e.g. Relay model preferences beyond the role/model picker).
- Custom Progress Surface categories.

---

## 10. First Five UI Slices

V1 ships in five sequential slices. Each is a meaningful demo. Slices are ordered so that every slice is usable on its own; the cockpit gets more capable each time, but never half-built.

### Slice 1: Prime Panel + Bottom Band + Compass Header

Ship:

- Top nav (rendered, mostly inactive).
- Prime panel with Orchestrator Queue tab only (Review Console tab visible but empty).
- Compass-driven header strip (project, bearing, risk tier, Prime status).
- Bottom instrumentation band (Beacon, Relay, Aegis, Compass, Queue, Risk Tier, build number, clock).
- Wake brief renders into Orchestrator Queue on cockpit open.

Demo criterion: Scott can open the cockpit, see Prime alive, see the bottom band, and read the wake brief without the CLI.

### Slice 2: Lane Side Band + Per-Lane Detail Panel

Ship:

- Lane side band, fed by Beacon heartbeat events for Build 1–5.
- Per-lane row with full canonical status set.
- Lane detail drilldown panel with Active Task, Read Checks, last commit, blocked reason, `steering_mode`.
- Single static lane action stub: `open queue file`.

Demo criterion: Scott can see every lane's state at a glance and drill into any lane without reading raw markdown.

### Slice 3: Progress Surface + Codex Reviews Integration

Ship:

- Progress Surface (right column) with the eight typed categories.
- Per-card inline controls (Pin / Mute / Severity threshold).
- Global Quiet mode toggle.
- Codex Reviews lanes emit `review result` and `repair routed` cards into the Surface.
- Aegis emits `proof summary` cards.

Demo criterion: Scott can read review outcomes and proof results from the cockpit without opening `docs/live-codex-reviews*.md`.

### Slice 4: Review Console With Disposition + Artifact Viewer

Ship:

- Review Console tab populated by typed items from Codex Reviews, Aegis, and Cross Check.
- Disposition actions (`approve / hold / reject / send back to lane / escalate to Aegis`).
- Inline artifact viewer for diffs and proof records.
- Dispositioned items flow to history pane and emit Progress Surface follow-up cards.

Demo criterion: Scott can resolve a real review item end-to-end without leaving the cockpit.

### Slice 5: Prime-Owned Queue Activation + Force-Poll Fan-Out + Harness Button

Ship:

- Global Queue activation control (`ON / OFF / PAUSED / DEGRADED / BLOCKED`).
- Per-session Q state subscriptions over the harness API.
- Force-poll fan-out (single button) with per-lane acknowledgement.
- Harness top-nav button opens the dashboard (cards grouped by domain, observation-only).
- Lane detail panel adds force-poll for that lane.

Demo criterion: Scott no longer hand-paste a polling command into any lane; Prime is dispatching. The Harness button shows every active harness at a glance.

### Out of V1 (held for V2)

- External notifications (email / Slack / SMS / webhooks).
- Audio Go calls (audio-first wake) — V1 can render the visual treatment but defer audio output.
- Per-harness controls in the Harness dashboard.
- Multi-project portfolio view in a single cockpit window.
- Theme switching beyond dark.
- Voice input.

---

## 11. Configuration Defaults At V1 Launch

| Setting | V1 default |
|---|---|
| Wake mode | `full wake` (visual only at V1 launch; audio enabled when the audio stack ships) |
| Lane band side | Right |
| Progress Surface | Visible (not collapsed) |
| Quiet mode | Off |
| Severity threshold (Progress Surface) | `info` and up (everything shown) |
| Retention window | 200 entries / 24 hours, whichever is smaller |
| Default routing per category | As specified in `bifrost-configurable-progress-surface-brief.md` §3 |
| Tab default | Orchestrator Queue |
| Risk Tier | Whatever Prime proposes; no Scott pin |
| Model selector | Roles default to current Relay route; no Scott pin |

Each default should be one click away to change and one click away to restore.

---

## 12. What V1 Should Intentionally Leave Out

Held for V2 unless promoted explicitly:

- **External notifications** (covered §10).
- **Audio Go calls** at launch (the visual treatment is in V1; the audio stack is V2).
- **Per-harness controls** in the Harness dashboard (V1 is observation-only per `bifrost-harness-dashboard-brief.md` §4).
- **Multi-window detachable panels.** One cockpit window only.
- **Per-card drag-and-drop reordering** on the Progress Surface.
- **Per-card threaded replies.** The Progress Surface is a feed, not chat.
- **AI-summarized digests** on the Progress Surface. Burst suppression in V1 is structural, not generative.
- **Cross-project portfolio aggregation.** The cockpit remains scoped to the active project; portfolio view is V2.
- **Custom Progress Surface categories.**
- **Routing reconfiguration between harnesses** beyond the role/model picker.
- **Voice input.**
- **Theme switching** beyond the V1 dark theme.
- **A worker-card grid** anywhere in the cockpit, even as an optional view.

Each of these has a clear later home. V1 ships less so the Prime-centered inversion holds the first time.

---

## 13. Implementation Dependencies Outside Build 5

V1 cannot ship without the following V0 → V1 maturations in other lanes:

- **Beacon heartbeat events** as typed structured payloads (not just CLI lines). Lane band, Harness dashboard, Progress Surface, and instrumentation band all subscribe.
- **Harness Registry** in `meridian_core` carrying name, role one-liner, capability list, maturity, version. The Harness dashboard reads from it; the Progress Surface labels cards from it.
- **Session Harness runtime** with `register / assign_queue / force_poll / pause / resume / transfer` operations. The Lane band and global queue activation control bind to it.
- **Codex Reviews lanes** emit typed `review result` and `repair routed` events on disposition / routing, not just markdown writes.
- **Aegis** emits typed `proof summary` events; the artifact reference points at a stored proof record.
- **Compass** exposes a project / bearing / objective object the cockpit header reads. Switching projects is a single Compass call.

Build 5 should not block on these landing in any specific order; the slices in §10 expose a meaningful cockpit at each step regardless of which integration is fully complete.

---

## 14. Open V1 Questions

- Final layout when the viewport is narrow (< 1280 px). Current lean: collapse the Lane band into a stacked summary above the Progress Surface, never below the Prime panel.
- Where the per-lane force-poll button lives: only in lane detail, or also as a tiny inline icon on the lane row.
- Whether Review Console disposition actions are keyboard-accessible from the Orchestrator Queue (so Scott can resolve items without tab-switching).
- Wake brief audio enablement — opt-in, opt-out, or always-off until the audio stack lands.
- Whether the Progress Surface collapse-to-glyph in the bottom band counts toward instrumentation cell budget.

These should be resolved before slice 5 ships. Slices 1–4 can land with the current leans.

---

## 15. Summary

- V1 turns Meridian from a CLI wake brief into a Prime-centered, browser-rendered cockpit composed from the five Bifrost source briefs.
- Layout: top nav + Prime panel + Lane band + Progress Surface + bottom instrumentation band. No worker-card grid.
- Prime owns Q polling; Scott no longer pastes polling commands into lane CLIs.
- Five UI slices ship in order: Prime panel + band → Lane band + detail → Progress Surface + Codex Reviews → Review Console + artifact viewer → Prime-owned queue activation + Harness button.
- Configuration is rich at the user-facing layer (Progress Surface, layout, model picker, project focus, wake mode) and deliberately quiet at the harness internals layer (no threshold editors, no capability toggles).
- V1 explicitly leaves out external notifications, audio, per-harness controls, multi-window, custom categories, and any worker wall — those are V2.
- V1's success criterion: Scott no longer reads raw `docs/live-build-N.md` content to know what the system is doing.

This brief is product / implementation-oriented and docs-only. It does not authorize runtime code, FileMap edits, or package-API changes.
