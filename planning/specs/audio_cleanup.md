# Audio Cleanup

This document defines Quince audio cleanup for actor recordings: noise reduction, click reduction, de-essing, light gating, trimming, and loudness normalization. Cleanup is a recording-quality pipeline, not a creative voice-character pipeline.

Implementation sequencing belongs in [../stager/audio_cleanup_implementation_plan.md](../stager/audio_cleanup_implementation_plan.md).

## Goals

- Improve noisy or clicky actor recordings without changing the intended character voice.
- Keep original LineRecorder exports and canonical segment audio recoverable.
- Start with conservative FFmpeg-native filters that work with a normal LGPL-compatible FFmpeg install.
- Make cleanup easy to use with minimal configuration.
- Allow A/B review because cleanup can damage speech when pushed too hard.

## Non-Goals

- Gender-presentation shifting, role effects, godlike reverb, or other creative voice profiles.
- ML voice conversion or voice cloning.
- Requiring GPL-enabled FFmpeg.
- Requiring external denoising model files.
- Perfect mouth-noise removal comparable to dedicated audio restoration tools.

## Audio Layers

Cleanup should preserve three layers:

1. **Original imported package content**
   - Raw files exported by LineRecorder.
   - Preserved in import transactions for undo/reprocessing.

2. **Canonical segment audio**
   - Current accepted segment WAVs used by verification and normal builds.
   - May be cleaned only by an explicit import/build option.

3. **Cleaned rendered audio**
   - Generated artifacts that can be inspected, deleted, and rebuilt.
   - Preferred MVP output for cleanup until we are confident enough to write cleaned audio into canonical segment storage.

## MVP Configuration

Audio cleanup should need less configuration than voice effects. The first config can be play-level defaults plus optional role overrides:

```yaml
version: 1

cleanup_approach: profile-based
default_profile: gentle_voice_cleanup
batch_padding_seconds: 3.0
boundary_warning_ms: 500

profiles:
  gentle_voice_cleanup:
    declick: gentle
    deesser: gentle
    denoise: light
    loudnorm: librivox
  mouth_click_repair:
    declick: medium
    deesser: gentle
    denoise: none
    loudnorm: librivox

roles:
  GOD:
    profile: none
  MEGAERA:
    profile: mouth_click_repair
```

The config file should be optional. If absent, cleanup commands can still run with a built-in `gentle_voice_cleanup` preset.

`cleanup_approach` controls how Stager chooses cleanup settings for roles without explicit overrides:

- `profile-based`: use `default_profile` for roles without overrides.
- `analysis-based`: use cleanup analysis recommendations for roles without overrides.

`profile-based` should be the default because it is predictable and simple. `analysis-based` is useful when recordings vary significantly by actor, room, microphone, or take quality.

`default_profile` is the normal profile-based configuration. It applies to every role that does not have an explicit override. Most productions should only need a default profile plus a small number of role overrides for unusually noisy, click-heavy, sibilant, or idiosyncratic recordings.

Role override resolution:

- Missing role override with `cleanup_approach: profile-based`: use `default_profile`.
- Missing role override with `cleanup_approach: analysis-based`: use the latest accepted cleanup analysis recommendation.
- `profile: none`: disable cleanup for that role.
- `profile: <name>`: use the named profile instead of the configured cleanup approach.
- `analysis: true`: use analysis for that role even when the play is profile-based.
- `analysis: false`: use `default_profile` for that role even when the play is analysis-based.

If `audio_cleanup.yaml` is absent, Stager should behave as if `cleanup_approach: profile-based` and `default_profile: gentle_voice_cleanup` were configured. If the file exists but omits `cleanup_approach`, Stager should default to `profile-based`. If the file exists but omits `default_profile`, Stager should use `gentle_voice_cleanup` unless the command explicitly asks for another profile with `--profile`.

For `analysis-based` cleanup, rendering must fail with a clear diagnostic if no accepted analysis report exists for a requested recording. Stager should not silently fall back from analysis to a profile because that would make rendered output depend on hidden state.

Candidate file:

```text
plays/<play_id>/audio_cleanup.yaml
```

## FFmpeg Filters

Required baseline filters:

- `loudnorm`: final loudness normalization.
- `atrim` and `asetpts`: trim/tail handling.

Optional cleanup filters:

- `adeclick`: click and mouth-click cleanup. This is the first filter to try for short impulsive mouth clicks.
- `deesser`: sibilance cleanup.
- `afftdn`: FFT denoising, useful for light room noise and hiss.
- `afwtdn`: wavelet denoising, useful as an alternate denoiser.
- `anlmdn`: non-local-means denoising; useful but potentially slower.
- `agate`: between-phrase noise reduction.

These filters are native FFmpeg filters when present. They do not require GPL-enabled FFmpeg or separate plugins. FFmpeg builds can disable individual filters, so Stager must probe and report them. Missing optional filters should disable the related cleanup preset or warn; they should not fail all cleanup.

## Cleanup Analysis

Stager should include an analysis step that inspects recordings before cleanup and recommends a profile or parameter set. Analysis should make cleanup easier to use, but it should not silently apply aggressive processing. The first implementation should write recommendations into a report and let render/review commands use them explicitly.

Initial analysis inputs:

- accepted segment audio,
- LineRecorder floor-noise or room-tone samples when present,
- recording-package metadata that associates takes with floor-noise samples,
- optional existing `audio_cleanup.yaml` defaults and role overrides.

LineRecorder floor-noise capture is the preferred noise-profile source. The export/import contract is planned in [../linerecorder/floor_noise_reduction_plan.md](../linerecorder/floor_noise_reduction_plan.md). When a recording has an associated floor-noise sample, Stager should use it to estimate the room noise floor and to drive denoising choices. When no floor-noise sample is available, analysis may estimate noise from leading/trailing quiet regions, but it should mark those recommendations as lower confidence.

Analysis should estimate:

- broadband noise floor and whether denoising is warranted,
- suggested denoise strength, starting conservatively,
- click density or impulsive-noise likelihood,
- sibilance risk and suggested de-essing strength,
- leading/trailing silence trim candidates,
- clipping or near-clipping risk,
- loudness normalization feasibility and expected gain change.

The analysis output should be inspectable, for example:

```text
build/<play_id>/audio/cleanup_analysis/report.json
build/<play_id>/audio/cleanup_analysis/report.md
```

The report should include the source recording, role, segment id, floor-noise id if used, measured values, recommended cleanup profile, confidence, and warnings about risky processing. Recommendations should be role-aware because one actor/room/microphone combination may need different cleanup from another.

For `afftdn`, floor-noise samples should be used as measured noise profiles where possible. A practical implementation can prepend the floor-noise sample to the recording, send `afftdn` commands to sample that interval, then trim the prepended audio before writing the cleaned output. This keeps cleanup deterministic and avoids requiring external model files.

## Batch Rendering And Boundaries

The preferred cleanup renderer should operate on batches, not individual segments. Per-segment rendering is simpler, but it is likely to be slower and gives analysis/filters too little context. The first batch grouping should be conservative:

- same play,
- same role or recording package grouping,
- same cleanup profile or analysis recommendation,
- same floor-noise id when present,
- same sample rate after normalization.

Batch construction should use anchor-based boundaries:

1. Normalize source segments to a common sample rate.
2. Concatenate segments with generated silence padding between them.
3. Default padding should be generous, initially `3.0` seconds, and configurable with `batch_padding_seconds`.
4. Store each segment's original start sample, original end sample, center sample, source duration, source hash, and guard/padding range in the batch manifest.
5. Run cleanup over the batch without global silence removal.
6. After cleanup, search inside each segment's padded window to detect the cleaned speech start/end.
7. Use the original center sample as an anchor so detection does not grab neighboring audio.
8. Split cleaned output using the detected boundaries.
9. Apply loudness normalization as a final per-segment step after the cleaned batch has been split, so loudness does not affect boundary detection and each exported segment has its own measured normalization pass.

The renderer should treat duration-preserving cleanup as the normal batch contract. Filters such as denoise, declick, de-ess, EQ, compression, limiting, and loudness normalization are expected to preserve timeline length. If a filter chain is not duration-preserving, it should not be batch-rendered unless it can emit reliable edit-decision metadata.

Post-cleanup boundary detection is necessary because clicks and mouth noise can artificially extend an original segment. Cleanup may remove or reduce those artifacts, making the cleaned segment's natural end earlier than the original end. Boundary detection should be conservative: it may trim obvious leading/trailing silence, but it must preserve speech around the original center anchor.

Boundary validation should warn when detected boundaries differ significantly from the original segment. Initial warning thresholds:

- cleaned start moves more than `boundary_warning_ms`,
- cleaned end moves more than `boundary_warning_ms`,
- cleaned duration changes by more than 20%,
- detected speech no longer contains the original center anchor,
- detected range approaches or crosses the midpoint of the padding toward a neighboring segment,
- detected range is empty.

Suspicious boundary shifts should be written to the cleanup manifest and review report. Severe cases should fall back to per-segment cleanup or require manual review instead of silently producing split audio.

Generated batch manifests should be inspectable:

```text
build/<play_id>/audio/cleaned/<batch_id>/batch_manifest.json
```

Each manifest entry should include both original and cleaned ranges so later review can explain exactly why a segment became shorter or longer. The render cache key should include source hashes, original ranges, floor-noise hash when present, resolved cleanup filters, selected loudnorm profile, padding, and boundary warning settings.

## Licensing

The MVP must work with a normal LGPL-compatible FFmpeg installation. Quince must not require GPL-enabled FFmpeg for audio cleanup.

`arnndn` is out of scope for the MVP. It requires an external `.rnnn` model file, and each model's license must be reviewed separately before use.

`ladspa` and `lv2` plugin hosts are out of scope for the MVP because plugin installation and plugin licensing would make support harder.

## Presets

Initial presets should be conservative:

- `declick_gentle`
- `declick_medium`
- `deesser_gentle`
- `denoise_light`
- `voice_cleanup_gentle`

Presets should be implemented as ordinary FFmpeg transform chains. They should not overwrite source audio by default.

## Build Integration

Initial commands:

```sh
./main audio-cleanup --play <play_id>
./main audio-cleanup --play <play_id> --role MEGAERA
./main audio-cleanup analyze --play <play_id>
./main audio-cleanup doctor
```

The doctor command should report:

- FFmpeg path,
- FFprobe path,
- config source or PATH fallback,
- required cleanup filters present/missing,
- optional cleanup filters present/missing.

## Review Policy

Cleanup should support review before adoption:

- render cleaned files into a generated directory,
- write a manifest with source path, output path, preset, and filter chain,
- optionally generate a comparison report,
- only promote cleaned output into canonical segment storage through an explicit command or option.

## Relationship To Voice Profiles

Audio cleanup can run before voice effects. Voice effects should consume cleaned or canonical segment audio depending on build options.

Voice profiles own actor/role characterization. Audio cleanup owns recording-quality repair.
