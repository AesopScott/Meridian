# Voice I/O Authority Contract

This V2 backend slice owns the typed Voice I/O provider/runtime boundary for
`VOC1` and `VOC3`-`VOC9`. It is intentionally non-UI and non-provider-live.

## Authority Owned

- Fail-closed voice runtime state with explicit provider capabilities.
- Display-safe transcript draft metadata: hash, length, confidence, correction
  count, provider refs, and evidence refs.
- Display-safe command intent normalization through injected local callables.
- Display-safe output job metadata for read-aloud posture, mute, and interrupt.
- Privacy guards for voice refs, transcript input, output text, and serialized
  display payloads.

## Authority Not Owned

- Browser microphone capture, permission prompts, media APIs, or UI gestures.
- SpeechRecognition, MediaRecorder, AudioContext, speechSynthesis, or Electron
  renderer behavior.
- Live STT/TTS provider calls, network calls, SDK calls, account probing, or
  credential handling.
- Relay prompt submission, model dispatch, Prime execution, bridge routes, or
  UI wiring.
- Raw audio storage, raw transcript display, raw prompt display, provider
  response display, worker chat display, or local filesystem path exposure.

## Display-Safe Evidence

Serialized Voice I/O payloads may include only IDs, provider refs, voice refs,
evidence refs, hashes, lengths, confidence, state flags, timestamps, and
explicit `raw_*_included=False` sentinels. They must not include raw audio,
raw transcript text, raw prompts, serialized prompts, provider responses,
worker chat, credentials, tokens, API keys, or local paths.

## Execution Boundary

`meridian_core.voice_io` is pure backend domain logic. Injected callables may
normalize an already-created transcript draft into a typed intent, but they do
not execute the intent. Every command intent serializes with
`execution_authorized=False` until a later reviewed Prime/Relay authority slice
chooses to consume it.
