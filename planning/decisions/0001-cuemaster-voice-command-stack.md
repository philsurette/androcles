# Decision: Cuemaster Voice Command Stack

## Status

Accepted for Phase 1 planning.

## Context

Cuemaster should eventually support hands-free commands after the wake word "Quince", but Phase 1 is a browser rehearsal app. Voice commands should not make the core app harder to ship or force speech-recognition dependencies into the browser MVP.

The current app already has a command abstraction for buttons and keyboard shortcuts. A later voice layer can map recognized utterances onto the same commands.

## Decision

Do not implement wake-word or voice-command recognition in Phase 1.

For the first mobile spike, prefer a native Vosk integration behind a Capacitor plugin bridge:

- Use the existing Cuemaster command abstraction as the app boundary.
- Keep recognition local/offline.
- Start with a tiny grammar: "next", "back", "repeat cue", "hear line", "pause", "resume", "bookmark", "slower", "faster", "normal speed", and "start timing".
- Require an Apache-2.0-compatible runtime and model before shipping.
- Prototype with `vosk-model-small-en-us-0.15` or another explicitly Apache-2.0 Vosk model.

Treat `vosk-browser` / Vosk WASM as a browser prototype option, not the preferred mobile implementation. It is Apache-2.0 and useful for feasibility checks, but native mobile bindings are a better fit for microphone integration, lifecycle management, CPU/battery controls, and packaged-model handling.

## Licensing Notes

The Vosk API repository is Apache-2.0 and includes Android and iOS support. Source: https://github.com/alphacep/vosk-api

Vosk model licenses vary by model. The small US English model is listed as Apache 2.0, while some other models are AGPL, LGPL-3.0, or CC-BY-NC-SA and must not be bundled without explicit approval. Source: https://alphacephei.com/vosk/models

`vosk-browser` is Apache-2.0 and compiles Vosk for WebWorker-based browser use. Source: https://github.com/ccoreilly/vosk-browser

## Technical Notes

Small Vosk models are plausible for mobile, but they are not free. The Vosk model list describes small models as roughly 40-50 MB and about 300 MB runtime memory. Continuous wake-word listening may have meaningful CPU and battery cost, so the spike must measure battery, thermal behavior, microphone lifecycle, app-background behavior, and memory pressure on real iPhone and Android devices.

Small Vosk models support dynamic vocabulary reconfiguration, which should allow a constrained command grammar. The spike should verify whether the grammar can be narrow enough to reduce false activations after the wake word.

## Rejected Alternatives

- **Ship voice commands in Phase 1 browser app**: rejected because the rehearsal loop is already useful without it, and speech recognition would add dependency, permissions, UI, and testing risk.
- **Use browser/WASM Vosk as the default mobile path**: rejected as the preferred path because mobile app lifecycle, microphone permissions, and battery controls are better handled natively.
- **Use cloud speech recognition**: rejected for the default command path because Cuemaster is local-first and rehearsal use should work offline.
- **Bundle arbitrary Vosk models**: rejected because model licenses vary and some listed models are incompatible with the project dependency policy.

## Proposed Capacitor Spike

1. Create a thin Capacitor plugin proof of concept for Android first.
2. Bundle one Apache-2.0 small English Vosk model.
3. Feed microphone audio into Vosk locally.
4. Recognize only the constrained command grammar after "Quince".
5. Map recognized commands onto the existing Cuemaster command abstraction.
6. Measure latency, false activations, memory, CPU, battery, and app lifecycle behavior.
7. Repeat on iOS only after Android proves the API shape.
