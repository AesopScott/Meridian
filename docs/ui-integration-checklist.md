# Meridian UI Integration Checklist

**Owner:** Prime / Bifrost coordination
**Status:** Active checklist
**Date:** 2026-06-01

## Purpose

This checklist is the gate for plugging live behavior into the Meridian UI. Use it whenever a button, panel, prompt surface, harness control, model bridge, or session behavior is added or changed.

The goal is simple: every visible UI piece must either work, clearly show that it is not available yet, or stay out of the interface.

Show a compact checklist status roughly every three UI/build prompts while active UI integration work is underway, and immediately when a stop condition is hit.

## Control Inventory

Use this as the working UI checklist. Every visible icon, selector, session control, and harness button gets its own row. Status values:

- `wired`: expected behavior exists and has at least one verification path.
- `partial`: visible and partly interactive, but not fully connected to the intended feature.
- `planned`: visible by design, but should not pretend to be complete.
- `blocked`: do not advance until fixed.

### Session Panels

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SP1 | Prime panel | User types directly to Prime/orchestrator. | partial | Send prompt from left panel; response appears below prompt in left panel. |
| SP2 | User panel | User interacts with what Prime routes to the user. | partial | Send prompt from right panel; response appears below prompt in right panel. |
| SP3 | Prime prompt input | Two-line scrollable prompt input. Enter sends; Shift+Enter newline. | wired | Type three lines; Enter sends and clears. |
| SP4 | User prompt input | Same prompt behavior as Prime panel. | wired | Type three lines; Enter sends and clears. |
| SP5 | Prime response window | Displays Prime/model output below Prime prompt. | partial | Prompt text remains yellow; response text appears below it. |
| SP6 | User response window | Displays routed session/model output below User prompt. | partial | Prompt text remains yellow; response text appears below it. |
| SP7 | Prime text-size slider | Changes text size in both session panels and syncs both sliders. | wired | Drag Prime slider; both panel text sizes change. |
| SP8 | User text-size slider | Changes text size in both session panels and syncs both sliders. | wired | Drag User slider; both panel text sizes change. |
| SP9 | User prompt color | User-entered transcript text is bright yellow anywhere it appears. | wired | Send prompt from either panel; transcript prompt is yellow. |
| SP10 | Path/file highlighting | File paths and filenames in output render bright orange. | wired | Ask model for working directory; path is orange. |
| SP11 | Model/source label | Shows the model/source used for a response when known. | partial | Send prompt; confirm model label appears near/below response. |

### Top Session Buttons

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| TB1 | Prime Confirm icon | Injects `Confirm` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB2 | Prime Continue icon | Injects `Continue` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB3 | Prime No icon | Injects `No` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB4 | Prime Yes icon | Injects `Yes` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB5 | User Yes icon | Injects `Yes` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB6 | User No icon | Injects `No` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB7 | User Continue icon | Injects `Continue` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |
| TB8 | User Confirm icon | Injects `Confirm` into active prompt; does not submit. | wired | Click icon; word appears at cursor. |

### Selectors

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SEL1 | Model selector | Manual model selection. Defaults to Codex. Auto stays disabled until Prime/Relay logic exists. | partial | Served page has Codex selected and Auto disabled. |
| SEL2 | Projects selector | Selects active project context for the Prime panel. | planned | Changing project must not move layout or silently reroute model calls yet. |

### Spark Ring Icons

| ID | Icon / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| SK1 | Spark center image | Visual voice/core of Prime; toggles session panel visibility through nearby core toggle. | partial | Center image remains visible after refresh. |
| SK2 | Toggle session panels | Opens/closes or reveals session panel mode without changing session data. | partial | Click toggle; panels visibility changes predictably. |
| SK3 | Settings | Opens settings surface for UI/model/project options. | planned | Until wired, it must not show fake settings. |
| SK4 | Filter | Filters current visible work/session content. | planned | Until wired, it must not imply active filtering. |
| SK5 | Models | Opens model selector/settings surface. | planned | Until wired, model selection remains in explicit selector. |
| SK6 | Backlog | Opens backlog/task surface. | planned | Until wired, it must not show fake backlog items. |
| SK7 | Skills | Opens skills/tool capability surface. | planned | Until wired, it must not show fake skills. |
| SK8 | Crosscheck | Starts or opens review/cross-check surface. | planned | Until wired, it must not claim review is complete. |
| SK9 | Close | Closes the active overlay/panel, not the whole browser tab. | planned | Click closes only intended UI surface. |
| SK10 | Archive | Archives or opens archive flow for selected item/session. | planned | Until wired, no destructive archive action. |
| SK11 | Reset | Clears session prompts/transcripts and hard reloads UI. | partial | Send text, click Reset, confirm both panels empty after reload. |
| SK12 | Reload | Hard reloads UI without promising to clear session state. | partial | Click Reload; page reloads with cache-bust. |
| SK13 | Routines | Opens routine/automation surface. | planned | Until wired, no fake routine status. |
| SK14 | Balance | Opens balance/provider/routing view. | planned | Until wired, it must not make routing claims. |

### Speech / Voice

| ID | Control / Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| VO1 | Speech mode icon | Enables/disables voice or speech mode once voice layer exists. | planned | Until wired, must not imply live microphone/model speech is active. |

### Harness Dock Buttons

| ID | Harness Button | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| HN1 | Prime | Opens/focuses Prime core session surface. | partial | Click updates session title/focus without fake status text. |
| HN2 | Bifrost | Opens/focuses UI/Bifrost surface. | partial | Click updates session title/focus without fake status text. |
| HN3 | Relay | Opens/focuses model-routing surface. | partial | Click updates session title/focus; does not enable Auto routing yet. |
| HN4 | Beacon | Opens/focuses heartbeat/liveness surface. | partial | Click updates session title/focus without fake heartbeat details. |
| HN5 | Security | Reserved TBD harness identity; replaces generic TBD. | planned | Button label/icon should become Security before wiring actions. |
| HN6 | Aegis | Opens/focuses proof/cross-check surface. | partial | Click updates session title/focus without fake proof status. |
| HN7 | Compass | Opens/focuses mission/project bearing surface. | partial | Click updates session title/focus. |
| HN8 | Vulcan / Session Lifecycle | Opens/focuses session lifecycle controls. | partial | Click updates session title/focus; no live worker control until wired. |
| HN9 | Atlas | Opens/focuses knowledge/context retrieval surface. | planned | Until wired, no fake retrieved context. |
| HN10 | Charon / FileMap | Opens/focuses navigation/FileMap surface. | partial | Click updates session title/focus; future view should read FileMap. |
| HN11 | Arbiter / Codex Reviews | Opens/focuses review queue surface. | partial | Click updates session title/focus; no fake review findings. |
| HN12 | Workflow | Opens/focuses workflow/sub-agent surface. | planned | Until wired, no fake sub-agent state. |
| HN13 | Federation | Opens/focuses federation/network surface. | planned | Until wired, no fake network state. |
| HN14 | Echo | Opens/focuses memory surface. | planned | Until wired, no fake memory recall. |
| HN15 | Ratchet / Tool | Opens/focuses tool execution surface. | planned | Until wired, no fake tool execution. |
| HN16 | Source / Git | Opens/focuses git/source-control surface. | planned | Until wired, no branch movement from UI. |
| HN17 | Vision / Browser | Opens/focuses browser/vision surface. | planned | Until wired, no fake browser state. |
| HN18 | Autonomy / Release | Opens/focuses release/autonomy surface. | planned | Until wired, no public release action. |

### Bridge / Backend Features

| ID | Feature | Intended Behavior | Current Status | Verification |
|---|---|---|---|---|
| BR1 | Meridian model bridge | Receives UI prompts and routes to selected local CLI backend. | wired | `/health` returns ok. |
| BR2 | Codex backend | Sends selected prompts to Codex CLI. | wired | Select Codex; prompt returns Codex CLI response or readable setup error. |
| BR3 | Max backend | Sends selected prompts to Claude CLI when available. | partial | Select Max; prompt returns Claude response or readable setup error. |
| BR4 | CLI setup detection | Detects missing CLI/auth and gives install/login guidance. | wired | `/api/models` and failed calls return setup guidance. |
| BR5 | Recent call diagnostics | Stores metadata only, never prompt text. | wired | `/api/recent-calls` returns request id/channel/backend/status only. |
| BR6 | Prime/Relay Auto routing | Future: Prime chooses model through Relay harness logic. | planned | Auto remains disabled until this contract exists. |

## Integration Rules

| # | Rule | Proof |
|---|------|-------|
| UI1 | Do not add decorative or mock explanatory text unless the user asks for it. | Visual check: no new unrequested labels, descriptions, status prose, or placeholder cards. |
| UI2 | Preserve the approved layout while wiring behavior. | Visual check after refresh: center image remains visible, project selector stays aligned, Prime/User panels do not drift. |
| UI3 | Prompt input is two visible lines by default, scrollable when needed. | Manual: type three lines; prompt area scrolls without resizing the panel. |
| UI4 | Enter submits; Shift+Enter inserts a newline. | Manual: Enter sends and clears prompt; Shift+Enter keeps editing. |
| UI5 | User-entered prompt text renders bright yellow wherever it appears in transcripts. | Manual: send a prompt and confirm transcript prompt color. |
| UI6 | File paths and filenames render bright orange in model output. | Manual: ask for the working directory or a file path and confirm path styling. |
| UI7 | Response window stays below the prompt and owns model output. | Visual/manual: prompt text does not replace response area and response does not appear in prompt input. |
| UI8 | Text size slider controls both Prime and User session text together. | Manual: drag either slider; both sliders move and both transcript areas resize text. |
| UI9 | Prompt macro buttons inject their literal word into the active prompt. | Manual: Yes, No, Continue, Confirm insert text at cursor and do not submit by themselves. |
| UI10 | Reset clears session transcripts and prompts, then hard reloads the UI. | Manual: send text, click Reset, confirm both panels empty after reload. |
| UI11 | Reload hard reloads the UI without promising to clear session state. | Manual: click Reload and confirm page reloads. |

## Model Bridge Rules

| # | Rule | Proof |
|---|------|-------|
| MB1 | Model selector defaults to Codex until Prime/Relay auto-routing exists. | Served page contains `value="codex" selected`; saved `auto` falls back to Codex. |
| MB2 | Auto remains unavailable until Prime/Relay harness logic owns routing. | Served page contains disabled Auto option or equivalent unavailable state. |
| MB3 | Selecting Codex sends through the Meridian bridge, not Polaris. | Request goes to `http://127.0.0.1:8767/api/message`; no Polaris path or process is touched. |
| MB4 | Selecting Max sends through the Meridian bridge when the Claude CLI is available. | `/api/models` reports Max availability before sending; unavailable state gives setup guidance. |
| MB5 | Public setup errors are readable. | Missing CLI or auth failure returns install/login guidance instead of a silent hang. |
| MB6 | Request metadata is tracked without logging prompt text. | `/api/recent-calls` shows request id, channel, backend, model label, duration, and status only. |
| MB7 | Model label appears below or near the response area when known. | Manual: send a request and confirm displayed model/source label. |

## Harness UI Rules

| # | Rule | Proof |
|---|------|-------|
| H1 | Harness buttons do not pretend to be complete before a harness surface exists. | Click behavior is either wired to a real panel or visibly inactive/coming soon by design. |
| H2 | User/session panels follow rules; orchestrator/Prime panels follow logic. | UI copy and behavior keep Prime logic separate from user/session rules. |
| H3 | Security is the reserved icon/identity for the TBD security harness. | Harness map lists Security for the TBD slot before wiring actions. |
| H4 | Prime/Relay model routing remains a future gate until harness logic is defined. | No UI default to Auto and no hidden automatic routing without an explicit Prime/Relay contract. |
| H5 | Any new harness window has a scoped prompt only if that harness can receive scoped commands. | Manual/code review: prompt target is explicit and does not leak into the wrong session channel. |

## Visual Regression Checks

| # | Check | Proof |
|---|-------|-------|
| V1 | Central spark image is present after refresh. | Visual check or served HTML references `spark-center-final.png`. |
| V2 | Prime/User panels remain empty until user/model transcript content exists. | Visual check: no unrequested instructional blocks inside the panels. |
| V3 | Project selector sits above the Prime line and aligns with the line's right edge. | Visual check after refresh at desktop width. |
| V4 | Prime and User prompt/response areas fill their internal panel space with low padding. | Visual check: no large dead margins inside session frames. |
| V5 | Reset and Reload icons remain in the spark ring, not as extra bottom buttons. | Visual check: no duplicate Reset UI button. |

## Verification Commands

Run these before committing UI/bridge changes:

```powershell
$html = Get-Content -Raw index.html
$scripts = [regex]::Matches($html, '<script>([\s\S]*?)</script>') | ForEach-Object { $_.Groups[1].Value }
$tmp = Join-Path $env:TEMP 'meridian-inline-check.js'
[IO.File]::WriteAllText($tmp, ($scripts -join "`n"))
node --check $tmp
node --check scripts\meridian-model-bridge.js
node scripts\meridian-model-bridge.js --self-test
Invoke-RestMethod http://127.0.0.1:8767/health -TimeoutSec 3
Invoke-RestMethod http://127.0.0.1:8767/api/models -TimeoutSec 5
```

For VS Code Live Server checks:

```powershell
$r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5500/index.html -TimeoutSec 5
@(
  'session-prompt-input',
  'session-response-output',
  'value="codex" selected',
  'value="auto" disabled',
  '/api/models',
  'spark-center-final.png'
) | ForEach-Object {
  if ($r.Content.Contains($_)) { "served has: $_" } else { "served missing: $_" }
}
```

## Stop Conditions

Pause and fix before continuing if any of these happen:

| Condition | Action |
|---|---|
| Main branch becomes dirty with worker implementation files | Stop UI work; quarantine/preserve contamination; reset main clean to `origin/main` only after preserving evidence. |
| Any change touches Polaris | Stop; revert the Meridian task path and restart from Meridian-only context. |
| A page refresh serves different UI than the edited `index.html` | Diagnose cache, Live Server root, browser cache, or service worker before editing more UI. |
| Reset does not clear visible session transcripts | Fix reset/session storage behavior before adding new controls. |
| A prompt disappears without a response or setup error | Check bridge health, `/api/models`, browser console, and recent call diagnostics before changing layout. |
| Center image disappears while wiring behavior | Restore visual baseline before continuing behavior work. |
| Model selector defaults to Auto before Prime/Relay routing exists | Revert to Codex default and keep Auto disabled. |
| New button label conflicts with AI/session semantics | Rename or remove it before wiring. Example: do not use Clear for a visual wipe unless it really clears model/session memory. |

## Clearance Record

Append entries here as items are verified.

```text
YYYY-MM-DD HH:MM TZ - <item#> cleared; proof: <short note>; commit: <hash>
```
