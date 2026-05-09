## Project context
This project is a Python command-line application for creating audio plays.

The key workflows are:
- Convert a play written in the custom text format defined in `src/format.md` into markdown artifacts, including one role file per role plus special roles such as Narrator, Caller, and Announcer.
- Split role recordings into individual segment files based on silence, verify those segments against the play text, and reassemble them in play order.
- Build supporting artifacts such as audio plans, captions, timing sheets, verification workbooks, cue files, and Librivox-style output.

Play inputs live under `plays/<play_id>/`. The main source file is `play.txt`; related metadata may include `source_text_metadata.yaml`, `reading_metadata.yaml`, and `substitutions.yaml`.

Generated artifacts live under `build/<play_id>/`.

## Development workflow
Always use the repository virtualenv Python at `.venv/bin/python` instead of attempting to use the global Python.

Run the full test suite with:

```sh
.venv/bin/python run_tests.py
```

`run_tests.py` sets `PYTHONPATH=src`. For targeted test runs, use:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/test_name.py
```

Avoid tests that require real recordings, downloaded Whisper models, network access, or ffmpeg unless the test explicitly mocks or skips those dependencies.

## Coding style
Use Python object-oriented code style. Prefer classes over standalone functions for production behavior.

Default to dataclasses when creating new data-holding classes.

Use one primary class per file for new code. Existing grouped model files such as `play.py`, `block.py`, `segment.py`, and `clip.py` may keep closely related small dataclasses together; do not split them as part of unrelated changes.

Prefer dependency injection for collaborators such as `paths.PathConfig`, parsed `Play` objects, Whisper stores, transcription caches, and audio helpers. This keeps tests fast and lets them use `tmp_path` and monkeypatching.

## Paths and configuration
Prefer passing `paths.PathConfig` into classes and helpers instead of reading module-level path globals.

Avoid adding new uses of the backwards-compatible path aliases in `paths.py` such as `BUILD_DIR`, `SEGMENTS_DIR`, or `RECORDINGS_DIR`.

Use `play-config.yaml` and the existing `--play/-p` CLI convention for selecting a play.

## CLI
The main CLI is Typer-based in `src/build.py`. Add new CLI commands there unless there is a strong reason to create a separate script.

For play-specific commands, support the existing `--play/-p` option.

Use `typer.BadParameter` for invalid CLI arguments. Use normal exceptions for internal failures.

CLI commands may use `typer.echo` for deliberate user-facing terminal output.

## Defensive programming
Do not program defensively. If an unexpected condition occurs, raise an exception.

In some cases I will change exceptions to logging. If you see an error condition being logged, do not change it back.

## Audio and transcription
Audio workflows may depend on ffmpeg, pydub, faster-whisper, and local Whisper model caches.

Do not introduce behavior that requires model downloads during normal tests.

When adding tests around audio length, splitting, transcription, verification, or Whisper behavior, mock expensive or external operations and use temporary files/directories.

## Logging
Reusable classes should use Python's logging mechanism with `logging.getLogger(__name__)`.

Do not use `print()` in library code.

Use logging for build progress, diagnostics, and generated artifact paths.
