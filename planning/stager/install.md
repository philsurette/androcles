# Stager Install Notes

This note describes the first install path for technical showrunners. It is not yet the standalone app bundle.

## Prerequisites

- Python 3.11 or newer.
- `ffmpeg` and `ffprobe` on `PATH` for audio commands.

Install ffmpeg separately:

- macOS: `brew install ffmpeg`, or install another trusted ffmpeg package.
- Windows: install ffmpeg from a trusted distribution and add its `bin` directory to `PATH`.
- Linux: install ffmpeg from the system package manager, such as `apt install ffmpeg`.

Stager checks for `ffmpeg` and `ffprobe` before commands that need them.

Quince/Stager does not bundle FFmpeg. Required Stager audio features must work with a normal LGPL-compatible FFmpeg installation. GPL-enabled FFmpeg builds are optional user-managed tools only.

## FFmpeg For Voice Profiles

Voice-profile rendering will use FFmpeg filters. Quince/Stager will not bundle FFmpeg, so showrunners need an FFmpeg build with the required filters available.

Verify the installed commands:

```sh
ffmpeg -version
ffprobe -version
```

List available filters:

```sh
ffmpeg -hide_banner -filters
```

Required filters for the portable voice-profile renderer:

- `aresample`
- `asetrate`
- `atempo`
- `highpass`
- `lowpass`
- `equalizer`
- `acompressor`
- `volume`
- `alimiter`
- `aecho`
- `atrim`
- `asetpts`
- `loudnorm`

Optional filters that improve quality or future effects:

- `concat`: future role-batch rendering and some integration fixtures.
- `firequalizer`: smoother filter-curve implementation.
- `afir`: convolution reverb if impulse responses are added later.

The first voice-profile implementation should work without optional quality filters. Pitch shifting in the MVP should use the portable `asetrate`/`aresample`/`atempo` path. If `loudnorm` is missing, Stager should fail voice-profile rendering because rendered role voices need consistent perceived loudness.

Check Stager's view of the installed FFmpeg:

```sh
./main voice-profiles doctor --play <play_id>
```

The doctor command reports the FFmpeg and FFprobe paths, whether required voice-profile filters are available, and whether optional filters are present. Stager first looks for a Quince FFmpeg config file and then falls back to `ffmpeg`/`ffprobe` on `PATH`.

Troubleshooting:

- If `voice-profiles doctor` reports a missing required filter, use a fuller LGPL-compatible FFmpeg build from a trusted distribution and rerun the doctor command.
- If only `concat`, `firequalizer`, or `afir` is missing, MVP per-segment voice rendering can still work. Those filters are optional for the current implementation.
- If FFmpeg is installed but Stager cannot find it, add the FFmpeg `bin` directory to `PATH` or create a Quince `ffmpeg.conf` file as described in [../../docs/quince_ffmpeg_rubberband_installation.md](../../docs/quince_ffmpeg_rubberband_installation.md).

## FFmpeg For Audio Cleanup

Audio cleanup uses FFmpeg for conservative recording-quality repair before creative voice effects. The MVP must work with a normal LGPL-compatible FFmpeg installation.

Required cleanup filters:

- `loudnorm`
- `atrim`
- `asetpts`

Optional cleanup filters:

- `adeclick`: optional click and mouth-click cleanup.
- `deesser`: optional sibilance cleanup.
- `afftdn`: optional FFT denoising.
- `afwtdn`: optional wavelet denoising.
- `anlmdn`: optional non-local-means denoising.
- `agate`: optional between-phrase noise gate.

The optional cleanup filters listed above are native FFmpeg filters. They do not require separate plugins or GPL-enabled FFmpeg when they are present in a normal FFmpeg build, but FFmpeg builds can disable individual filters. If a cleanup filter is missing, Stager should disable or warn for that cleanup preset rather than failing all cleanup or voice-profile rendering.

`arnndn` is not part of the baseline cleanup feature. It requires an external model file, and model licenses must be reviewed separately before use.

If a required filter is missing, install a fuller FFmpeg build from a trusted distribution. If only optional filters are missing, audio cleanup should still work with reduced presets or clear warnings.

Do not treat `ffmpeg-full` or Rubber Band as a Quince dependency. Rubber Band is a follow-on feature and must stay outside the MVP.

## Build A Wheel

From the repository root:

```sh
.venv/bin/python -m build --no-isolation
```

The wheel is written under:

```text
dist/
```

## Install From A Wheel

In a user environment with Python available:

```sh
python -m pip install dist/quince_stager-0.1.0-py3-none-any.whl
```

For an isolated command-line install, `pipx` is the intended direction once dependencies are published cleanly:

```sh
pipx install dist/quince_stager-0.1.0-py3-none-any.whl
```

## Run Stager

The package installs a `stager` command:

```sh
stager --help
stager scriptwright lock --help
stager playbook --help
```

Normal play-specific commands keep the existing `--play/-p` convention:

```sh
stager scriptwright lock --play <play_id>
stager text --play <play_id>
stager playbook --play <play_id> --audio-format mp3
```

## Current Packaging Caveats

- The wheel depends on Python packages from normal package indexes.
- The local editable `../audacity_export` dependency is not part of the wheel metadata. Stager imports without it, but Audacity export support requires `audacity-ctl` to be installed separately.
- `ffmpeg` is intentionally not bundled.
- The standalone app bundle milestone still needs PyInstaller or equivalent work.
