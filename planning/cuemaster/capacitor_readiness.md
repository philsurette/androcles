# Cuemaster Capacitor Readiness

This note records what can remain unchanged when the browser app is wrapped with Capacitor, and what should become native/mobile adapters.

## Current Adapter Boundaries

- File import starts from browser `File` objects and Playbook zip extraction is isolated under `src/playbook/`.
- Storage is accessed through `CuemasterStorage` and the current implementation is `indexedDbStorage`.
- Audio playback is isolated behind `AudioPlayer` and `AudioQueue`.
- Microphone permission and stream acquisition are isolated in `platform/microphone.ts`; voice activity detection is app-owned.
- Domain logic, manifest validation, rehearsal sequencing, cue selection, timing feedback, bookmarks, and script browsing do not depend on React or Capacitor.

## Capacitor Replacement Points

- Filesystem: keep Playbook import validation and normalization, but replace browser `File` selection/storage with Capacitor file picker/filesystem APIs. Audio assets should move from IndexedDB blobs to filesystem-backed paths if large Playbooks make IndexedDB impractical.
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

- Zip extraction currently runs on the main thread. Move extraction and required-asset checks to a Web Worker before large Playbook testing.
- Browser IndexedDB is adequate for Phase 1, but large audio libraries need a Capacitor filesystem spike before mobile packaging.
- Stage-direction toggling is not yet implemented because normalized role lines do not yet expose enough direction context.
- Real microphone timing still needs a manual test matrix before declaring mobile-ready behavior.

## Recommended Next Spike

Build a narrow Capacitor proof of concept that imports one Playbook, stores audio assets through the mobile filesystem, persists session metadata through the storage interface, and plays one cue plus one response through either the current web audio path or a native audio plugin.
