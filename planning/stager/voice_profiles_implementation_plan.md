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
- Support MVP actor selection without requiring LineRecorder actor metadata.
- Respect canonical/cleaned source-audio selection before creative voice rendering.
- Use FFmpeg as the first renderer, with portable filters as the baseline.
- Keep performance acceptable with caching before attempting role-batch rendering.
- Keep creative voice effects separate from recording-quality cleanup.

## Phase 1: Spec And Planning

- [x] Create [../specs/voice_profiles.md](../specs/voice_profiles.md).
- [x] Document actor baselines, role targets, and actor-role cast profiles.
- [x] Document explicit and computed transform modes.
- [x] Document tempo-aware pitch strategy selection.
- [x] Document MVP actor selection.
- [x] Document source-audio selection and cache identity.
- [x] Document per-segment, role-batch, and full-source rendering tradeoffs.
- [x] Document cache and generated-artifact policy.
- [x] Add this implementation plan.
- [x] Link the docs from [../README.md](../README.md).

## Phase 2: Config Model And Parser

- [x] Add `src/stager/audio/voice_profile_config.py`.
- [x] Define dataclasses for:
  - `VoiceProfileConfig`,
  - `ActorVoiceBaseline`,
  - `RoleVoiceTarget`,
  - `CastVoiceProfile`,
  - `RoleTempoPolicy`,
  - `PitchStrategyPolicy`,
  - `ObservedVoiceMetrics`,
  - `VoiceTransform`,
  - `VoicePreset`.
- [x] Load `plays/<play_id>/voice_profiles.yaml` when present.
- [x] Treat a missing profile file as an empty config.
- [x] Validate `version: 1`.
- [x] Parse optional manual observed actor-role metrics for tempo-aware pitch strategy selection.
- [x] Parse pitch transforms with `strategy: auto|linked_speed|preserve_tempo`.
- [x] Reject legacy `preserve_tempo` boolean pitch-transform fields.
- [x] Validate actor ids, role ids, cast profile ids, and duplicate `actor@role` bindings.
- [ ] Validate transform parameters with clear diagnostics.
- [x] Reject unknown transform types.
- [x] Reject computed profiles missing required baseline or target pitch.
- [x] Validate `tempo_policy` ranges and thresholds.
- [x] Validate `pitch_strategy` values.
- [x] Treat tempo-policy fields as constraints, not required target transforms.
- [x] Add parser tests using `tmp_path`.

## Phase 3: Transform Resolution

- [x] Add `src/stager/audio/voice_profile_resolver.py`.
- [x] Resolve the active actor from explicit `--actor`, a single matching cast profile, or a play-level actor mapping if added.
- [x] Fail when multiple cast profiles match a role and no actor can be selected.
- [x] Resolve the active profile for a role and actor.
- [x] Support `mode: none`.
- [x] Support `mode: explicit`.
- [x] Support `mode: computed`.
- [x] Compute pitch shift with `12 * log2(target / baseline)`.
- [x] Clamp computed pitch shift with `max_pitch_shift_semitones`.
- [x] Compute the speed factor implied by linked speed/pitch.
- [x] Use observed actor-role tempo to predict post-transform WPM when metrics are present and confident.
- [x] Preserve tempo when observed metrics are absent.
- [x] Select linked speed/pitch only when role tempo policy allows it.
- [x] Select preserve-tempo pitch when linked speed/pitch would violate tempo policy.
- [x] Select preserve-tempo pitch when observed tempo confidence is too low.
- [x] Record the selected pitch strategy in the resolved profile.
- [x] Warn when independent pitch is chosen because linked speed/pitch is unsafe and may produce artifacts.
- [x] Apply computed-profile overrides.
- [x] Expand `preset` transforms into concrete transform chains.
- [x] Preserve a stable resolved-profile id for cache keys.
- [x] Do not require `voice-analyze` output for transform resolution.
- [x] Add unit tests for one actor reading multiple roles.
- [x] Add unit tests for two actors reading the same role.
- [x] Add unit tests for ambiguous actor selection.
- [x] Add unit tests for pitch clamping and overrides.
- [x] Add unit tests for linked speed/pitch selection when predicted WPM is within policy.
- [x] Add unit tests for preserve-tempo fallback when predicted WPM is outside policy.
- [x] Add unit tests for low-confidence tempo preserving performance timing.

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
  - `loudnorm`.
- [x] Check optional filters:
  - `concat`,
  - `firequalizer`,
  - `afir`.
- [x] Fail render preflight when required filters are missing.
- [x] Warn when optional filters are missing and a fallback exists.
- [ ] Ensure required voice-profile rendering works with a normal LGPL-compatible FFmpeg install.
- [x] Add `src/stager/audio/ffmpeg_filter_graph.py`.
- [x] Compile `highpass`.
- [x] Compile `lowpass`.
- [x] Compile `eq` bands.
- [x] Compile `filter_curve` into FFmpeg-compatible equalizer filters.
- [x] Compile `compressor` to `acompressor`.
- [x] Compile `gain`.
- [x] Compile `loudnorm`.
- [x] Reuse the existing Lorick-derived `stager.loudnorm` two-pass normalizer for final loudness normalization.
- [x] Add tests around `stager.loudnorm` parsing, command construction, and unnormalizable audio handling before using it in voice rendering.
- [x] Make loudness targets explicit presets instead of hard-coded podcast/Librivox assumptions.
- [x] Compile baseline portable `pitch` with `strategy: linked_speed`.
- [x] Compile baseline portable `pitch` with `strategy: preserve_tempo`.
- [x] Compile baseline portable `pitch` with `strategy: auto` after resolution has selected a concrete strategy.
- [x] Compile baseline portable `speed`.
- [x] Compile initial `reverb` using FFmpeg-native filters.
- [x] Compile initial `delay` using FFmpeg-native filters.
- [x] Add compiler tests that assert filter graph strings for representative transforms.
- [x] Add tests for unsupported transforms and invalid values.

## Phase 5: Render Cache

- [x] Add `src/stager/audio/voice_render_cache.py`.
- [x] Choose generated output root:

  ```text
  build/<play_id>/audio/rendered/<render_profile_id>/<ROLE>/<segment_id>.wav
  ```

- [x] Compute source audio fingerprints.
- [x] Include selected source audio layer, path, and content hash in cache keys.
- [x] Include cleanup review identity, path, and content hash when cleaned source audio is used.
- [x] Include resolved transform chain in cache key.
- [x] Include actor id, role id, segment id, production id, and content hash where available.
- [x] Include observed metrics used by resolution and the selected pitch strategy.
- [x] Include renderer backend and relevant FFmpeg capability flags.
- [x] Write render manifest JSON for each rendered profile.
- [x] Skip rendering when cache key and output file match.
- [x] Invalidate cache when source audio changes.
- [x] Invalidate cache when transform parameters change.
- [x] Add unit tests for cache hit/miss behavior without invoking FFmpeg.

## Phase 6: Segment Renderer

- [x] Add `src/stager/audio/voice_profile_renderer.py`.
- [x] Render one segment with FFmpeg.
- [x] Preserve source files unchanged.
- [x] Write rendered WAV output.
- [x] Handle effect tails for reverb and delay.
- [x] Detect missing `ffmpeg` and `ffprobe` with existing external-tool diagnostics.
- [x] Log rendered and skipped files using `paths.display_path()`.
- [x] Add tests with a fake FFmpeg runner.
- [ ] Add a small generated-WAV integration test if it does not require nonstandard filters.

## Phase 7: CLI

- [x] Add `./main voice-render`.
- [x] Add `./main voice-profiles doctor` or equivalent FFmpeg capability diagnostic.
- [x] Support `--play/-p`.
- [x] Support `--role`.
- [x] Support `--actor` as the MVP explicit actor selector.
- [x] Support `--audio-source auto|canonical|cleaned`.
- [x] Support `--force` to ignore cache.
- [x] Support `--dry-run` to print planned renders and cache hits.
- [x] Print a summary of rendered, skipped, and failed segments.
- [x] Add CLI tests for missing config, valid config, invalid config, and dry-run output.

## Phase 8: Audioplay Integration

- [ ] Add `--voice-profiles/--no-voice-profiles` to audioplay build commands that consume segment audio.
- [ ] Propagate `--audio-source auto|canonical|cleaned` into voice rendering when profiles are enabled.
- [ ] Resolve rendered audio for roles with active profiles.
- [ ] Fall back to canonical segment audio for roles without profiles.
- [ ] Ensure missing rendered audio triggers rendering or a clear diagnostic.
- [ ] Preserve existing behavior when voice profiles are disabled.
- [ ] Add tests that audioplay assembly chooses rendered audio when enabled.

## Phase 9: Playbook Integration

- [ ] Add `--voice-profiles/--no-voice-profiles` to `./main playbook`.
- [ ] Propagate `--audio-source auto|canonical|cleaned` into voice rendering when profiles are enabled.
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

- [ ] Treat recording-package actor metadata as a follow-on enhancement unless MVP actor selection proves insufficient.
- [ ] Decide whether Recording Requests need actor ids after the explicit `--actor` and single-profile inference workflow is exercised.
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
- [ ] Write observed metrics that pitch-strategy resolution can consume.
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
- [ ] Missing or low-confidence observed tempo preserves recorded timing.
- [ ] Actor selection is explicit or unambiguous, and ambiguity fails before rendering.
- [ ] Render cache keys distinguish canonical source audio from reviewed cleaned source audio.
- [ ] Voice analysis can estimate observed speaking rate with confidence and does not normalize tempo.
- [ ] Built-in presets expand to deterministic FFmpeg transform chains.
- [ ] Rendered audio is cached and rebuilt only when relevant inputs change.
- [ ] Playbook/audioplay builds can opt into rendered voice-profile audio.
- [ ] Verification remains based on canonical segment audio unless explicitly requested otherwise.
- [ ] Tests do not require real recordings, network access, or downloaded models.
