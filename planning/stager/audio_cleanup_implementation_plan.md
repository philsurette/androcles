# Audio Cleanup Implementation Plan

This is a resumable implementation plan for Stager audio cleanup. The design source of truth is [../specs/audio_cleanup.md](../specs/audio_cleanup.md).

## Objectives

- Add conservative, FFmpeg-native cleanup for actor recordings.
- Keep cleanup separate from creative voice effects.
- Avoid requiring GPL-enabled FFmpeg.
- Render cleaned audio as generated artifacts before promoting it into canonical segment storage.
- Keep configuration minimal.

## Phase 1: Spec And Planning

- [x] Create [../specs/audio_cleanup.md](../specs/audio_cleanup.md).
- [x] Split audio cleanup out of the voice profile plan.
- [x] Document FFmpeg filter, install, and licensing expectations.
- [x] Link the plan from [../README.md](../README.md).

## Phase 2: Capability Detection

- [x] Add shared FFmpeg discovery and filter probing.
- [x] Probe required cleanup filters:
  - `loudnorm`,
  - `atrim`,
  - `asetpts`.
- [x] Probe optional cleanup filters:
  - `adeclick`,
  - `deesser`,
  - `afftdn`,
  - `afwtdn`,
  - `anlmdn`,
  - `agate`.
- [ ] Add cleanup-specific capability report rendering.
- [ ] Ensure missing optional cleanup filters disable only affected presets.

## Phase 3: Config And Presets

- [ ] Add `src/stager/audio/audio_cleanup_config.py`.
- [ ] Load optional `plays/<play_id>/audio_cleanup.yaml`.
- [ ] Provide built-in defaults when no config exists.
- [ ] Add dataclasses for cleanup profile and role override.
- [ ] Validate profile names and role ids.
- [ ] Add built-in presets:
  - `declick_gentle`,
  - `declick_medium`,
  - `deesser_gentle`,
  - `denoise_light`,
  - `voice_cleanup_gentle`.
- [ ] Add parser and preset tests.

## Phase 4: FFmpeg Cleanup Compiler

- [ ] Add `src/stager/audio/audio_cleanup_filter_graph.py`.
- [ ] Compile `declick` to `adeclick`.
- [ ] Compile `deesser` to `deesser`.
- [ ] Compile `denoise_light` to conservative `afftdn`.
- [ ] Support `afwtdn` and `anlmdn` as explicit alternates.
- [ ] Compile optional gating to conservative `agate`.
- [ ] Integrate existing two-pass `stager.loudnorm`.
- [ ] Add tests for filter graph construction.
- [ ] Add tests for missing filter diagnostics.

## Phase 5: Render Cache

- [ ] Add cleanup output root:

  ```text
  build/<play_id>/audio/cleaned/<profile_id>/<ROLE>/<segment_id>.wav
  ```

- [ ] Compute cache keys from source audio fingerprint and resolved cleanup chain.
- [ ] Write cleanup manifest JSON.
- [ ] Skip unchanged renders.
- [ ] Add cache hit/miss tests without invoking FFmpeg.

## Phase 6: Renderer

- [ ] Add `src/stager/audio/audio_cleanup_renderer.py`.
- [ ] Render one segment with FFmpeg.
- [ ] Preserve source files unchanged.
- [ ] Write cleaned WAV output.
- [ ] Run loudnorm as the final step.
- [ ] Validate output exists, is non-silent, and does not clip.
- [ ] Add tests with fake FFmpeg runner.

## Phase 7: CLI

- [ ] Add `./main audio-cleanup`.
- [ ] Add `./main audio-cleanup doctor`.
- [ ] Support `--play/-p`.
- [ ] Support `--role`.
- [ ] Support `--profile`.
- [ ] Support `--force`.
- [ ] Support `--dry-run`.
- [ ] Print rendered/skipped/missing-filter summary.
- [ ] Add CLI tests.

## Phase 8: Review And Promotion

- [ ] Add generated comparison manifest.
- [ ] Add optional report listing source, cleaned output, profile, and duration delta.
- [ ] Decide whether a promote command is needed for canonical segment audio.
- [ ] If added, require explicit confirmation or option before overwriting canonical segment audio.

## Phase 9: Integration

- [ ] Let Playbook generation optionally use cleaned audio.
- [ ] Let audioplay generation optionally use cleaned audio.
- [ ] Keep verification on canonical segment audio unless explicitly requested.
- [ ] Add tests for cleaned-audio selection.

## Phase 10: Documentation And Verification

- [ ] Update [install.md](install.md) with audio cleanup filter notes.
- [ ] Update [../quince-workflow.md](../quince-workflow.md) with cleanup workflow guidance.
- [ ] Add examples for noisy recording cleanup.
- [ ] Add examples for click-heavy recording cleanup.
- [ ] Run targeted Stager audio cleanup tests.
- [ ] Run full Python suite:

  ```sh
  .venv/bin/python run_tests.py
  ```

## Acceptance Criteria

- [ ] Cleanup works with a normal LGPL-compatible FFmpeg installation.
- [ ] Missing optional cleanup filters produce clear warnings.
- [ ] Original LineRecorder package content is never modified.
- [ ] Canonical segment audio is not overwritten by default.
- [ ] Cleaned audio is cacheable and inspectable.
- [ ] Built-in gentle presets work without a config file.
- [ ] Playbook/audioplay can opt into cleaned audio later.

