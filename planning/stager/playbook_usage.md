# Stager Playbook Usage

This note documents the current Stager-side Playbook export workflow. The manifest contract remains defined in `planning/specs/playbook_manifest.md`.

## Command

Build a Playbook for the configured play:

```sh
./main playbook
```

Build a Playbook for a specific play directory:

```sh
./main playbook --play androcles
```

The command is strict. It raises if any rehearsable non-meta role line is missing required cue audio or response audio.

## Output Layout

Stager writes an unpacked Playbook directory for inspection and a distributable zip package.

The zip package is:

```text
build/<play_id>/<play_id>.playbook.zip
```

Cuemaster imports this `.zip` file.

The unpacked inspection directory is:

```text
build/<play_id>/app/
```

Expected layout:

```text
build/<play_id>/app/
  manifest.json
  audio/
    segments/
      <ROLE>/
        <segment_id>.wav
```

Manifest audio paths are relative to the Playbook root, not repository-root paths.

## Required Inputs

Playbook generation expects parsed play text and split segment audio:

- `plays/<play_id>/play.txt`
- `build/<play_id>/audio/segments/<ROLE>/<segment_id>.wav`
- cue audio for every rehearsable role line
- response audio for every rehearsable role line

Run the relevant Stager preparation commands before Playbook export:

```sh
./main text
./main segments
./main playbook
```

## Tests

Run Playbook-focused tests with:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/stager/playbook
```

Run the full suite with:

```sh
.venv/bin/python run_tests.py
```

## External Dependencies

The current Playbook builder reads WAV durations and copies existing segment audio. It does not assemble MP4 files or invoke Whisper. It uses the same Python audio stack as the rest of Stager, so the repository virtualenv must be used.

Audio preparation before Playbook export may require Audacity exports, pydub, and ffmpeg through the segment-splitting workflow.
