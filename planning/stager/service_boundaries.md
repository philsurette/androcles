# Stager Service Boundaries

This document defines target service boundaries for hardening Stager before Playbook generation.

## Principle

`src/build.py` should own CLI parsing and user-facing command wiring. Domain behavior should live in injectable service classes that receive explicit dependencies and raise exceptions on failure.

Stager should support two actor-facing rehearsal outputs:

- Legacy cue MP4 files for use in general-purpose audio players.
- Cuemaster Playbooks for use in the Cuemaster app.

These outputs should share parsed play structure and segment audio assets, but they should not share output-specific assembly code. In particular, Playbook generation should not depend on MP4 cue-file chapter markers or `CueBuilder` internals.

## Module Categories

Stager code should move toward three module categories.

Shared modules:

- own source parsing, play models, ids, reader metadata, role metadata, segment identity, and reusable audio-file lookup
- may be used by audiobook, cue MP4, verification, and Playbook outputs
- examples in the current codebase: `play.py`, `block.py`, `segment.py`, `block_id.py`, `segment_id.py`, `play_text_parser.py`, `paths.py`

Audiobook and legacy cue-output modules:

- own assembled audio-play/audiobook outputs, Librivox decoration, captions, timings, and role cue MP4 generation
- may use MP4 chapter markers and pydub/ffmpeg assembly details
- should not be imported by Playbook builders except through clearly shared lower-level utilities
- examples in the current codebase: `play_builder.py`, `play_plan_builder.py`, `play_audio_builder.py`, `librivox_play_plan_decorator.py`, `chapter_builder.py`, `cue_builder.py`

Playbook modules:

- own Cuemaster manifest records, cue/response selection, required-audio validation, and package layout
- should emit structured JSON plus audio assets, not assembled MP4 cue tracks
- should use shared models and segment audio files directly
- proposed modules: `app_manifest.py`, `app_role.py`, `app_line.py`, `app_audio_asset.py`, `playbook_builder.py`, and a Playbook-specific cue selector

If a class needs to know about MP4 chapter markers, it belongs to the audiobook/legacy cue-output category, not the Playbook category.

## Proposed Services

- `TextArtifactBuilder`: parses play text and writes paragraphs, block files, role markdown, caller scripts, announcer scripts, and source markdown.
- `SegmentBuildService`: splits recordings into segment WAV files and verifies segment counts.
- `TimingBuildService`: builds timing sheets and related timing artifacts.
- `AudioPlayBuildService`: assembles audiobook/audio-play outputs.
- `CueBuildService`: builds Stager cue MP4s using `CueBuilder`.
- `PlaybookBuilder`: writes the Cuemaster Playbook directory, manifest, and audio assets without using `CueBuilder`.

Each service should be a class. New data-only support types should be dataclasses.

## Dependency Ownership

Services should receive dependencies through constructors:

- `paths.PathConfig`
- parsed `Play` when the caller already has one
- parser/build helpers where test injection is useful
- audio duration helpers when tests need tiny fixtures

Services should not call `paths.current()` internally except as a transitional compatibility wrapper.

## External Dependencies

External dependencies should be isolated by service:

- `TextArtifactBuilder`: no ffmpeg, pydub, Whisper, or Audacity.
- `SegmentBuildService`: may use pydub and ffmpeg.
- `TimingBuildService`: may read audio lengths; should not invoke Whisper unless explicitly needed by a timing feature.
- `AudioPlayBuildService`: may use pydub and ffmpeg.
- `CueBuildService`: may use pydub and ffmpeg.
- `PlaybookBuilder`: may read audio lengths and copy or link files; should not invoke Whisper, ffmpeg assembly, or MP4 chapter generation.

Whisper/model-download behavior must stay out of normal tests.

## CLI Ownership

Typer commands in `src/build.py` should:

- validate options
- construct or select `PathConfig`
- construct the service
- call one service method
- use `typer.echo` only for deliberate CLI output

Services should:

- use `logging.getLogger(__name__)`
- raise exceptions for internal failures
- return generated paths or result objects instead of printing

## Testability

Fast service tests should use:

- in-memory `Play` objects where possible
- `tmp_path` for build/play roots
- tiny generated WAV files for audio fixtures
- monkeypatching for ffmpeg or expensive external calls

The Playbook path should be testable without real project recordings.
