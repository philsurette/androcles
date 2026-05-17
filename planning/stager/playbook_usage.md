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

Build a Playbook with MP3 audio assets:

```sh
./main playbook --audio-format mp3
```

Supported Playbook audio formats are `wav` and `mp3`. The default is `wav`; MP3 assets are encoded at 128 kbps.

The command is strict. It raises if any rehearsable non-meta role line is missing required cue audio or response audio.

Playbook generation copies production metadata from the selected production source into `manifest.json`. Published-source builds include `production.version`, `production.sequence`, `production.publication_id`, and `production.source: "published"`. Working-source preview builds are marked with `production.source: "working"` and do not create synthetic production versions.

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

When `--audio-format mp3` is used, segment files are written with `.mp3` extensions and manifest audio paths point to those `.mp3` files.

Manifest audio paths are relative to the Playbook root, not repository-root paths.

## Required Inputs

Playbook generation expects a locked production script and split segment audio:

- `plays/<play_id>/production.md` with `production_ids: locked`
- `build/<play_id>/audio/segments/<ROLE>/<segment_id>.wav`
- cue audio for every rehearsable role line
- response audio for every rehearsable role line

For release/distribution builds, publish the production first:

```sh
./main publish-production --play <play_id> --change-summary "Describe the release script state."
```

The Playbook command does not mutate `plays/<play_id>/production.md`; it only records the production metadata it was built from.

Run the relevant Stager preparation commands before Playbook export:

```sh
./main scriptwright lock
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

The Playbook builder reads source WAV durations for manifest `duration_ms`. When exporting MP3 Playbooks, `duration_ms` remains the source WAV audible content duration rather than an MP3 container duration.

Cue-start offsets are computed from the source WAV and may be emitted for both WAV and MP3 Playbooks. MP3 playback can have small encoder/player seek drift, but Stager treats the offsets as content-timeline values.

The builder does not assemble MP4 files or invoke Whisper. It uses the same Python audio stack as the rest of Stager, so the repository virtualenv must be used. MP3 Playbook export uses pydub's ffmpeg-backed encoder.

Audio preparation before Playbook export may require Audacity exports, pydub, and ffmpeg through the segment-splitting workflow.
