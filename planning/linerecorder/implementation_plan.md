# LineRecorder Implementation Plan

This plan turns the LineRecorder design into resumable implementation work. It covers both Stager-side package import/export and the browser LineRecorder app.

## Phase 0: Contracts And Fixtures

- [ ] Keep [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md) as the source of truth for recording pack and recording package schemas.
- [ ] Add small Stager test fixtures with one role, multiple segments, inline directions, and simultaneous speech.
- [ ] Define fixture WAV files with deterministic short audio.
- [ ] Add schema-validation tests for `role_recording_pack`.
- [ ] Add schema-validation tests for `role_recordings`.
- [ ] Keep re-record request tests out of MVP unless Cuemaster export work begins.

## Phase 1: Stager Recording Pack Export

- [ ] Add Stager dataclasses for recording pack manifest records under `src/stager/linerecorder/`.
- [ ] Export role-specific recording packs from parsed `Play` data.
- [ ] Use actor-facing `line_id` for UI display and Stager `segment_id` for audio identity.
- [ ] Emit one recording item per speakable role segment.
- [ ] If one displayed source line contains multiple speakable segments, emit multiple recording items with shared display context.
- [ ] Include cue text, stage directions, part/scene context, and expected `output_path` when available.
- [ ] Add tests for solo and dramatic readings.
- [ ] Add tests for inline directions and simultaneous speech.
- [ ] Add a thin Stager CLI command after the service is tested.

## Phase 2: LineRecorder Browser MVP

- [ ] Create React + Vite + TypeScript app structure.
- [ ] Implement local import of `role_recording_pack` zip files.
- [ ] Validate manifest shape and reject unsupported `schema_version`.
- [ ] Store imported projects in IndexedDB.
- [ ] Show actor-facing line list backed by `segment_id`.
- [ ] Implement microphone setup with input meter.
- [ ] Prototype AudioWorklet WAV capture in desktop Chrome and Safari.
- [ ] Verify mobile Safari and Android Chrome constraints before committing to mobile MVP support.
- [ ] Record, stop, play, accept, retry, next, previous, and jump-to-item flows.
- [ ] Persist accepted takes across reloads.

## Phase 3: Export Recording Packages

- [ ] Export accepted WAV files to the paths declared by the recording pack.
- [ ] Write `role_recordings` manifest with `complete` and `missing_segment_ids`.
- [ ] Allow partial export, but mark it incomplete.
- [ ] Export only the current accepted take for each segment by default.
- [ ] Add browser tests for complete and partial exports.
- [ ] Add storage-quota and export-failure recovery tests where practical.

## Phase 4: Stager Recording Package Import

- [ ] Add Stager import service for LineRecorder `role_recordings` packages.
- [ ] Validate play id, role id, segment ids, audio paths, and WAV readability.
- [ ] Report missing, extra, silent, clipped, too-quiet, and suspicious-duration recordings.
- [ ] Copy accepted WAVs into Stager's segment tree only after validation.
- [ ] Permit partial imports explicitly, but keep Playbook generation strict.
- [ ] Add tests that imported segment files can be consumed by Playbook generation.

## Phase 5: Hardening

- [ ] Add a license review checklist for runtime dependencies.
- [ ] Decide whether Clean Recording Mode or Noisy Room Mode is the default.
- [ ] Decide whether LineRecorder preserves device sample rate or resamples before export.
- [ ] Document browser support after AudioWorklet/WAV prototype results.
- [ ] Add user-facing troubleshooting for microphone permission, no signal, clipping, and storage quota.

## Later

- [ ] Import Cuemaster re-record request files.
- [ ] Export replacement-only packages.
- [ ] Mark changed items from updated Stager packs.
- [ ] Add Capacitor wrapper if browser MVP proves useful.
- [ ] Add optional package checksums/signatures.
