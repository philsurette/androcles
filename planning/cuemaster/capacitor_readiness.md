# Cuemaster Capacitor Readiness

This note records what can remain unchanged if the browser app is wrapped with Capacitor, and what should become native/mobile adapters.

Cuemaster is now PWA-first. Active install/offline work is tracked in [pwa_implementation_plan.md](pwa_implementation_plan.md). Capacitor work is a fallback tracked in [../mobile_app_implementation_plan.md](../mobile_app_implementation_plan.md) and should resume only if real-device PWA testing exposes a native-only blocker.

## Current Adapter Boundaries

- File import starts from browser `File` objects and Playbook zip extraction is isolated under `src/playbook/`.
- Zip extraction now runs through a Web Worker when available, so the mobile spike should preserve that path unless a native file/storage adapter replaces it deliberately.
- Storage is accessed through `CuemasterStorage` and the current implementation is `indexedDbStorage`.
- Audio playback is isolated behind `AudioPlayer` and `AudioQueue`.
- Microphone permission and stream acquisition are isolated in `platform/microphone.ts`; voice activity detection is app-owned.
- Domain logic, manifest validation, rehearsal sequencing, cue selection, timing feedback, bookmarks, and script browsing do not depend on React or Capacitor.

## Capacitor Replacement Points

- Filesystem: keep Playbook import validation and normalization. First test the existing WebView file input and IndexedDB path on Android; replace browser file selection or storage with Capacitor file picker/filesystem APIs only if real-device testing shows usability, quota, performance, or playback problems.
- Preferences: keep session/bookmark/timing interfaces, but decide whether small records stay in IndexedDB/SQLite or move to Capacitor Preferences. Do not store audio blobs in Preferences.
- Native/background audio: keep `AudioQueue` semantics, but replace `AudioPlayer` with a native audio adapter if background playback, lock-screen controls, or more reliable pause/resume are required.
- Microphone permission: keep `VoiceActivityTracker` and timing feedback, but replace `requestMicrophoneStream()` with a Capacitor/native permission and stream adapter if browser `getUserMedia` is insufficient.
- Hardware controls: add a command layer that maps keyboard, buttons, voice commands, and native media controls to the same rehearsal actions.

## Can Remain Unchanged

- Playbook manifest schema and validation.
- Normalized Playbook domain model.
- Rehearsal engine and cue-depth behavior.
- Timing target and feedback calculations.
- Bookmark and review domain behavior.
- User-facing terminology and guide content, except for platform-specific import/storage wording.

## Known Web Decisions That Need Follow-Up

- Web Worker extraction exists for the browser app; Android should verify it behaves correctly inside the WebView.
- Browser IndexedDB is adequate for the first Android spike if current MP3 Playbooks import, persist, reload, and play reliably. Filesystem-backed audio should be a measured response to import time, quota, or playback failures, not a default assumption.
- Real microphone timing still needs a manual test matrix before declaring mobile-ready behavior.

## Real Playbook Baseline

Use a current MP3 Playbook from a real production as the first Android import test. The older Androcles WAV-heavy Playbook remains a stress baseline if it is still available:

- Playbook zip: about 322 MB.
- Extracted Playbook audio: about 383 MB.
- Audio files: 605.
- Manifest: about 748 KB.
- Rehearsable roles: 26.
- Rehearsable lines: 471.

The test should measure import time, whether the UI remains responsive enough during import, whether the WebView grants enough storage quota, whether reload/resume works after import, and whether cue/response playback still resolves assets promptly.

The 95% product assumption is one active Playbook per actor at a time. Supporting several stored Playbooks is useful, but the app does not need to optimize for a large local library before the first mobile spike. If storage pressure appears, the acceptable first mitigation is clear user-facing guidance to remove old Playbooks.

## Recommended Native Fallback Spike

Start with the PWA-first milestones in [pwa_implementation_plan.md](pwa_implementation_plan.md). If mobile browser storage, import/export, playback, microphone timing, or install/offline behavior fails in a way that blocks real use, record the failed capability and then run the smallest Capacitor spike that addresses that capability. Preserve the storage interface and add native adapters only behind existing boundaries.
