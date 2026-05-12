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
