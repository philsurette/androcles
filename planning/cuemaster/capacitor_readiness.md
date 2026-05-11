# Cuemaster Capacitor Readiness

This note records what can remain unchanged when the browser app is wrapped with Capacitor, and what should become native/mobile adapters.

## Current Adapter Boundaries

- File import starts from browser `File` objects and Playbook zip extraction is isolated under `src/playbook/`.
- Storage is accessed through `CuemasterStorage` and the current implementation is `indexedDbStorage`.
- Audio playback is isolated behind `AudioPlayer` and `AudioQueue`.
- Microphone permission and stream acquisition are isolated in `platform/microphone.ts`; voice activity detection is app-owned.
- Domain logic, manifest validation, rehearsal sequencing, cue selection, timing feedback, bookmarks, and script browsing do not depend on React or Capacitor.

## Capacitor Replacement Points

- Filesystem: keep Playbook import validation and normalization, but replace browser `File` selection/storage with Capacitor file picker/filesystem APIs. Do not assume audio assets must move out of IndexedDB until this is tested with real Playbooks; the current Androcles Playbook is the baseline fixture at about 322 MB zipped and 383 MB of audio.
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

- Zip extraction currently runs on the main thread. Test import responsiveness with the real Androcles Playbook before deciding whether Web Worker extraction is required.
- Browser IndexedDB is adequate for Phase 1 if the Androcles Playbook imports, persists, reloads, and plays reliably. MP3 Playbook packaging should be the first storage optimization if WAV assets create quota/import pressure; filesystem-backed audio should be a measured response to remaining import time, quota, or playback failures, not a default assumption.
- Stage-direction toggling is not yet implemented because normalized role lines do not yet expose enough direction context.
- Real microphone timing still needs a manual test matrix before declaring mobile-ready behavior.

## Real Playbook Baseline

Use `build/androcles/androcles.playbook.zip` as the first large-file import test. Current local measurements:

- Playbook zip: about 322 MB.
- Extracted Playbook audio: about 383 MB.
- Audio files: 605.
- Manifest: about 748 KB.
- Rehearsable roles: 26.
- Rehearsable lines: 471.

The test should measure import time, whether the UI remains responsive enough during import, whether the browser grants enough storage quota, whether reload/resume works after import, and whether cue/response playback still resolves assets promptly.

The 95% product assumption is one active Playbook per actor at a time. Supporting several stored Playbooks is useful, but the app does not need to optimize for a large local library before the first mobile spike. If storage pressure appears, the acceptable first mitigation is clear user-facing guidance to remove old Playbooks.

## Recommended Next Spike

First run a web import stress test with the real Androcles Playbook. If IndexedDB storage is reliable at that size, the Capacitor proof of concept can start by preserving the storage interface and testing whether mobile WebView IndexedDB quotas are acceptable. If mobile quota or performance fails, then build a narrow Capacitor proof of concept that stores audio assets through the mobile filesystem while keeping session metadata behind the storage interface.
