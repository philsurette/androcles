# LineRecorder Implementation Plan

This plan turns the LineRecorder design into resumable implementation work. It covers both Stager-side package import/export and the browser LineRecorder app.

## Current Fit After Cuemaster And Stager Changes

The plan is still directionally correct. Recent Stager and Cuemaster work makes the following adjustments important before implementation starts:

- Cuemaster now has a real React/Vite/TypeScript app under `cuemaster/`. LineRecorder should follow its local-first layout, testing setup, storage style, and license-audit pattern unless a recording-specific need argues otherwise.
- Cuemaster microphone access is isolated in `cuemaster/src/platform/microphone.ts`, and voice-activity timing is app-owned. LineRecorder should start with its own recording-focused microphone classes, but keep the browser permission/device-selection/metering boundary small enough to move into a shared Quince browser module or copy back into Cuemaster.
- Stager Playbook generation now emits explicit `sections`, supports MP3 Playbook packaging, cue-window presets, cue-start offsets, and strict required audio. None of those invalidate the LineRecorder recording package contract, but recording packs should include section context from the same parsed Play model rather than relying only on ad hoc scene text.
- Playbook generation must remain strict. LineRecorder may export partial `role_recordings`, but Stager import must not make incomplete recordings look Playbook-ready.
- Cuemaster currently uses `jszip` and Dexie-backed IndexedDB. The LineRecorder app should either reuse those choices for consistency or document a deliberate reason for choosing `fflate` or raw IndexedDB.

## Phase 0: Contracts And Fixtures

- [ ] Keep [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md) as the source of truth for recording pack and recording package schemas.
- [ ] Add small Stager test fixtures with one role, multiple segments, inline directions, and simultaneous speech.
- [ ] Define fixture WAV files with deterministic short audio.
- [ ] Add schema-validation tests for `role_recording_pack`.
- [ ] Add schema-validation tests for `role_recordings`.
- [ ] Keep re-record request tests out of MVP unless Cuemaster export work begins.
- [ ] Decide whether LineRecorder lives as a sibling app beside `cuemaster/` or inside a future shared app workspace.
- [ ] Identify copyable shared-browser candidates from Cuemaster before coding: microphone platform access, storage estimates, zip import/export helpers, license audit script, and Playwright/Vitest setup.

## Phase 1: Stager Recording Pack Export

- [ ] Add Stager dataclasses for recording pack manifest records under `src/stager/linerecorder/`.
- [ ] Export role-specific recording packs from parsed `Play` data.
- [ ] Use actor-facing `line_id` for UI display and Stager `segment_id` for audio identity.
- [ ] Emit one recording item per speakable role segment.
- [ ] If one displayed source line contains multiple speakable segments, emit multiple recording items with shared display context.
- [ ] Include cue text, stage directions, part/scene context, and expected `output_path` when available.
- [ ] Include section metadata compatible with Stager's Playbook `sections` model so actors can navigate by act, scene, or synthetic play section.
- [ ] Reuse the same parsed play/segment model patterns as `PlaybookBuilder` for role lines, simultaneous speech, and meta-role exclusion.
- [ ] Add tests for solo and dramatic readings.
- [ ] Add tests for inline directions and simultaneous speech.
- [ ] Add tests for section context and no-part synthetic section behavior.
- [ ] Add a thin Stager CLI command after the service is tested.

## Phase 2: LineRecorder Browser MVP

- [ ] Create React + Vite + TypeScript app structure.
- [ ] Mirror Cuemaster's app organization where it applies: domain code outside React, platform adapters, storage repositories, browser tests, and license audit.
- [ ] Implement local import of `role_recording_pack` zip files.
- [ ] Validate manifest shape and reject unsupported `schema_version`.
- [ ] Store imported projects and accepted takes in IndexedDB, likely through Dexie for consistency with Cuemaster.
- [ ] Show actor-facing line list backed by `segment_id`.
- [ ] Implement microphone setup with explicit device selection, browser permission handling, and input meter.
- [ ] Keep microphone access and metering behind a small platform/domain boundary that can later be shared with Cuemaster timing and voice-command work.
- [ ] Prototype AudioWorklet WAV capture in desktop Chrome and Safari.
- [ ] Capture actual sample rate, channel count, clipping, too-quiet, and no-signal metadata for export and troubleshooting.
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
- [ ] Decide whether shared microphone code should be copied between apps, factored into a shared package, or deferred until the Capacitor spike.
- [ ] Document browser support after AudioWorklet/WAV prototype results.
- [ ] Add user-facing troubleshooting for microphone permission, no signal, clipping, and storage quota.

## Later

- [ ] Import Cuemaster re-record request files.
- [ ] Export replacement-only packages.
- [ ] Mark changed items from updated Stager packs.
- [ ] Add Capacitor wrapper if browser MVP proves useful.
- [ ] Add optional package checksums/signatures.
