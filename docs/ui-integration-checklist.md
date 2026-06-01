# Meridian UI Integration Checklist

**Owner:** Prime / Bifrost coordination
**Status:** Active checklist
**Date:** 2026-06-01

## Purpose

This checklist is the gate for plugging live behavior into the Meridian UI. Use it whenever a button, panel, prompt surface, harness control, model bridge, or session behavior is added or changed.

The goal is simple: every visible UI piece must either work, clearly show that it is not available yet, or stay out of the interface.

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
