# Bifrost V0 Cockpit Layout Brief

**Status:** Strategic / design-only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Relay, Aegis, Compass, future cockpit implementers
**Companion briefs:**
- `docs/bifrost-session-queue-activation-brief.md` — activation policy + per-session Q mechanism
- `docs/bifrost-cockpit-queue-status-brief.md` — how queue/lane state is shown without recreating the worker wall

This brief defines the **V0 cockpit layout**: where each surface lives on screen, what is dominant, what is supportive, and what V0 deliberately leaves out so the inversion from worker-wall to Prime-centered command center actually holds.

The two prior briefs answered "what state exists" and "what should be visible." This one answers "where it goes on screen, and at what relative weight."

---

## 1. Layout Goal

The V0 cockpit must feel like:

> A command surface where Prime is the relationship, the queue/gates are inspectable instrumentation, and everything else is recessed until it earns attention.

Not:

- A wall of worker cards with a chat box bolted on.
- A dashboard with seventeen widgets and no clear focus.
- A pretty mockup that doesn't change what Scott actually does.

Layout success is measured by where Scott's eyes go first, second, and third when the cockpit is open. V0 should make that order: Prime, then attention items (gates / blocked lanes), then instrumentation. Nothing else by default.

---

## 2. Prime As The Dominant Top/Center Relationship Surface

Prime occupies the visually dominant zone of the cockpit. Top-center, large, primary contrast.

V0 rules:

- The Prime panel is the single tallest and widest content surface on the cockpit.
- It hosts the Orchestrator Queue / Review Console tabbed view (see §3).
- It always shows the latest Prime message and the input control for Scott's response.
- It carries one small header strip with: active project name, project bearing (Compass), active risk tier, and Prime status (online / thinking / waiting on Scott / blocked).
- Nothing in the rest of the cockpit may be visually louder than Prime. Lane attention indicators may be brighter (amber/red), but the Prime panel itself remains the structural focal point.
- No worker card may share Prime's vertical strip. Workers belong below or behind.

Anti-rules:

- Prime is not buried in a tab among many tabs. It is the surface; the tabs live inside it.
- Prime does not become a tail of worker output. Prime's stream is Prime's words, plus the items Prime chooses to route into it.
- The cockpit must not be usable in a configuration where Prime is hidden. Bifrost can collapse panels, but Prime is always present.

---

## 3. Orchestrator Queue + Review Console As Tabbed Prompt Surfaces

The Prime panel contains two prompt surfaces, accessed as tabs in the same dominant zone:

- **Orchestrator Queue** — Scott ↔ Prime conversation. Progress intentions, judgment requests, outcomes, conversational explanations. Default tab on cockpit open.
- **Review Console** — promptable review/gating surface for plans, cross-check, Codex review, Aegis proof, comparisons, artifacts, system findings. Items here have disposition actions (approve / hold / reject / send back).

V0 rules:

- Both tabs render inside the Prime panel; switching tabs does not change layout.
- The Review Console tab carries a badge with the count of unaddressed items. Severity is encoded in badge color, count is the number.
- A `needs human gate` event sets the Review Console badge to its highest-severity state and triggers Prime to drop one short line into the Orchestrator Queue tab (see cockpit-queue-status-brief §9).
- The non-active tab keeps a live indicator: the unread count for Orchestrator Queue if Prime has spoken; the badge for Review Console as above.
- Tab switching is one click or one keystroke. There is no third prompt surface in V0.

Anti-rules:

- The Review Console is not a passive log. Items there are interactive.
- The Orchestrator Queue is not a worker activity feed. Heartbeats stay out.
- A third tab (e.g. "All Events") is not added in V0. It is the failure path back to the worker wall.

---

## 4. Bottom And Side Instrumentation

Instrumentation surfaces flank the Prime panel as compact, scannable bands. They never compete with Prime for visual weight.

V0 instrumentation set:

**Bottom band (always visible, single line where possible):**

- Beacon health — overall + per-harness rollup
- Relay route + active model lanes
- Aegis proof / gate status
- Compass bearing — current project, initiative, objective
- Bifrost — which session set is being inspected, if any
- Queue state — global `ON / OFF / PAUSED / DEGRADED / BLOCKED` indicator (from `bifrost-session-queue-activation-brief.md`)
- Risk tier — current tier and whether dual-lane / Council / Aegis are active
- Meridian build number
- Clock

**Side band (vertical, lane-strip):**

- Per-lane compressed rows (from `bifrost-cockpit-queue-status-brief.md` §3)
- Sorted: attention first, then running, then polling, then idle, offline last
- Filterable by project; default scope is the active project
- Compresses gracefully from 3 to 25 lanes

V0 rules:

- Each instrumentation cell maps to exactly one structured event source. If Beacon does not emit a value, the cell shows `–`, not a guess.
- Clicking any cell opens a drilldown panel for that surface (Beacon detail, Relay route detail, Aegis gate list, Compass objective view, etc.). The drilldown does not replace Prime; it overlays adjacent space.
- Color discipline: cool/neutral for normal, amber for attention, red for critical, restrained violet for thinking/dual-lane. Color is a signal, not a decoration.
- Bottom band has a fixed cell budget. V0 must not grow it beyond what fits on one line at the target window size. Surplus telemetry goes into the drilldown, not the band.

Anti-rules:

- No metric in the bottom band that Scott would not act on. Cost per token, tokens per second, TTFT — those live in lane detail and analytics, never on the instrumentation band.
- The lane side-band is not a card grid. It is a row strip; rows expand only on click.

---

## 5. The Harness Button

Harness is a first-class nav action, not a tab inside Prime.

V0 rules:

- The Harness button lives in the top navigation, alongside Settings, Projects, Reset, Close, Cross Check, Backlog, Skills, Search, Mission Objectives.
- Clicking Harness opens a dedicated view (full-window or large overlay; design decision in §13) showing:
  - every active harness (Bifrost, Beacon, Echo, Atlas, Vault, Forge, Aegis, Charter, Loom, Compass, Relay, Groot, Lens, Launch)
  - each harness's heartbeat, capability set, last event, error count
  - status: alive / busy / blocked / failed / stale / sleeping
  - drilldown into individual harness state
- The Harness view is observation-first. V0 must not introduce harness configuration controls; "see clearly" precedes "change behavior."
- Closing Harness returns Scott to the Prime-centered cockpit. Prime remained loaded in the background.

Anti-rules:

- Harness is not a permanent panel. It is a destination Scott navigates to and leaves.
- Harness is not the worker-session view. Worker session detail comes from the side-band lane drilldown.

---

## 6. Worker / Session Detail Visibility

V0 default: worker session detail is **not visible** in the main cockpit view.

What is visible by default:

- The compressed per-lane row strip in the side band.
- Any lane in `blocked`, `needs review`, `needs human gate`, or `stale` (visible because they earn attention).
- The active project's lane count summary.

What is hidden until requested:

- Lane detail panels.
- Per-lane Codex review entries while clean.
- Per-lane Beacon heartbeat history.
- Per-lane Active Task text.
- Per-lane diagnostic log.

How Scott reaches it:

- Click a lane row → drilldown panel opens in an adjacent region (not on top of Prime).
- The drilldown shows: current Active Task, last commit, last poll, blocked reason if any, backend `steering_mode`, lane diagnostic log, and the per-lane action set (from `bifrost-cockpit-queue-status-brief.md` §6).
- Closing the drilldown returns the cockpit to default state.

Anti-rules:

- No pinned worker card grid as the default view. Pinning a lane keeps its row at the top of the side band, not as a card.
- No "expand all sessions" control. The wall is the failure mode being retired.

---

## 7. Mission Objectives On Demand

The Mission Objectives / Compass control is a top-nav button. It is not a permanent panel.

V0 rules:

- Clicking Mission Objectives opens the current Compass-derived view: portfolio → initiatives → objectives → bottlenecks.
- The view overlays Prime's region or opens as a routed view (design decision; see §13).
- Prime remains live in the background.
- The view shows: active objectives, status, blocked items, next moves, recent decisions, and the link from each objective to its driving harnesses / lanes.
- The view always reflects current Compass state; it is not a static document.

Anti-rules:

- Mission Objectives does not live in the bottom band as a permanent ticker.
- The Compass view is not the cockpit landing surface; Prime is.
- No tab inside Prime is dedicated to objectives in V0. The button + overlay is sufficient.

---

## 8. NASA-Style Go Sequence — Audio-First, Visually Restrained

The wake / boot sequence is part of the cockpit experience but must not crowd the Prime conversation.

V0 rules:

- The preferred channel is **audio**: Bifrost / Beacon Go / Echo Go / Relay Go / Aegis Go / Compass Go spoken on wake.
- Visual treatment: each Go call momentarily highlights the corresponding instrumentation cell (Beacon, Relay, Aegis, Compass, Bifrost). The highlight fades to the cell's normal state.
- A small, optional "wake transcript" appears in the Review Console as a single collapsed item (`Wake sequence completed — 6 of 6 nominal`). Scott can expand to see each call; the transcript is not posted to the Orchestrator Queue.
- If a Go call returns degraded/blocked/offline, the corresponding cell holds amber/red after the highlight fades, and Prime drops one short line into the Orchestrator Queue ("Echo wake reported degraded — see Review Console").
- Wake modes: `full wake` (audio + visual + transcript), `fast wake` (visual only), `silent wake` (visual only, no audio, no transcript item). Default is `full wake`.

Anti-rules:

- The Go sequence is not a teletype scroll across the Prime conversation.
- It does not produce one Orchestrator Queue line per harness on success. Success is silent; only failure speaks.
- It is not a permanent visual element. Once wake completes nominally, the visual treatment is gone.

---

## 9. Scaling From 3 Lanes To 25 Lanes

V0 must look right at 3 lanes and survive at 25.

V0 rules:

- The side-band lane row strip is the primary scaling surface. It grows vertically with a scroll, not horizontally.
- A summary header on the strip shows: `<count> total | <attention> need attention | <blocked> blocked | <stale> stale`. The header stays visible while the rest scrolls.
- At ≥ 8 lanes, the strip gains group-and-filter controls: filter by project, by status, by role; group by project or role.
- At ≥ 15 lanes, lanes not in the active project are collapsed under a portfolio-summary row by default; expand on click.
- The bottom band does not scale per-lane. It scales per-harness and per-system-state, which stays constant.
- Prime does not change shape with lane count. The relationship surface is not a function of how many workers are alive.
- Hidden state must remain summarizable. A "3 lanes hidden, 1 needs attention" summary is always visible if anything is hidden.

Anti-rules:

- No layout reflow that makes Prime smaller as lanes grow.
- No card grid that wraps to a second row at lane count 5 and a third at lane count 9.
- No "give up" mode at high lane counts that drops to a raw event log.

---

## 10. What V0 Should Intentionally Leave Out

V0 ships less to keep the inversion intact. Hold these for V1+ unless promoted explicitly:

- **A worker-session card grid as a default panel.** Even a "pretty" version is the failure path.
- **Permanent per-card colors derived from streamed text.** Wait for Beacon events.
- **Cost / latency / token bottom-band cells.** They live in lane detail and analytics; not on the main band.
- **Color shifters, locks, preview, fork, card reset-size.** Polaris-era ornament; no Meridian use proven.
- **Drag-and-drop lane reassignment or transfer.** Explicit, logged harness actions are V1; UI gestures come after.
- **A combined "All Events" tab or third prompt surface.** Two prompts and an instrumentation band only.
- **Modal popups, toasts, banner alerts for routine findings.** Severity-gated rules in `bifrost-cockpit-queue-status-brief.md` §9 govern this; no modals in V0.
- **In-cockpit harness configuration UI.** Harness V0 is observation-only.
- **Forecasting / "Prime predicts" widgets.** Wait until Prime has earned predictions in lived use.
- **Multi-window / detachable panels.** One cockpit window in V0.
- **Federation / multi-user view.** Single user, single host, single project focus.
- **Theme switching beyond dark.** The dark navy / cyan / amber / restrained violet visual identity is the V0 look. No light mode, no high-contrast variant in V0.
- **Card-name-driven coordination.** Identity is harness session id; names are display.

Each of these has a clear later home (V1 backlog, Harness drilldown, analytics view, etc.). V0's job is to ship the inversion, not the catalog.

---

## 11. V0 Default Layout Sketch

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Settings  Projects  Reset  Close  Cross Check  Backlog  Skills  Harness     │
│  Search  Mission Objectives                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                  ┌─────────┐ │
│  Project: Meridian  ·  Bearing: V0 Cockpit  ·  Tier: 2  ·  Prime: online    │ │
│ ┌─────────────────────────────────────────────────────────┐    │ Lanes    │ │
│ │  [Orchestrator Queue]  [Review Console (3)]             │    │ ──────── │ │
│ │                                                          │    │ B1  run │ │
│ │   Prime: Good morning, Scott. Three items in the         │    │ B2  poll│ │
│ │   Review Console; one needs your judgment.               │    │ B3  blk │ │
│ │                                                          │    │ B4  idle│ │
│ │   [scrollable conversation]                              │    │ B5  run │ │
│ │                                                          │    │         │ │
│ │   ┌──────────────────────────────────────────────────┐   │    │ 5 total │ │
│ │   │ > _                                              │   │    │ 1 attn  │ │
│ │   └──────────────────────────────────────────────────┘   │    └─────────┘ │
│ └─────────────────────────────────────────────────────────┘                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Beacon ✓  Relay route✓  Aegis ✓  Compass ✓  Queue ON  Tier 2  v0.X  11:46   │
└──────────────────────────────────────────────────────────────────────────────┘
```

The sketch is illustrative, not pixel-precise. The structural points it carries:

- Top nav is one row, including Harness and Mission Objectives.
- Prime occupies the dominant zone, with Orchestrator Queue / Review Console as tabs inside.
- The lane strip is a vertical side band, compressed rows, with a summary header.
- The instrumentation band is one line across the bottom, cool and unobtrusive.
- No worker-card grid anywhere on the default surface.

---

## 12. V0 Build Discipline

For each V0 surface, before it ships:

- Name the structured event source. If there is none, the surface waits.
- Name the action set. If clicking the surface does nothing, it does not ship.
- Name the failure mode. What does the surface show when its data source is degraded, missing, or stale?
- Name the scaling story. Does it still work at 25 lanes / 10 harnesses / 5 active gates?

These four answers are the V0 acceptance test per surface. A surface that cannot answer all four is not V0.

---

## 13. Open Layout Questions

- Should the Review Console open as a tab inside Prime (current default), as a side drawer, or as a full alternate main surface?
- Should the lane side band be on the right (current default) or left?
- Should the Harness view be a full-window replacement of the cockpit or a large overlay that keeps the bottom band visible?
- Should Mission Objectives open as an overlay over Prime or as a routed view that replaces Prime?
- Where does active risk tier control live: top nav, Prime header strip (current default), or bottom band?
- What is the V0 behavior when no project is selected? (Likely: portfolio view replaces the cockpit until a project is chosen.)
- Audio Go calls — opt-in or opt-out by default?

These should be resolved before V0 implementation. Resolving them is design work, not code.

---

## 14. Summary

- Prime is the dominant surface. Everything else is recessed until it earns attention.
- Two prompt tabs inside Prime: Orchestrator Queue (default) and Review Console (gates, findings, artifacts).
- One bottom instrumentation band, one side lane strip — never a worker-card grid.
- Harness, Mission Objectives, and Search are nav destinations, not permanent panels.
- The NASA-style Go sequence speaks on failure and stays silent on success.
- The layout looks right at 3 lanes and survives at 25 because Prime's shape does not depend on lane count.
- V0 ships less so the inversion holds; the catalog is V1.

This brief is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
