# ADR 0002: LineRecorder Audio Capture Policy

## Status

Accepted.

## Context

LineRecorder records actor line audio in the browser and exports WAV files for Stager import. Browser microphone capture can vary by device, browser, operating system, and user settings. The app needs predictable enough output for Stager while avoiding brittle browser-specific resampling or heavy audio processing in the actor-facing tool.

## Decision

LineRecorder defaults to **Clean Recording Mode**.

Clean mode requests browser capture without echo cancellation, noise suppression, or automatic gain control. This preserves the actor's voice most directly and avoids browser processing that can pump, gate, or distort performance audio. Noisy Room Mode remains available when an actor is using a laptop microphone or cannot find a quiet recording space.

LineRecorder preserves the device/browser sample rate instead of resampling in the browser. Export manifests record the actual `sample_rate_hz` and `channels` for each accepted take. Stager is responsible for later production processing, including any resampling needed for Playbook or final audio output.

LineRecorder should continue to export WAV. The browser implementation may use ScriptProcessor during early MVP work, but the target capture path remains Web Audio API plus AudioWorklet once desktop Chrome/Safari behavior is verified.

## Consequences

- Actors get the least processed recording path by default.
- Noisy Room Mode is an explicit tradeoff, not the baseline.
- Stager import can validate, warn, normalize, and resample consistently in one production-side place.
- LineRecorder avoids adding a browser resampling dependency before mobile/browser behavior is known.
- Exported packages may contain 44.1 kHz, 48 kHz, or other browser-provided sample rates, so downstream code must trust manifest metadata rather than assuming one fixed rate.

## Alternatives Considered

- **Default to Noisy Room Mode**: rejected because browser suppression and automatic gain control may harm performance quality in quiet rooms.
- **Resample every recording to 48 kHz in LineRecorder**: rejected for MVP because browser resampling adds complexity, testing burden, and possible dependency/licensing concerns. Stager can handle batch processing more predictably.
- **Use MediaRecorder output directly**: rejected as the primary contract because browser output formats vary and Stager import expects WAV.
