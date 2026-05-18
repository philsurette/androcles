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

default_profile: gentle_voice_cleanup

profiles:
  gentle_voice_cleanup:
    declick: gentle
    deesser: gentle
    denoise: light
    loudnorm: librivox

roles:
  GOD:
    profile: none
  MEGAERA:
    profile: gentle_voice_cleanup
```

The config file should be optional. If absent, cleanup commands can still run with a built-in `gentle_voice_cleanup` preset.

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

These filters are native FFmpeg filters when present. They do not require Rubber Band, `ffmpeg-full`, GPL-enabled FFmpeg, or separate plugins. FFmpeg builds can disable individual filters, so Stager must probe and report them. Missing optional filters should disable the related cleanup preset or warn; they should not fail all cleanup.

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

