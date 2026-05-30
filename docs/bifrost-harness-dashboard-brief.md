# Bifrost Harness Dashboard Brief

**Status:** Strategic / design-only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Relay, Aegis, Compass, Echo, Atlas, future cockpit/harness implementers
**Companion briefs:**
- `docs/bifrost-session-queue-activation-brief.md` — queue activation policy + per-session Q mechanism
- `docs/bifrost-cockpit-queue-status-brief.md` — what queue/lane state is shown and where it routes
- `docs/bifrost-v0-cockpit-layout-brief.md` — V0 cockpit layout (Harness button identified as top-nav destination)

This brief defines the **Harness dashboard surface** Scott called out as a first-class navigation destination. The V0 cockpit layout brief named the Harness button and reserved its slot in the top nav. This brief specifies what opens when Scott clicks it.

The dashboard's purpose is observability of every harness: their heartbeats, capabilities, maturity, recent events, and the relationship each has to active work. Harness V0 is **observation-first** — see clearly, then later add controls where Scott actually needs them.

---

## 1. Why This Brief Exists

Polaris had no harness dashboard. Capability state was scattered across logs, session output, and ad-hoc UI hints. When something went wrong, Scott had to infer "which subsystem failed?" from streamed text. That worked at one or two harnesses; it will not work at the dozen-plus Meridian is planning (Bifrost, Beacon, Echo, Atlas, Vault, Forge, Aegis, Charter, Loom, Compass, Relay, Groot, Lens, Launch).

The Harness dashboard is the one place that answers, at any moment:

- Which harnesses exist?
- Which are alive, busy, blocked, failed, stale, or sleeping?
- What capabilities does each expose?
- What did each one do most recently?
- How mature is each — domain slice, integrated, needs hardening?
- Where can I drill in further?

Without this surface, the V0 cockpit's other inversions (Prime-centered, Review Console for gates, queue/lane rows in the side band) cannot scale: the moment Scott needs to know "is Relay degraded or is the worker just slow?", he needs a dashboard that does not exist anywhere else.

---

## 2. Where The Harness Button Belongs

The Harness button is a **first-class top-navigation action**, sitting alongside Settings, Projects, Reset, Close, Cross Check, Backlog, Skills, Search, and Mission Objectives (as named in `docs/cockpit-ui-architecture.md` and `docs/bifrost-v0-cockpit-layout-brief.md` §5).

V0 rules:

- The button is always visible in the top nav, never hidden inside a menu.
- It carries a single health glyph reflecting overall harness health (cool / amber / red).
- It carries a small count badge when one or more harnesses are in `blocked`, `failed`, or `stale` state.
- Clicking opens the dashboard as a routed destination (or large overlay; see §13) that keeps the bottom instrumentation band visible.
- Closing returns Scott to the Prime-centered cockpit with Prime still loaded.

Anti-rules:

- Harness is not a tab inside Prime.
- Harness is not a side panel that competes with Prime for screen real estate at the default view.
- Harness does not auto-open on cockpit launch; it is reached deliberately.

---

## 3. What The Dashboard Shows Per Harness

The dashboard renders one **harness card** per known harness. Cards are compact, scannable, and consistent across harnesses — so Scott can compare them at a glance.

### V0 card fields (every harness)

| Field | Meaning | Source of truth |
|---|---|---|
| Harness name | `Relay`, `Bifrost`, `Beacon`, `Aegis`, `Compass`, `Echo`, `Atlas`, `FileMap`, etc. | Harness registry |
| Role one-liner | Plain-prose description from `docs/prime-wake-sequence-build-brief.md` naming context | Harness registry |
| Status | `online / stable / standing_by / busy / blocked / degraded / failed / stale / sleeping / offline / unknown` | Beacon |
| Maturity tag | `planned / domain slice / integrated / needs hardening` | `docs/meridian-capabilities-architecture-map.md` |
| Build number / version | Tracks the harness's own build cadence | Harness registry |
| Last heartbeat | Timestamp + age | Beacon |
| Recent event | Most recent structured event (e.g. "Relay dispatched route at 11:58") | Harness event stream |
| Capability list | Compact chip row of capabilities the harness exposes | Harness registry |
| Active links | Number of currently-active links to other harnesses or sessions (e.g. Relay → 2 lanes) | Harness event stream |
| Attention? | Boolean derived from status; same semantics as cockpit lane rows | Bifrost (computed) |

Cards stay the same shape across harnesses. Specialty data (per-harness detail) belongs in the drilldown panel (§6), not on the card.

### Per-harness V0 specifics

The V0 dashboard ships cards for at least these harnesses; each one's card body is rendered from the table above using its harness-specific values:

- **Relay** — model lanes, active routes, current Prompt Budget tier rollup, recent dispatch.
- **Bifrost** — UI session set bound to this cockpit; whether it is rendering, polling for state, or stale.
- **Beacon** — overall heartbeat aggregator; per-harness rollup; missed-cycle count.
- **Aegis** — open gates, recent proof results, current tier-3+ items.
- **Compass** — current bearing, active objective(s), portfolio status snapshot.
- **Echo** — last memory injection count, ranked/capped status, fail-soft hits.
- **Atlas** — knowledge/RAG status, last retrieval, index freshness.
- **FileMap** — registry coverage rollup, last refresh, drift count.
- **Queue / Review Harness** — the live-build queue lanes (Build 1–5) and the centralized Codex Reviews queue. Recent commits, pending reviews, repair tasks routed.

Other planned harnesses (Vault, Forge, Charter, Loom, Groot, Lens, Launch) appear as cards in `planned` maturity with placeholder cells. They are intentionally visible-but-empty in V0 — their absence is informative.

---

## 4. View-Only In V0 vs. Editable Later

V0 Harness is **observation-only**.

Concretely:

- Every card field is read-only.
- The only V0 click actions are: open drilldown, open recent event detail, follow a link to a related surface (Review Console item, lane row, FileMap entry, etc.).
- No start/stop/restart buttons in V0.
- No configuration controls in V0.
- No threshold editors in V0.

Held for later:

- **Restart / pause / resume** a harness from the card.
- **Edit thresholds** (heartbeat windows, retry counts, budget caps).
- **Toggle capabilities** on or off.
- **Reconfigure routing** between harnesses (e.g. Relay model preferences).
- **Force a heartbeat** or **rerun a recent action**.
- **Pin / hide** harness cards in the dashboard.

These controls land only after the data they would mutate is visible and stable. "See clearly" precedes "change behavior" — this matches Polaris Lesson 1 (visibility before mutation) and the Pillar 12 framing of harnesses as Prime's capabilities, not Scott's chores.

---

## 5. Maturity And Build Numbers

The dashboard names where each harness is on the path from idea to integrated capability. This makes the cockpit honest about what is real vs. what is sketched.

V0 rules:

- Each card carries the harness's **maturity tag**: `planned`, `domain slice`, `integrated`, or `needs hardening`. Same taxonomy as `docs/meridian-capabilities-architecture-map.md`.
- Each card carries a **build number / version**. For runtime harnesses this is a semantic version; for live-queue lanes (currently the closest live analogue) it can be the lane's commit cursor.
- A `planned` harness card shows its placeholder state plainly; the card is not hidden just because the harness is not implemented.
- A `needs hardening` harness card shows the known weakness inline (e.g. "Relay: integrated; needs hardening — prompt budget not enforced on dispatch yet").
- Maturity transitions emit Review Console items (`Aegis moved from domain slice to integrated`) so Scott has a record of when a harness graduated.

Anti-rules:

- Maturity is not painted from prose. It comes from a structured registry the harness owners maintain.
- A harness does not get to mark itself `integrated` without a corresponding Aegis-style proof or registry update.

---

## 6. Health And Liveness Without Becoming The Worker Wall

The Harness dashboard is at risk of recreating the Polaris failure mode at a different scale: instead of a wall of worker cards, a wall of harness cards. V0 must guard against this.

Constraints:

- **Compressed cards, not full panels.** Each card is roughly 1/4 to 1/6 of the dashboard surface — many cards visible at once without scroll.
- **Default sort: attention first.** `blocked`, `failed`, `stale` cards rise to the top. Healthy harnesses settle below.
- **Drilldown on click, not always-on.** Per-harness detail (event history, capability docs, recent errors, recent routes) opens as a side or modal panel; it does not live permanently on the card.
- **No live-streaming text on the card.** The recent-event line is a single short string updated on heartbeat; not a tail.
- **No color soup.** Status color is canonical (cool / amber / red / muted) and shared with the lane-row strip elsewhere in the cockpit.
- **No per-card configuration controls in V0.** Removes the "every card has six buttons" Polaris failure mode at the source.
- **Group by domain.** Optional grouping by harness family (cognition harnesses, infra harnesses, knowledge harnesses, gating harnesses) keeps the dashboard scannable at a dozen harnesses.

The principle, restated for this surface:

> **Harnesses are Prime's capabilities. The dashboard makes them legible. It is not a control room Scott pilots — it is an instrument panel Prime operates and Scott inspects.**

---

## 7. How Prime Uses The Dashboard vs. How Scott Uses It

These are different uses of the same surface.

### Prime's use (continuous)

- Prime queries harness state directly through the harness registry / event substrate — **not** by scraping the Harness dashboard UI.
- The dashboard is a **rendered view** over the same data Prime is acting on. They share a source of truth; they don't share a path of action.
- When Prime takes routine recovery action (restart a degraded harness, retry a failed proof, force a Beacon poll), the action appears on the dashboard as a Beacon-emitted event, not as a UI button-press.
- Prime never has to look at the dashboard. The dashboard exists for Scott and for audit.

### Scott's use (inspection)

- Scott opens Harness when he needs to know "what's going on across the system" beyond what Prime's conversation surfaces.
- Typical Scott questions answered by the dashboard:
  - "Why is Build 3 stalled — Relay slow, Aegis blocked, or the lane itself?"
  - "How mature is Aegis now? Domain slice or integrated?"
  - "Is Echo actually injecting memory or has it gone silent?"
  - "Is Compass current with this project's objectives?"
- Scott's actions in V0 are limited to: inspect, drill in, follow a link, return.
- Mutations Scott wants ("restart Relay") become Review Console items for Prime to act on, not direct controls on the harness card.

The split: **Prime acts; Scott understands; the dashboard makes both possible without conflating them.**

---

## 8. Relationship To Review Console And Orchestrator Queue

The Harness dashboard is the third surface in the cockpit, after the Orchestrator Queue and the Review Console. It must not become a fourth prompt stream.

V0 rules on inter-surface flow:

- **Routine harness events stay on the dashboard.** Heartbeats, recent events, status updates do not enter the Orchestrator Queue or the Review Console.
- **Maturity transitions and capability changes** produce a Review Console item with disposition actions if approval is required (e.g. acknowledging that Aegis moved to `integrated`).
- **Harness failures (status: `failed`, `blocked`)** raise an attention flag on the dashboard card; Prime decides whether to drop a one-line update into the Orchestrator Queue based on severity and whether routine recovery is in progress.
- **A Review Console item that affects a harness** (e.g. an Aegis finding that blocks a tier-3 gate) links from the Review Console entry to the relevant harness card. Same artifact, two entry points.
- **Lane rows in the cockpit side band** are aware of which harness they are dispatched through (Relay → lane); clicking a lane row can offer "open dispatching harness" as a related action.

Anti-rules:

- The dashboard does not host a chat panel.
- The dashboard does not duplicate Review Console items inline.
- A harness in `failed` state does not auto-post a torrent of events into the Orchestrator Queue. Severity-gated rules in `bifrost-cockpit-queue-status-brief.md` §9 apply.

---

## 9. Default Layout Sketch

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Settings  Projects  Reset  Close  Cross Check  Backlog  Skills  [Harness●]  │
│  Search  Mission Objectives                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  Harness Dashboard                                       Group: [Domain ▼]  │
│                                                                              │
│  ┌── Cognition ────────────────────────────────────────────────────────┐    │
│  │ [Relay]                  [Aegis]                [Echo]              │    │
│  │ integrated · stable      domain slice · busy    domain slice · ok   │    │
│  │ v0.7 · 12:02             v0.3 · 12:01           v0.4 · 11:59        │    │
│  │ "dispatched lane 5"      "1 gate open"          "ranked 7, capped"  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌── Knowledge & Memory ─────────────────────────────────────────────────┐   │
│  │ [Atlas]                  [FileMap]                                   │   │
│  │ planned · -              integrated · ok                             │   │
│  │ -                        v0.5 · 11:58                                │   │
│  │ -                        "registry refreshed"                        │   │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌── Coordination / UI ──────────────────────────────────────────────────┐   │
│  │ [Bifrost]                [Beacon]              [Compass]             │   │
│  │ domain slice · ok        integrated · stable   domain slice · ok     │   │
│  │ v0.2 · 12:02             v0.6 · 12:02          v0.3 · 11:55          │   │
│  │ "session set bound"      "all lanes heartbeat" "bearing: V0 layout"  │   │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌── Queue / Review ─────────────────────────────────────────────────────┐   │
│  │ [Live Queue]             [Codex Reviews]                             │   │
│  │ integrated · 5 lanes     integrated · idle                           │   │
│  │ - · 12:02                Round 1 cleared all                         │   │
│  │ "B5 idle, awaiting"      "no findings"                               │   │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌── Planned ────────────────────────────────────────────────────────────┐   │
│  │ [Vault]  [Forge]  [Charter]  [Loom]  [Groot]  [Lens]  [Launch]      │   │
│  │ planned · - · placeholder cards, no heartbeat yet                    │   │
│  └──────────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Beacon ✓  Relay route ✓  Aegis ✓  Compass ✓  Queue ON  Tier 2  v0.X  12:02  │
└──────────────────────────────────────────────────────────────────────────────┘
```

The sketch is illustrative. The structural points it carries:

- The Harness button in the top nav carries a `●` glyph when any harness needs attention.
- The dashboard groups cards by domain by default; a group dropdown lets Scott regroup or flatten.
- Cards are uniform-shape, four-line bodies. Specialty detail is in the drilldown.
- Planned harnesses are visible with placeholder cells, not hidden.
- The bottom instrumentation band stays visible across all cockpit destinations — Harness, Mission Objectives, Prime — so global health is never a click away.

---

## 10. V0 Build Discipline (Per-Harness Card)

Before a harness card ships in the dashboard:

1. **Named structured event source.** Beacon (or harness-specific event stream) must emit the status, heartbeat, and recent event. If not, the card waits.
2. **Named registry entry.** The harness must be present in a typed registry with name, role one-liner, capability list, and maturity.
3. **Named failure mode.** What does the card show when the harness is offline, the registry is stale, or events stop arriving?
4. **Named link target.** Where does the drilldown go? At minimum: a panel that lists recent events and capability docs.

A harness that cannot satisfy all four ships as a `planned` placeholder card — visible, with the cells empty.

---

## 11. What V0 Should Intentionally Leave Out

Held for V1+ unless promoted explicitly:

- **Per-card start/stop/restart controls.** V0 is observation-only.
- **Threshold editors** (heartbeat windows, retry caps, budget ceilings).
- **Capability toggles.**
- **Routing reconfiguration** (e.g. Relay model preferences, Echo ranking weights).
- **Force-heartbeat / rerun-last-action buttons.**
- **Pin / hide controls** on harness cards.
- **Inline live-streaming text** on cards (recent event is one short line, not a tail).
- **Per-harness chat or directive composer.**
- **Multi-window detachable dashboards.**
- **Cross-project harness aggregation.** V0 dashboard shows harnesses for the active project; portfolio rollup is V1.
- **Custom card layouts / user-drawn dashboards.** V0 ships the four-line uniform card.
- **Modal alerts or banners for routine harness events.** Severity-gated routing applies; failures route to Review Console.
- **A direct command interface to a harness.** Mutations go through Prime via Review Console items.

Each item has a clear later home. V0 ships less so the inversion holds.

---

## 12. Cross-Surface Invariants

These hold across the Harness dashboard, the Orchestrator Queue, the Review Console, and the cockpit instrumentation band:

- **Single source of truth per fact.** A harness's status is Beacon's; a maturity tag is the registry's; a Review Console item's severity is the producer's. No surface invents data.
- **Color discipline is shared.** Cool / amber / red / muted mean the same thing on a lane row, an instrumentation cell, a harness card, and a Review Console badge.
- **Identity is registry id.** Card titles are display. Renaming a harness in the registry updates the dashboard automatically.
- **Drilldowns do not replace Prime.** Every dashboard interaction can be exited without losing the Prime conversation.
- **Audit trail.** Maturity transitions, status changes from `online` to `failed`, and per-harness capability changes all produce structured events recorded outside the dashboard so a later review can reconstruct what was visible when.

---

## 13. Open Layout Questions

- Should the Harness dashboard be a **full routed destination** (replaces the cockpit's main region while keeping nav + bottom band visible) or a **large overlay** (Prime stays semi-visible behind)? Current lean: routed destination with bottom band visible.
- Should the dashboard default to **grouped-by-domain** or **flat alphabetical** view? Current lean: grouped-by-domain.
- Should `planned` harnesses appear in their own bottom group (current sketch) or interleaved alphabetically inside their domain group?
- Should the per-card "Active links" field be a number or a tiny inline list of link targets?
- Should the Harness button's count badge include `degraded` as well as `blocked` / `failed` / `stale`?
- Should the dashboard surface a "what changed since you last looked" summary on open, or stay fully present-tense?
- Where does the audit trail of maturity transitions live — in the Review Console, in a dedicated Harness History panel, or both?

These are resolved by design decision, not code. V0 can ship with the current leans and revisit.

---

## 14. Open Source-Of-Truth Questions

- Is there a single **Harness Registry** object (typed file, dataclass, or service) that every harness registers into, or does each harness publish its own registry shard? The dashboard needs a single read path; V0 should converge on one.
- Where do **maturity tags** live authoritatively? `docs/meridian-capabilities-architecture-map.md` carries them today; if the dashboard reads them, that doc becomes a load-bearing input rather than a strategic reference.
- How does **Beacon** distinguish "harness is silent because nothing is happening" from "harness has gone dark"? V0 needs a configured idle-vs-stale threshold per harness, not a global one.
- What is the **build-number cadence** for harnesses that are not yet runtime objects (e.g. the live-queue lane "harness")? A documentary version is acceptable in V0; the field cannot be left blank.

These should be resolved before the dashboard is implemented. Documenting them as open questions is the V0 contribution.

---

## 15. Summary

- The Harness dashboard is a first-class top-nav destination; observation-only in V0.
- Every harness gets a uniform compact card: name, role, status, maturity, version, last heartbeat, recent event, capabilities, links, attention flag.
- Health/liveness comes from Beacon; maturity comes from a registry; nothing is painted from prose.
- Prime queries the underlying data directly; Scott uses the dashboard to understand. Mutations go through Prime via the Review Console, not through the dashboard.
- The dashboard groups by domain, surfaces `planned` harnesses as placeholders, and never becomes a chat surface or a control room.
- V0 leaves out start/stop/restart, threshold editors, capability toggles, and per-card chat; those land only after observability is stable.
- The Polaris worker-card failure mode is the explicit thing to avoid; uniform compact cards + drilldown on demand are the structural defense.

This brief is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
