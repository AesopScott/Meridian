# Meridian UI Build Handoff

**Owner lane:** UI / Bifrost interface session

**Objective:** Redesign the Meridian Electron app toward the last approved HUD
interface direction: the dark multi-panel Meridian command grid Scott provided
in chat. This is not a spaceship cockpit build. The Electron app is the Meridian
UI; root `index.html` is the current renderer source inside that app, so edits
to it are app UI work. Generated Bifrost preview HTML is proof output only.

## Hard Correction

Scott's controlling direction is: **"I don't want the cockpit. I want the last image we had worked on as the UI."**

This handoff must not be interpreted as permission to continue the old spaceship-window cockpit direction. The correct UI target is the dark 10-panel `MERIDIAN` HUD/dashboard reference image Scott posted, where multiple rectangular HUD panels surround circular radar/orb elements. Meridian should adapt that look into a real working interface with a large central prompt, project lanes, harness viewers, and voice controls.

## Primary Visual Reference

Use the **last user-approved UI reference from the thread**, not the older `06-meridian-prime-cockpit-single-view.png` spaceship cockpit asset and not the current command-bay preview screenshot.

The correct reference is the dark Meridian HUD interface image with:

- a multi-panel grid of dark cyan HUD panels,
- repeated `MERIDIAN` panel headers in the source image, but Meridian should reduce that repetition,
- circular radar/orb graphics in several panels,
- one large central prompt / Prime interaction surface to be created from that style,
- project/session lanes on the left,
- harness/system viewers around the central surface,
- minimal permanent top navigation.

Important: the repository currently does **not** contain a local copy of this latest UI reference image. The UI session must not silently substitute another asset. Save or request the exact dark 10-panel Meridian HUD grid image into:

```text
C:\Users\scott\Code\Meridian\docs\assets\diagrams\meridian-v2-ui-reference-hud-grid.png
```

Known wrong/insufficient references:

- `C:\Users\scott\AppData\Local\Temp\bifrost-command-bay-preview.png` is only the current preview proof; it is not the target.
- `C:\Users\scott\Pictures\Screenshots\Screenshot 2026-05-31 152532.png` is a generic JARVIS screenshot; it is mood only, not the target.
- `C:\Users\scott\Code\Meridian\docs\assets\diagrams\06-meridian-prime-cockpit-single-view.png` is the older cockpit asset; it is explicitly rejected as the layout target.

Do **not** use this older generated cockpit image as the primary reference:

```text
C:\Users\scott\Code\Meridian\docs\assets\diagrams\06-meridian-prime-cockpit-single-view.png
```

That older image is useful only as background mood for high-production HUD polish; it is not the layout target.

The current browser preview is:

```text
http://127.0.0.1:8765/bifrost/preview.html
```

## Current Steering From Scott

- The prompt window is too small. Make the prompt / Prime interaction surface large enough to be the main working area.
- Remove visual noise. Do not waste top space with repeated labels such as `V1 cockpit`, `tier two`, `Prime Online`, `Prime Meridian Orchestrator`, version numbers, decorative panel numbers, or repeated `Meridian` labels.
- The central Prime HUD should be quiet: show `PRIMED` and the central circle/orb only. The circle should pulse when Prime is speaking/thinking.
- Remove all of this from the central Prime window: Provider Balance, Claude, OpenAI, DeepSeek, Prompt Payload, Queue, Proof, Prime, B1, B2, B3, B4, B5, ABH.
- Keep real controls where useful, but the interface should not become a wall of labels.
- HTML/browser preview is acceptable and preferred for fast iteration. Do not force Electron unless a desktop-only feature requires it.
- Meridian must be fully voice-enabled in design: voice input, voice output, listening/thinking/speaking states, mute controls, and spoken Prime responses.

## Layout Direction From The Correct Reference

### Center

The center is Prime and the prompt.

- A large central prompt / conversation surface.
- A quiet `PRIMED` orb/pulse area.
- The prompt should feel like the primary command channel, not a sidebar widget.
- Use the dark cyan HUD-panel style from the latest grid image, but do not bury the prompt in decorative clutter.

### Left Lane

The left lane should show **project names**, not build session names by default.

Behavior:

- Each project row is a compact HUD control.
- Clicking a project row expands it and everything else in that lane disappears/collapses.
- The expanded project view shows the individual sessions running for that project.
- This must scale to many projects. Do not use 25 always-visible tabs.

### Top Navigation

Remove the heavy top navigation system.

Scott can verbally ask Prime to open panels. The visual UI should rely on HUD surfaces and voice/command invocation, not a permanent top nav taking space.

### Harness Dashboard / Systems

The bottom `Systems` / harness area should become a launcher for harness-specific windows.

Behavior:

- Clicking a harness button opens that harness window.
- The harness window has its own prompt scoped to that harness.
- Example: clicking Aegis opens an Aegis-focused prompt/window; clicking Relay opens a Relay-focused prompt/window.
- Remove `tier 2` and `version 1.0` buttons/noise from that window.

## Required Real Buttons / Controls

Use real, clickable UI controls where they are natural:

- Prime prompt submit / voice send.
- Microphone toggle.
- Speaker / mute toggle.
- Project row expand/collapse.
- Harness window open/close.
- Mission objectives recall.
- Review / approve / modify / redirect / stop controls only where an actual gate/action exists.
- Queue state controls should be minimal and not shown in the central Prime orb.

## Visual Tone

Target feel:

- JARVIS/HUD command interface, matching the latest dark Meridian multi-panel HUD image rather than the older spaceship-window cockpit.
- Dark glass, cyan instrument lines, selective amber/red/green state.
- Spacious central command surface.
- Fewer words, stronger hierarchy.
- Functional controls over decorative labels.

Avoid:

- Generic SaaS dashboard.
- Cards inside cards.
- A label-heavy top bar.
- Repeating `Meridian` and numeric panel labels everywhere.
- Tiny prompt boxes.
- Provider/model telemetry in the Prime orb.
- Treating `06-meridian-prime-cockpit-single-view.png` as the layout source.
- Saying "cockpit" as shorthand for the old visual direction.

## Files To Start With

Likely implementation files:

```text
bifrost/cockpit.py
bifrost/static/cockpit.css
tests/test_bifrost_cockpit.py
tests/test_bifrost_preview.py
docs/bifrost-v2-cockpit-extensions.md
```

Read before editing:

```text
docs/v2-detailed-build-plan.md
docs/bifrost-v2-cockpit-extensions.md
docs/jarvis-ui-source-assessment.md
docs/v1-bifrost-cockpit-implementation-brief.md
docs/FileMap.md
```

## Constraints

- Keep Bifrost browser-first.
- Do not add live model calls.
- Do not route prompt contents into Prime context just to render UI.
- Do not implement broad runtime session control in the UI slice.
- Keep changes scoped to Bifrost UI/rendering and tests unless coordinator assigns a wider task.
- Preserve HTML escaping / safety tests.
- Update tests to verify the intended UI, not stale labels.
- If adding new files, route FileMap follow-up to Build 3.

## Suggested Acceptance Checks

- `python -m pytest tests/test_bifrost_cockpit.py tests/test_bifrost_preview.py -q`
- Open `http://127.0.0.1:8765/bifrost/preview.html`.
- Confirm the prompt is visually dominant.
- Confirm central Prime area only shows `PRIMED` and the pulsing orb/core.
- Confirm no repeated top noise labels or numeric panel labels.
- Confirm project rows can be represented as expandable project controls.
- Confirm harness/system buttons imply scoped harness windows.
- Confirm voice input/output controls are visible in the design.

## Completion Protocol

When complete:

- Commit and push only the UI slice.
- Update Obsidian in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.
- Mark the changed UI slice ready for Codex review.
- Include screenshot or browser verification notes in the completion summary.
