# Voice Profiles Implementation Plan

This is a resumable implementation plan for Stager voice profiles. The design source of truth is [../specs/voice_profiles.md](../specs/voice_profiles.md).

Recording-quality cleanup is planned separately in [audio_cleanup_implementation_plan.md](audio_cleanup_implementation_plan.md). Voice-profile rendering may consume cleaned audio, but it does not implement click removal, denoising, de-essing, or cleanup promotion.

## Objectives

- Add optional `plays/<play_id>/voice_profiles.yaml`.
- Preserve canonical segment audio while rendering profile-transformed audio as generated artifacts.
- Support one actor reading multiple roles with different voices.
- Support a different actor later reading the same role through actor-role cast profiles.
- Start with explicit transforms and manual baseline values.
- Add computed pitch transforms from actor baseline to role target.
- Use observed actor-role tempo as a pitch-strategy constraint, not as tempo normalization.
- Use FFmpeg as the first renderer, with portable filters as the baseline.
- Keep performance acceptable with caching before attempting role-batch rendering.
- Keep creative voice effects separate from recording-quality cleanup.

## Phase 1: Spec And Planning

- [x] Create [../specs/voice_profiles.md](../specs/voice_profiles.md).
- [x] Document actor baselines, role targets, and actor-role cast profiles.
- [x] Document explicit and computed transform modes.
- [x] Document tempo-aware pitch strategy selection.
- [x] Document per-segment, role-batch, and full-source rendering tradeoffs.
- [x] Document cache and generated-artifact policy.
- [x] Add this implementation plan.
- [x] Link the docs from [../README.md](../README.md).

## Phase 2: Config Model And Parser

- [ ] Add `src/stager/audio/voice_profile_config.py`.
- [ ] Define dataclasses for:
  - `VoiceProfileConfig`,
  - `ActorVoiceBaseline`,
  - `RoleVoiceTarget`,
  - `CastVoiceProfile`,
  - `RoleTempoPolicy`,
  - `PitchStrategyPolicy`,
  - `ObservedVoiceMetrics`,
  - `VoiceTransform`,
  - `VoicePreset`.
- [ ] Load `plays/<play_id>/voice_profiles.yaml` when present.
- [ ] Treat a missing profile file as an empty config.
- [ ] Validate `version: 1`.
- [ ] Validate actor ids, role ids, cast profile ids, and duplicate `actor@role` bindings.
- [ ] Validate transform parameters with clear diagnostics.
- [ ] Reject unknown transform types.
- [ ] Reject computed profiles missing required baseline or target pitch.
- [ ] Validate `tempo_policy` ranges and thresholds.
- [ ] Validate `pitch_strategy` values.
- [ ] Treat tempo-policy fields as constraints, not required target transforms.
- [ ] Add parser tests using `tmp_path`.

## Phase 3: Transform Resolution

- [ ] Add `src/stager/audio/voice_profile_resolver.py`.
- [ ] Resolve the active profile for a role and actor.
- [ ] Support `mode: none`.
- [ ] Support `mode: explicit`.
- [ ] Support `mode: computed`.
- [ ] Compute pitch shift with `12 * log2(target / baseline)`.
- [ ] Clamp computed pitch shift with `max_pitch_shift_semitones`.
- [ ] Compute the speed factor implied by linked speed/pitch.
- [ ] Use observed actor-role tempo to predict post-transform WPM.
- [ ] Select linked speed/pitch only when role tempo policy allows it.
- [ ] Select preserve-tempo pitch when linked speed/pitch would violate tempo policy.
- [ ] Select preserve-tempo pitch when observed tempo confidence is too low.
- [ ] Record the selected pitch strategy in the resolved profile.
- [ ] Warn when independent pitch is chosen because linked speed/pitch is unsafe and may produce artifacts.
- [ ] Apply computed-profile overrides.
- [ ] Expand `preset` transforms into concrete transform chains.
- [ ] Preserve a stable resolved-profile id for cache keys.
- [ ] Add unit tests for one actor reading multiple roles.
- [ ] Add unit tests for two actors reading the same role.
- [ ] Add unit tests for pitch clamping and overrides.
- [ ] Add unit tests for linked speed/pitch selection when predicted WPM is within policy.
- [ ] Add unit tests for preserve-tempo fallback when predicted WPM is outside policy.
- [ ] Add unit tests for low-confidence tempo preserving performance timing.

## Phase 4: FFmpeg Filter Graph Compiler

- [x] Add FFmpeg capability detection for required and optional filters.
- [x] Check required filters:
  - `aresample`,
  - `asetrate`,
  - `atempo`,
  - `highpass`,
  - `lowpass`,
  - `equalizer`,
  - `acompressor`,
  - `volume`,
  - `alimiter`,
  - `aecho`,
  - `atrim`,
  - `asetpts`,
  - `concat`,
  - `loudnorm`.
- [x] Check optional filters:
  - `firequalizer`,
  - `afir`.
- [ ] Fail render preflight when required filters are missing.
- [x] Warn when optional filters are missing and a fallback exists.
- [ ] Ensure required voice-profile rendering works with a normal LGPL-compatible FFmpeg install.
- [ ] Add `src/stager/audio/ffmpeg_filter_graph.py`.
- [ ] Compile `highpass`.
- [ ] Compile `lowpass`.
- [ ] Compile `eq` bands.
- [ ] Compile `filter_curve` into FFmpeg-compatible equalizer filters.
- [ ] Compile `compressor` to `acompressor`.
- [ ] Compile `gain`.
- [ ] Compile `loudnorm`.
- [x] Reuse the existing Lorick-derived `stager.loudnorm` two-pass normalizer for final loudness normalization.
- [x] Add tests around `stager.loudnorm` parsing, command construction, and unnormalizable audio handling before using it in voice rendering.
- [x] Make loudness targets explicit presets instead of hard-coded podcast/Librivox assumptions.
- [ ] Compile baseline portable `pitch` with `strategy: linked_speed`.
- [ ] Compile baseline portable `pitch` with `strategy: preserve_tempo`.
- [ ] Compile baseline portable `pitch` with `strategy: auto` after resolution has selected a concrete strategy.
- [ ] Compile baseline portable `speed`.
- [ ] Compile initial `reverb` using FFmpeg-native filters.
- [ ] Compile initial `delay` using FFmpeg-native filters.
- [ ] Add compiler tests that assert filter graph strings for representative transforms.
- [ ] Add tests for unsupported transforms and invalid values.

## Phase 5: Render Cache

- [ ] Add `src/stager/audio/voice_render_cache.py`.
- [ ] Choose generated output root:

  ```text
  build/<play_id>/audio/rendered/<render_profile_id>/<ROLE>/<segment_id>.wav
  ```

- [ ] Compute source audio fingerprints.
- [ ] Include resolved transform chain in cache key.
- [ ] Include actor id, role id, segment id, production id, and content hash where available.
- [ ] Include renderer backend and relevant FFmpeg capability flags.
- [ ] Write render manifest JSON for each rendered profile.
- [ ] Skip rendering when cache key and output file match.
- [ ] Invalidate cache when source audio changes.
- [ ] Invalidate cache when transform parameters change.
- [ ] Add unit tests for cache hit/miss behavior without invoking FFmpeg.

## Phase 6: Segment Renderer

- [ ] Add `src/stager/audio/voice_profile_renderer.py`.
- [ ] Render one segment with FFmpeg.
- [ ] Preserve source files unchanged.
- [ ] Write rendered WAV output.
- [ ] Handle effect tails for reverb and delay.
- [ ] Detect missing `ffmpeg` and `ffprobe` with existing external-tool diagnostics.
- [ ] Log rendered and skipped files using `paths.display_path()`.
- [ ] Add tests with a fake FFmpeg runner.
- [ ] Add a small generated-WAV integration test if it does not require nonstandard filters.

## Phase 7: CLI

- [ ] Add `./main voice-render`.
- [ ] Add `./main voice-profiles doctor` or equivalent FFmpeg capability diagnostic.
- [ ] Support `--play/-p`.
- [ ] Support `--role`.
- [ ] Support `--actor` when actor metadata is available.
- [ ] Support `--force` to ignore cache.
- [ ] Support `--dry-run` to print planned renders and cache hits.
- [ ] Print a summary of rendered, skipped, and failed segments.
- [ ] Add CLI tests for missing config, valid config, invalid config, and dry-run output.

## Phase 8: Audioplay Integration

- [ ] Add `--voice-profiles/--no-voice-profiles` to audioplay build commands that consume segment audio.
- [ ] Resolve rendered audio for roles with active profiles.
- [ ] Fall back to canonical segment audio for roles without profiles.
- [ ] Ensure missing rendered audio triggers rendering or a clear diagnostic.
- [ ] Preserve existing behavior when voice profiles are disabled.
- [ ] Add tests that audioplay assembly chooses rendered audio when enabled.

## Phase 9: Playbook Integration

- [ ] Add `--voice-profiles/--no-voice-profiles` to `./main playbook`.
- [ ] Use rendered audio for response assets when enabled.
- [ ] Decide and implement first cue policy:
  - [ ] rendered cues,
  - [ ] canonical cues,
  - [ ] CLI option if both are implemented.
- [ ] Preserve strict required-audio behavior.
- [ ] Add profile/render metadata to Playbook manifests only after updating [../specs/playbook_manifest.md](../specs/playbook_manifest.md).
- [ ] Add Cuemaster validation/normalization updates if manifest metadata changes.
- [ ] Add Playbook builder tests for rendered response audio.
- [ ] Add Playbook builder tests for cue policy.

## Phase 10: Recording Package And Actor Metadata

- [ ] Decide whether Recording Requests need actor ids in the first implementation.
- [ ] If needed, update [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md).
- [ ] Preserve actor id through LineRecorder project state and `role_recordings` exports if added.
- [ ] Keep voice effects out of LineRecorder recording/export behavior.
- [ ] Add Stager import tests for actor metadata if added.
- [ ] Add LineRecorder validation tests if package contracts change.

## Phase 11: Presets

- [ ] Add built-in preset registry.
- [ ] Add producer-defined presets in `voice_profiles.yaml`.
- [ ] Implement `female_bright` from the existing Audacity macro shape.
- [ ] Add `female_bright_subtle`.
- [ ] Add `male_warm`.
- [ ] Add `godlike_hall`.
- [ ] Add `ghostly_small_room`.
- [ ] Add tests that presets expand deterministically.
- [ ] Document initial presets in the spec or a linked preset reference.

## Phase 12: Optional Analysis

- [ ] Add `./main voice-analyze`.
- [ ] Estimate pitch center from a supplied reference WAV or selected role recordings.
- [ ] Estimate observed speech-active duration from selected role recordings.
- [ ] Estimate approximate actor-role speaking rate from represented text and speech-active duration.
- [ ] Require enough speech-active audio, words, and segments before marking tempo confidence usable.
- [ ] Mark sparse-role tempo estimates as low confidence.
- [ ] Feed observed tempo into pitch-strategy resolution without normalizing tempo.
- [ ] Write analysis output as suggestions, not automatic config changes by default.
- [ ] Add `--write-baseline` only after diagnostics are trustworthy.
- [ ] Add tests using generated synthetic audio fixtures.
- [ ] Add tests that tempo analysis affects pitch strategy but does not create a speed-normalization transform.

## Phase 13: Performance Optimization

- [ ] Measure per-segment rendering time on a representative play.
- [ ] Log FFmpeg process count and total rendered duration.
- [ ] Add safe parallel rendering if per-segment rendering is too slow.
- [ ] Design role-batch rendering manifest and split-boundary tracking.
- [ ] Prototype role-batch rendering with silence padding between segments.
- [ ] Compare output correctness and speed against per-segment rendering.
- [ ] Keep per-segment rendering as the correctness fallback.

## Phase 14: Rubber Band Follow-On

Rubber Band integration is explicitly out of scope for the MVP. The MVP must use the portable LGPL-compatible FFmpeg path for pitch shifting.

- [ ] Revisit whether Rubber Band quality is worth the GPL-enabled FFmpeg integration complexity.
- [ ] Keep Rubber Band disabled unless a user explicitly configures a compatible GPL-enabled FFmpeg build.
- [ ] Detect optional `rubberband` support only in a follow-on diagnostic path.
- [ ] Prefer `rubberband` for pitch only when explicitly requested.
- [ ] Fall back to portable pitch filters when `rubberband` is unavailable.
- [ ] Add diagnostics that clearly say `rubberband` is optional and requires a compatible user-installed FFmpeg build.
- [ ] Document GPL-enabled FFmpeg and Rubber Band licensing before enabling the feature.

## Phase 15: Documentation And Verification

- [ ] Update [playbook_usage.md](playbook_usage.md) with voice-profile options.
- [ ] Update [../quince-workflow.md](../quince-workflow.md) with producer workflow guidance.
- [ ] Update [install.md](install.md) with voice-profile FFmpeg install and verification instructions.
- [ ] Add troubleshooting notes for missing MVP FFmpeg filters.
- [ ] Add examples for one actor reading multiple roles.
- [ ] Add examples for two actors reading the same role.
- [ ] Run targeted Stager audio/profile tests.
- [ ] Run Playbook tests.
- [ ] Run audioplay tests.
- [ ] Run Recording Request and LineRecorder tests if contracts changed.
- [ ] Run full Python suite:

  ```sh
  .venv/bin/python run_tests.py
  ```

## Acceptance Criteria

- [ ] Original recording package content is never modified by voice profile rendering.
- [ ] Canonical segment audio remains usable without voice profiles.
- [ ] `voice_profiles.yaml` can express actor baselines, role targets, and actor-role cast profiles.
- [ ] One actor can render different voices for multiple roles.
- [ ] Two actors can render toward the same role target with different transforms.
- [ ] Explicit transform mode works.
- [ ] Computed pitch mode works and clamps large shifts.
- [ ] Computed pitch strategy uses linked speed/pitch only when role tempo policy allows it.
- [ ] Voice analysis can estimate observed speaking rate with confidence and does not normalize tempo.
- [ ] Built-in presets expand to deterministic FFmpeg transform chains.
- [ ] Rendered audio is cached and rebuilt only when relevant inputs change.
- [ ] Playbook/audioplay builds can opt into rendered voice-profile audio.
- [ ] Verification remains based on canonical segment audio unless explicitly requested otherwise.
- [ ] Tests do not require real recordings, network access, or downloaded models.
