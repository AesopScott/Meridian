# Bifrost Voice-Control Command Palette Contract

**Owner:** Bifrost Harness
**Status:** UI contract only — no runtime code
**Lane owner:** Build 5 (Bifrost / session-harness product lane)
**Audience:** Prime, Bifrost, Beacon, Relay, future cockpit implementers
**Companion briefs:**
- `docs/bifrost-v2-cockpit-extensions.md` — V2 cockpit regions including voice command layer
- `docs/bifrost-v0-cockpit-layout-brief.md` — V0 layout, NASA-style Go sequence, audio-first design
- `docs/jarvis-ui-source-assessment.md` — JARVIS/HUD source direction for Prime presence and voice patterns

This contract defines every voice command Bifrost must recognize in V2, the visible state transitions that accompany each command, and the boundaries that separate voice recognition from Prime decision-making. It is a UI contract: it specifies what the cockpit must do when a voice command is recognized, not how speech recognition, wake-word detection, or audio processing are implemented.

---

## 1. Purpose

Voice control is not a novelty. It is the primary interaction mode for:

- Hands-free operation while Scott is focused elsewhere.
- Rapid navigation that bypasses pointer-and-click overhead.
- Ambient awareness: Prime speaks results; Scott does not always need to look at the screen.
- NASA-style boot/status calls that confirm system health without reading instrumentation.

The voice command palette is the complete set of commands Bifrost must recognize and act on. Every command produces a visible state change in the cockpit and, where applicable, a spoken acknowledgment from Prime.

---

## 2. Voice Command Architecture

### 2.1 Recognition Flow

```
User speaks → Bifrost voice layer → recognized intent + arguments → cockpit state change + Prime acknowledgment
```

Bifrost owns voice recognition and cockpit state. Prime owns decision-making. A voice command that opens a harness panel is a Bifrost action. A voice command that asks Prime to evaluate something is routed to Prime's prompt surface and treated as typed input would be.

### 2.2 Visible Voice State

The cockpit must always show exactly one of these voice states in the Voice I/O indicator:

| State | Meaning | Visual treatment |
|---|---|---|
| `idle` | Voice layer ready, not listening. | Muted mic icon, dim. |
| `listening` | Mic active, waiting for command. | Bright mic icon, pulse animation. |
| `processing` | Command recognized, determining action. | Spinner or thinking indicator. |
| `speaking` | Prime is speaking a response aloud. | Speaker icon, audio-level indicator. |
| `muted` | Voice input and output both suppressed. | Muted mic + speaker icons, persistent. |
| `error` | Voice layer unavailable or failed. | Error icon, reason text on hover. |

The Voice I/O indicator is always visible in the bottom instrumentation band. Clicking it toggles mute. Right-clicking or long-pressing opens voice settings (mic source, output device, wake-word toggle, volume).

### 2.3 Wake Word

The default wake word is `"Prime"`. On hearing the wake word:

- State transitions `idle` → `listening`.
- The Prime presence core pulses once in acknowledgment.
- If dictation mode is active, the wake word is treated as punctuation, not a command — the user must pause briefly after the wake word to trigger command recognition.

The wake word is configurable. Alternatives (`"Meridian"`, `"JARVIS"`) must be selectable. Wake-word detection is local; no audio leaves the machine until after a command is recognized.

### 2.4 Command Timeout

If Bifrost is in `listening` state and no command is recognized within 5 seconds, it returns to `idle`. The transition is silent — no error spoken, no visual interrupt.

---

## 3. Command Palette

Commands are organized by category. Each command includes:

- **Phrase:** What Scott says (primary + accepted alternatives).
- **Action:** What Bifrost does in response.
- **State change:** How the cockpit visibly changes.
- **Prime acknowledgment:** What Prime speaks back, if anything.

### 3.1 Navigation Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 1 | **Open harness panel** | `"Open [HarnessName]"`, `"Show [HarnessName]"`, `"Go to [HarnessName]"` | Opens the named harness panel. Valid names: Bifrost, Beacon, Echo, Atlas, Relay, Aegis, Compass, Codex Reviews, Session Lifecycle, Vault, Forge, Charter, Loom, Groot, Lens, Launch. | Harness panel opens as overlay or routed view per layout policy. Voice state: `processing` → `speaking` → `idle`. | `"[HarnessName] panel open."` |
| 2 | **Close harness panel** | `"Close [HarnessName]"`, `"Hide [HarnessName]"` | Closes the named harness panel if it is open. | Harness panel closes. Voice state: `processing` → `idle`. | None (silent close). |
| 3 | **Return to Prime** | `"Return"`, `"Back to Prime"`, `"Go home"` | Closes any open overlay or panel and returns focus to the Prime command bay. | Cockpit returns to default Prime-centered layout. Voice state: `processing` → `speaking` → `idle`. | `"Prime."` |
| 4 | **Switch project** | `"Switch to [ProjectName]"`, `"Open project [ProjectName]"`, `"Go to [ProjectName]"` | Switches the active project context. If the named project exists, Prime, lane strip, instrumentation, and Compass bearing all update to that project. If the project does not exist, Prime reports the mismatch. | Active project changes. Lane strip re-scopes. Compass bearing updates. Voice state: `processing` → `speaking` → `idle`. | On success: `"Now viewing [ProjectName]."` On failure: `"No project named [ProjectName] found."` |
| 5 | **List projects** | `"List projects"`, `"What projects are active?"`, `"Show projects"` | Prime speaks the list of active and recent projects. The cockpit does not change views; the project rail highlights briefly. | Project rail highlights momentarily. Voice state: `processing` → `speaking` → `idle`. | `"Active projects: [list of project names]. Recent: [list of recent project names]."` |

### 3.2 Focus Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 6 | **Focus prompt** | `"Focus prompt"`, `"Go to prompt"`, `"Talk to Prime"` | Moves keyboard/mic focus to the Prime Orchestrator Queue input. If a harness panel is open with a scoped prompt, focuses that scoped prompt instead. | Input cursor active in the target prompt. Voice state: `processing` → `listening` if dictation mode auto-engages, otherwise `speaking` → `idle`. | `"Ready."` |
| 7 | **Focus Review Console** | `"Open reviews"`, `"Show Review Console"`, `"Review Console"` | Switches the Prime panel to the Review Console tab. | Review Console tab becomes active; badge count visible. Voice state: `processing` → `speaking` → `idle`. | `"Review Console. [N] items."` (speaks count if > 0, otherwise `"Review Console. No items."`) |
| 8 | **Focus lane** | `"Focus lane [N]"`, `"Show Build [N]"`, `"Open lane [N]"` | Opens the lane detail panel for the named build lane. | Lane detail panel opens adjacent to Prime. Lane row highlights. Voice state: `processing` → `speaking` → `idle`. | `"Build [N]. Status: [status]. Task: [active task summary or 'idle']."` |
| 9 | **Focus instrumentation** | `"Show status"`, `"System status"`, `"Beacon report"` | Prime speaks a summary of Beacon health, Relay route, Aegis gate state, and queue activation. No panel opens; this is spoken-only. | Bottom instrumentation band cells highlight briefly as each is reported. Voice state: `processing` → `speaking` → `idle`. | `"Beacon healthy. Relay route active. Aegis clear. Queue on. Tier [N]."` (varies by state — degraded items reported by name). |

### 3.3 Dictation Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 10 | **Start dictation** | `"Start dictation"`, `"Begin dictation"`, `"Listen"` | Begins continuous dictation mode. Everything Scott says is transcribed into the focused prompt input. Dictation remains active until explicitly stopped, a timeout (configurable, default 30s of silence), or a wake-word–preceded command interrupts it. | Voice state: `listening` continuously. Dictation indicator (red dot or similar) appears in the prompt input area. | `"Listening."` |
| 11 | **Stop dictation** | `"Stop dictation"`, `"End dictation"`, `"Stop listening"` | Ends continuous dictation mode. Transcribed text remains in the prompt input; nothing is sent. | Voice state: `processing` → `speaking` → `idle`. Dictation indicator disappears. | `"Dictation stopped."` |
| 12 | **Send dictation** | `"Send"`, `"Submit"`, `"Go ahead"` | Submits the current prompt input content to Prime (or the scoped harness prompt) exactly as if the user pressed Enter. If dictation mode was active, it remains active after sending. | Prompt input submits. Voice state: `processing` → `speaking` → `listening` (if dictation still active) or `idle`. | None (Prime's response follows naturally). |

### 3.4 Prime Output Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 13 | **Read aloud** | `"Read that"`, `"Read it aloud"`, `"Speak"` | Prime speaks the most recent message in the Orchestrator Queue aloud. If the message contains code blocks, tables, or structured data, Prime summarizes and offers to read details on request. | Voice state: `processing` → `speaking` → `idle`. | The most recent Prime message, spoken. |
| 14 | **Read last N** | `"Read the last [N] messages"`, `"Catch me up"`, `"Summarize"` | Prime summarizes the last N messages in the Orchestrator Queue, spoken aloud. | Voice state: `processing` → `speaking` → `idle`. | Summary of last N messages, spoken. |
| 15 | **Stop speaking** | `"Stop"`, `"Quiet"`, `"Silence"`, `"Shut up"` | Immediately interrupts Prime's speech output. Does not affect dictation or listening state. | Voice state: `speaking` → `idle`. Speaking indicator disappears. | None (interrupted). |
| 16 | **Repeat** | `"Repeat"`, `"Say that again"`, `"What?"` | Prime repeats the last spoken output verbatim. If nothing was spoken recently, Prime reports no recent speech. | Voice state: `processing` → `speaking` → `idle`. | Last spoken output repeated, or `"Nothing to repeat."` |

### 3.5 Wake / Boot Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 17 | **Full wake** | `"Wake"`, `"Full wake"`, `"Good morning"`, `"Start up"` | Executes the full NASA-style Go sequence: Bifrost Go → Beacon Go → Echo Go → Atlas Go → Relay Go → Aegis Go → Compass Go. Each check is spoken. Any degraded/failed check is reported aloud and visually. | Each instrumentation cell highlights then fades. Degraded checks hold amber/red. Wake transcript item appears in Review Console (collapsed). Voice state: `processing` → `speaking` throughout → `idle`. | `"Bifrost Go. Beacon Go. Echo Go. Atlas Go. Relay Go. Aegis Go. Compass Go. [N] of [M] nominal."` (degraded items reported by name). |
| 18 | **Fast wake** | `"Fast wake"` | Executes the Go sequence silently — visual only, no spoken calls, no audio. | Same visual treatment as full wake. No audio. Wake transcript item in Review Console (collapsed). Voice state: `processing` → `idle`. | None (silent). |
| 19 | **Status call** | `"Status"`, `"Report"`, `"What's your status?"` | Prime speaks the current system status summary without re-running the Go sequence. Reads last known Beacon/Relay/Aegis/Compass/Queue state. | Instrumentation cells highlight briefly. Voice state: `processing` → `speaking` → `idle`. | Current status summary, spoken. |

### 3.6 Queue / Build Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 20 | **Queue status** | `"Queue status"`, `"What's in the queue?"`, `"Build status"` | Prime speaks the global queue activation state and a per-lane summary (status + attention flags). | Lane strip highlights briefly. Voice state: `processing` → `speaking` → `idle`. | `"Queue is [ON/OFF/PAUSED]. [N] lanes: [running count] running, [idle count] idle, [attention count] need attention."` |
| 21 | **Force poll** | `"Poll now"`, `"Check queues"`, `"Force poll"` | Prime issues a force-poll directive to all active build lanes. | Queue state indicator pulses. Lane rows update as poll results arrive. Voice state: `processing` → `speaking` → `idle`. | `"Polling all lanes."` |
| 22 | **Pause / Resume queue** | `"Pause queues"`, `"Stop queues"` / `"Resume queues"`, `"Start queues"` | Prime toggles global queue activation. This is a gated action: if a human gate is required (tier-3+), Prime asks for confirmation rather than executing immediately. | Queue state indicator changes. Voice state: `processing` → `speaking` → `idle`. | On pause: `"Queues paused."` On resume: `"Queues resumed."` If gated: `"Queue pause requires confirmation. Proceed?"` |

### 3.7 Cockpit Control Commands

| # | Command | Phrase(s) | Action | State change | Prime acknowledgment |
|---|---|---|---|---|---|
| 23 | **Mute / Unmute** | `"Mute"`, `"Be quiet"` / `"Unmute"`, `"Wake up"` | Toggles voice mute — suppresses both mic input and spoken output. Unmute re-enables both. | Voice state: `muted` or returns to `idle`. Voice I/O indicator updates. | None on mute. On unmute: `"Listening."` |
| 24 | **Volume** | `"Volume up"`, `"Louder"` / `"Volume down"`, `"Quieter"` / `"Volume [N]"`, `"Set volume to [N] percent"` | Adjusts speech output volume. Does not affect mic sensitivity. | Volume indicator appears briefly near Voice I/O indicator. Voice state: unchanged. | None (volume change is self-evident via the next spoken output). |
| 25 | **Toggle captions** | `"Captions on"`, `"Show captions"` / `"Captions off"`, `"Hide captions"` | Enables or disables live caption overlay for all Prime speech. Captions appear in a small translucent bar at the bottom of the Prime panel. | Caption bar appears or disappears. Voice state: `processing` → `speaking` → `idle`. | `"Captions [on/off]."` |

---

## 4. Voice + Prompt Interaction Rules

### 4.1 Dictation Mode vs Command Mode

Dictation mode and command mode are mutually exclusive at the recognition level:

- In **dictation mode**, all speech is transcribed to the prompt input. Only a wake-word–preceded command or the stop-dictation command interrupts it.
- In **command mode** (default after wake word but before dictation starts), speech is interpreted as a command from this palette.
- A command that is not recognized produces: voice state `processing` → `speaking` → `idle`, and Prime says `"Command not recognized. Say 'help' for available commands."`

### 4.2 Help Command

`"Help"`, `"What can I say?"`, `"Commands"` — Prime speaks a short categorized summary of available commands. The full palette should be speakable in under 20 seconds. Voice state: `processing` → `speaking` → `idle`.

### 4.3 Scoped Harness Prompts

When a harness panel is open with a scoped prompt, dictation and send-go to that harness's prompt, not the main Orchestrator Queue. The user must say `"Return"` or click back to Prime to resume main-conversation dictation. The scoped prompt is visually distinct (harness label above input).

### 4.4 Prime Is Not a Voice Assistant

Prime is not a general-purpose voice assistant. Voice commands that are not in this palette — e.g., `"What's the weather?"`, `"Play music"`, `"Set a timer"` — are not recognized. Prime may optionally suggest routing such requests elsewhere but must not attempt to fulfill them. The cockpit is a build/command system, not a consumer assistant.

---

## 5. Error and Degraded States

| Condition | Voice state | Visual treatment | Prime acknowledgment |
|---|---|---|---|
| Mic permission denied or unavailable | `error` | Error icon in Voice I/O indicator. Tooltip: `"Microphone unavailable."` | None (silent — if mic is unavailable, Prime cannot hear the command that would trigger acknowledgment). |
| Speech recognition engine failed | `error` | Error icon in Voice I/O indicator. Tooltip: `"Voice recognition unavailable."` | None. |
| Audio output device unavailable | `error` (partial — mic still works) | Speaker icon shows error state. Mic icon shows normal state. Tooltip: `"Audio output unavailable."` | None (spoken output cannot be delivered). Prime routes its response to the Orchestrator Queue as text. |
| Network-dependent recognition unavailable (if cloud-backed) | `error` or `degraded` | Voice I/O indicator shows degraded icon. Tooltip: `"Local-only. Wake word and basic commands available."` | `"Voice recognition is degraded. Basic commands only."` |
| Command recognized but action fails (e.g., opening a harness that is offline) | `speaking` | Panel does not open. Instrumentation cell for that harness shows offline. | `"[HarnessName] is offline."` |
| Wake word detected but no command follows within timeout | `idle` | Mic icon returns to dim. No other change. | None (silent timeout). |

---

## 6. What This Contract Does Not Cover

This contract is a UI specification. It intentionally leaves out:

- **Speech recognition implementation.** STT engine, wake-word detection model, audio pipeline, on-device vs cloud processing — these are implementation decisions, not UI contract.
- **Text-to-speech implementation.** TTS engine, voice model, audio output pipeline — implementation decisions.
- **Wake-word training or customization beyond selection.** The palette allows choosing `"Prime"`, `"Meridian"`, or `"JARVIS"` as the wake word. Custom wake words, voice fingerprints, or multi-user recognition are out of scope.
- **Non-English language support.** V2 voice commands are English only.
- **Voice authentication.** The contract assumes Scott is the sole user. Voice-based user identification is a Federation/V3 concern.
- **Continuous ambient listening beyond wake-word detection.** The cockpit listens only for the wake word when idle. It does not record, analyze, or transmit ambient audio.
- **Prime decision-making about what to say.** What Prime says in response to commands is Prime's responsibility, governed by the Orchestrator Queue and Review Console contracts. This contract specifies only the acknowledgment phrases that confirm a command was recognized and acted on.

---

## 7. Open Questions

- Should `"Prime"` be the default wake word, or should `"Meridian"` lead to avoid confusion with Prime the orchestrator? (Current lean: `"Prime"` as default because it is shorter and works as a proper-name call; `"Meridian"` as alternative because it is unambiguous.)
- Should dictation auto-engage after every wake-word detection, requiring an explicit `"Stop dictation"` to return to command mode? Or should dictation require an explicit `"Start dictation"` command? (Current lean: explicit start; accidental dictation is worse than an extra command.)
- Should the help command be context-sensitive — e.g., `"Help"` when a harness panel is open lists only commands relevant to that harness? (Current lean: yes, but V2 ships with a flat help palette first.)
- Should volume control be a voice command or handled entirely through OS-level audio controls? (Current lean: voice command included because hands-free volume adjustment is a real need.)
- How should the cockpit handle a voice command while Prime is already speaking? (Current lean: interrupt Prime's speech, process the command, respond. The `"Stop"` command is a dedicated interrupt; other commands interrupt implicitly.)

These should be resolved before voice command implementation. Resolving them is design work, not code.

---

## 8. Summary

- Bifrost owns voice recognition and cockpit state; Prime owns decision-making.
- The voice command palette has 25 commands across 7 categories: navigation, focus, dictation, Prime output, wake/boot, queue/build, and cockpit control.
- Visible voice state is always shown in the bottom instrumentation band: `idle`, `listening`, `processing`, `speaking`, `muted`, or `error`.
- Dictation mode transcribes everything to the prompt; command mode (after wake word) interprets speech against this palette.
- Prime is not a general-purpose voice assistant. Unrecognized commands are rejected cleanly.
- Degraded states (no mic, no audio output, network-dependent recognition unavailable) have defined visual and behavioral fallbacks.
- This is a UI contract only. Speech recognition, TTS, and audio pipeline are implementation decisions left to later slices.

This contract is docs-only and strategic. It does not authorize runtime code, FileMap edits, or package-API changes.
