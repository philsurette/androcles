# ADR 0003: Browser Microphone Code Sharing

## Status

Accepted.

## Context

Cuemaster and LineRecorder both need browser microphone access, but their product responsibilities differ.

Cuemaster currently uses microphone input for rehearsal timing and future voice-command workflows. It needs permission handling, stream lifecycle control, and low-cost signal analysis.

LineRecorder uses microphone input for actor recording. It needs everything Cuemaster needs plus device selection, clean/noisy capture constraints, take recording, WAV encoding, accepted-take persistence, export metadata, and stronger troubleshooting.

The projects are currently separate sibling apps. Extracting a shared browser package too early would add workspace/package complexity before the browser and mobile capture behavior is known.

## Decision

Do not create a shared browser microphone package yet.

For the LineRecorder MVP, keep microphone platform code in `linerecorder/src/platform/microphone.ts` and recording-specific code under `linerecorder/src/audio/`. Cuemaster keeps its narrower microphone adapter under `cuemaster/src/platform/microphone.ts`.

Copy small improvements between apps when useful, but preserve matching boundaries:

- secure-context and browser API checks,
- permission errors,
- stream request and shutdown,
- input device enumeration,
- capture constraint presets,
- level metering and classification.

Do not share or move LineRecorder-specific recording behavior into Cuemaster:

- WAV capture,
- take lifecycle,
- accepted-take storage,
- recording package export metadata.

Revisit extraction after the AudioWorklet and mobile browser/Capacitor spike. At that point, consider a small shared Quince browser module only if both apps need the same stable code.

## Consequences

- LineRecorder can keep moving without a repo-wide workspace refactor.
- Cuemaster is not forced to carry recording-specific abstractions.
- The code remains easy to copy or extract later because platform boundaries are intentionally narrow.
- Some short-term duplication is accepted until browser/mobile behavior is validated.

## Extraction Trigger

Create a shared browser microphone module only when at least two apps need the same tested implementation for:

- secure-context and media API validation,
- microphone permission errors,
- device enumeration,
- selected-device stream requests,
- clean/noisy constraint presets,
- stream shutdown,
- input-level classification.

The shared module should not include LineRecorder take recording or Cuemaster voice-command domain behavior.
