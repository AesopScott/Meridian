# Meridian UI v1.0

Historical checkpoint for the Meridian UI version 1.0 state.

Current UI authority: the Electron app is the Meridian UI. Root `index.html`
is its renderer source. This checkpoint records an earlier named UI state and
should not be treated as the current app entrypoint unless intentionally
restoring that old visual state.

## Historical Preview

`http://127.0.0.1:8766/bifrost/preview.html?v=meridian-ui-v1.0`

## Historical Restore Only

Do not run this as part of normal Meridian UI work. It overwrites the generated
Bifrost preview artifact with the older v1.0 checkpoint. Current app launch
uses `index.html`.

```powershell
Copy-Item -LiteralPath "C:\Users\scott\Code\Meridian\bifrost\versions\Meridian-UI-v1.0\preview.html" -Destination "C:\Users\scott\Code\Meridian\bifrost\preview.html" -Force
Copy-Item -LiteralPath "C:\Users\scott\Code\Meridian\bifrost\versions\Meridian-UI-v1.0\static" -Destination "C:\Users\scott\Code\Meridian\bifrost" -Recurse -Force
```

Created: 
2026-05-31T23:22:03.3862767-06:00
- Obsidian note: `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\UI Checkpoints\Meridian UI v1.0.md`

