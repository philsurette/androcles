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
- [x] Add cleanup-specific capability report rendering.
- [x] Ensure missing optional cleanup filters disable only affected presets.

## Phase 3: Config And Presets

- [x] Add `src/stager/audio/audio_cleanup_config.py`.
- [x] Load optional `plays/<play_id>/audio_cleanup.yaml`.
- [x] Provide built-in defaults when no config exists.
- [x] Add dataclasses for cleanup profile and role override.
- [x] Support `cleanup_approach: profile-based`.
- [x] Support `cleanup_approach: analysis-based`.
- [x] Default omitted `cleanup_approach` to `profile-based`.
- [x] Support `batch_padding_seconds`, defaulting to `3.0`.
- [x] Support `boundary_warning_ms`, defaulting to `500`.
- [x] Resolve a play-level `default_profile` for roles without overrides.
- [x] Treat omitted `default_profile` as built-in `gentle_voice_cleanup`.
- [x] Support role-level `profile: none` to disable cleanup.
- [x] Support role-level named profile overrides for exceptional recordings.
- [x] Support role-level `analysis: true` override in profile-based productions.
- [x] Support role-level `analysis: false` override in analysis-based productions.
- [x] Fail clearly when analysis-based cleanup is requested without an accepted analysis report.
- [x] Validate profile names.
- [x] Validate role ids.
- [x] Add built-in presets:
  - `declick_gentle`,
  - `declick_medium`,
  - `deesser_gentle`,
  - `denoise_light`,
  - `voice_cleanup_gentle`.
- [x] Add parser and preset tests.

## Phase 4: FFmpeg Cleanup Compiler

- [x] Add `src/stager/audio/audio_cleanup_filter_graph.py`.
- [x] Compile `declick` to `adeclick`.
- [x] Compile `deesser` to `deesser`.
- [x] Compile `denoise_light` to conservative `afftdn`.
- [x] Support `afwtdn` and `anlmdn` as explicit alternates.
- [x] Compile optional gating to conservative `agate`.
- [x] Integrate existing two-pass `stager.loudnorm`.
- [x] Add tests for filter graph construction.
- [x] Add tests for missing filter diagnostics.

## Phase 5: Cleanup Analysis

- [x] Add `src/stager/audio/audio_cleanup_analyzer.py`.
- [x] Load accepted segment audio for the selected play/role.
- [x] Load LineRecorder floor-noise metadata when present.
- [x] Resolve each recording's floor-noise sample by explicit id.
- [x] Resolve each recording's floor-noise sample by timestamp association.
- [x] Estimate broadband noise floor from floor-noise samples.
- [x] Fall back to leading/trailing quiet-region analysis when floor-noise samples are unavailable.
- [x] Mark fallback noise estimates as lower confidence.
- [x] Estimate suggested denoise strength.
- [x] Estimate click density or impulsive-noise likelihood.
- [x] Estimate sibilance risk and suggested de-essing strength.
- [x] Identify conservative leading/trailing silence trim candidates.
- [x] Detect clipping or near-clipping risk.
- [x] Estimate loudness normalization feasibility and expected gain change.
- [x] Group analysis by role, recording package/session, floor-noise id, and source characteristics.
- [x] Recommend a first-pass cleanup profile per recording.
- [x] Flag per-segment outliers for review.
- [x] Write machine-readable analysis report under `build/<play_id>/audio/cleanup_analysis/report.json`.
- [x] Write human-readable analysis report under `build/<play_id>/audio/cleanup_analysis/report.md`.
- [x] Add tests for floor-noise-backed signal analysis.
- [x] Add tests for fallback analysis without floor-noise samples.
- [x] Add tests that aggressive recommendations require explicit opt-in.

## Phase 6: Render Cache

- [x] Add cleanup output roots:

  ```text
  build/<play_id>/audio/cleaned/<batch_id>/batch_manifest.json
  build/<play_id>/audio/cleaned/<batch_id>/<ROLE>/<segment_id>.wav
  ```

- [x] Compute batch cache keys from grouped source audio fingerprints, floor-noise fingerprint, resolved cleanup chain, loudnorm profile, and boundary settings.
- [x] Include source segment hashes and original sample ranges in cache inputs.
- [x] Write cleanup batch manifest JSON.
- [x] Skip unchanged manifest preparation.
- [x] Add cache hit/miss tests without invoking FFmpeg.

## Phase 7: Anchor-Based Batch Renderer

- [x] Add `src/stager/audio/audio_cleanup_renderer.py`.
- [x] Add `src/stager/audio/audio_cleanup_batch.py`.
- [x] Group segments by role, cleanup profile or analysis recommendation, and floor-noise id.
- [x] Group segments by LineRecorder import transaction/session.
- [x] Group segments by normalized sample rate.
- [x] Normalize source segments to a common sample rate before batch construction.
- [x] Build concatenated batches with configurable generated silence padding, default `3.0` seconds.
- [x] Store original start sample, original end sample, original center sample, source duration, source hash, and guard/padding ranges for each segment.
- [x] Render each batch with FFmpeg.
- [x] Preserve source files unchanged.
- [x] Use associated floor-noise samples for `afftdn` measured-noise workflows when available.
- [x] Forbid global silence removal during batch cleanup.
- [x] Declare each cleanup filter/preset as duration-preserving or not duration-preserving.
- [x] Use batch rendering only for duration-preserving filter chains.
- [x] After cleanup, detect cleaned speech start/end inside each segment's padded window.
- [x] Use original center sample as the boundary detection anchor.
- [x] Write cleaned segment WAV output from detected boundaries.
- [x] Warn when cleaned start/end moves more than `boundary_warning_ms`.
- [x] Warn when cleaned duration changes by more than 20%.
- [x] Warn when detected speech no longer contains the original center anchor.
- [x] Warn when detected range approaches or crosses padding midpoint toward a neighboring segment.
- [x] Treat empty detected ranges as severe review items.
- [x] Store original and cleaned ranges in the batch manifest.
- [x] Fall back to per-segment cleanup when a batch cannot be safely split.
- [x] Run loudnorm as the final step after splitting cleaned batches back into segments.
- [x] Validate output exists, is non-silent, and does not clip.
- [x] Add tests with fake FFmpeg runner.
- [x] Add tests for sample-accurate batch manifest construction.
- [x] Add tests for post-cleanup boundary detection.
- [x] Add tests for suspicious boundary warnings.
- [x] Add tests for per-segment fallback when batch validation fails.

## Phase 8: CLI

- [x] Add `./main audio-cleanup`.
- [x] Add `./main audio-cleanup analyze`.
- [x] Add `./main audio-cleanup doctor`.
- [x] Support `--play/-p`.
- [x] Support `--role`.
- [x] Support `--profile`.
- [x] Support `--use-analysis` to render using analysis recommendations.
- [x] Support `--force`.
- [x] Support `--dry-run`.
- [x] Print analysis report locations.
- [x] Print rendered/skipped summary.
- [x] Print missing-filter summary.
- [x] Add CLI tests.

## Phase 9: Review And Promotion

- [x] Add generated comparison manifest.
- [x] Add generated report listing source, cleaned output, batch, and duration delta.
- [x] Include analysis recommendation ids in comparison output when analysis was used.
- [x] Include batch id and original/cleaned sample ranges in comparison output.
- [x] Include boundary-shift warnings in comparison output.
- [x] Decide whether a promote command is needed for canonical segment audio.
- [x] If added, require explicit confirmation or option before overwriting canonical segment audio.

## Phase 10: Integration

- [x] Let Playbook generation use `--audio-source auto|canonical|cleaned`.
- [x] Let audioplay generation use `--audio-source auto|canonical|cleaned`.
- [x] Keep verification on canonical segment audio unless explicitly requested.
- [x] Add tests for cleaned-audio selection.

## Phase 11: Documentation And Verification

- [x] Update [install.md](install.md) with audio cleanup filter notes.
- [x] Update [../quince-workflow.md](../quince-workflow.md) with cleanup workflow guidance.
- [x] Cross-link [../linerecorder/floor_noise_reduction_plan.md](../linerecorder/floor_noise_reduction_plan.md) from cleanup docs.
- [x] Add examples for noisy recording cleanup.
- [x] Add examples for click-heavy recording cleanup.
- [x] Add examples for floor-noise-backed denoising.
- [x] Run targeted Stager audio cleanup tests.
- [x] Run full Python suite:

  ```sh
  .venv/bin/python run_tests.py
  ```

## Acceptance Criteria

- [x] Cleanup works with a normal LGPL-compatible FFmpeg installation.
- [x] Missing optional cleanup filters produce clear warnings.
- [x] Original LineRecorder package content is never modified.
- [x] Canonical segment audio is not overwritten by default.
- [x] Cleaned audio is cacheable and inspectable.
- [x] Built-in gentle presets work without a config file.
- [x] Analysis can recommend cleanup settings from LineRecorder floor-noise samples.
- [x] Analysis can make lower-confidence recommendations without floor-noise samples.
- [x] Batch rendering is the preferred renderer for duration-preserving cleanup chains.
- [x] Batch manifests preserve original center anchors and original/cleaned ranges.
- [x] Suspicious boundary shifts are warned and reviewable.
- [x] Per-segment rendering remains available as a fallback.
- [x] Playbook/audioplay use reviewed cleaned audio automatically when complete and available.
