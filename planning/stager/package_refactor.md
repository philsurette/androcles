# Package Refactor Plan

This document defines the package structure Stager should move toward before adding substantial Playbook code.

## Goal

Create explicit Python package boundaries so shared parsing/domain code can be reused by both actor-facing outputs:

- legacy MP4 cue files for general-purpose audio players
- Cuemaster Playbooks for the Cuemaster app

The refactor should preserve current CLI behavior and keep each migration slice testable.

## Proposed Source Layout

```text
src/stager/
  __init__.py

  cli/
    __init__.py
    build.py

  shared/
    __init__.py
    paths.py
    play_config.py
    build_type_resolver.py

  domain/
    __init__.py
    play.py
    block.py
    block_id.py
    segment.py
    segment_id.py
    reader_block.py

  text/
    __init__.py
    play_text_parser.py
    role_markdown_writer.py
    narrator_markdown_writer.py
    play_markdown_writer.py
    callout_script_writer.py
    announcer_script_writer.py
    announcer.py

  audio/
    __init__.py
    audio_check.py
    audio_mixer.py
    audio_splitter.py
    segment_splitter.py
    role_splitter.py
    narrator_splitter.py
    announcer_splitter.py
    segment_audio_player.py
    spacing.py

  audiobook/
    __init__.py
    audio_plan.py
    audio_plan_writer.py
    caption_builder.py
    chapter.py
    chapter_builder.py
    clip.py
    librivox_announcer_markdown_writer.py
    librivox_play_plan_decorator.py
    play_audio_builder.py
    play_builder.py
    play_plan_builder.py
    play_plan_decorator.py
    timings_xlsx.py

  cues/
    __init__.py
    callout_director.py
    cue_builder.py
    narration_cues.py
    role_cues.py

  verification/
    __init__.py
    audio_verifier_diff.py
    audio_verifier_diff_builder.py
    audio_verifier_problems_sheet_builder.py
    audio_verifier_sheet_builder.py
    audio_verifier_summary_renderer.py
    audio_verifier_summary_sheet_builder.py
    audio_verifier_workbook_writer.py
    audio_verifier_xlsx_writer.py
    diff_context.py
    diff_event.py
    diff_walker.py
    equivalencies.py
    extra_audio_diff.py
    homophone_matcher.py
    inline_text_diff.py
    inline_text_differ.py
    inline_text_replacement.py
    match_audio_diff.py
    missing_audio_diff.py
    recording_checker.py
    role_audio_verifier.py
    segment_verifier.py
    spelling_normalizer.py
    token_comparator.py
    token_slice.py
    unresolved_diffs.py

  transcription/
    __init__.py
    role_whisper_transcriber.py
    vad_config.py
    whisper_cache_cleaner.py
    whisper_model_store.py
    whisper_transcription_cache.py
    word_audio_splitter.py

  playbook/
    __init__.py
    app_manifest.py
    app_role.py
    app_line.py
    app_audio_asset.py
    playbook_builder.py
    playbook_cue_selector.py

  loudnorm/
    __init__.py
    ...
```

## Proposed Test Layout

Unit tests should mirror source package boundaries:

```text
tests/stager/domain/
tests/stager/shared/
tests/stager/text/
tests/stager/audio/
tests/stager/audiobook/
tests/stager/cues/
tests/stager/verification/
tests/stager/transcription/
tests/stager/playbook/
```

Integration tests may stay grouped by workflow:

```text
tests/integration/
```

Integration tests can cover CLI commands, generated file layouts, and workflows that cross package boundaries.

## Import Rules

Use absolute package imports after a module moves:

```python
from stager.domain.play import Play
from stager.shared.paths import PathConfig
```

Avoid new bare imports such as:

```python
from play import Play
import paths
```

Allowed dependency direction:

- `cli` may import services from any Stager package.
- `playbook` may import `domain`, `shared`, and focused audio-file helpers.
- `playbook` must not import `audiobook`, `cues`, or MP4 chapter models.
- `audiobook` and `cues` may import `domain`, `shared`, and `audio`.
- `verification` may import `domain`, `shared`, `audio`, and transcription helpers.
- `domain` must not import output packages.

## Compatibility Strategy

Use compatibility wrappers during migration when necessary.

Example:

```python
# src/play.py
from stager.domain.play import *
```

Wrappers should be temporary and removed once all imports and tests use package paths.

Do not mix moved implementation and wrapper behavior in the same file. After a module moves, the old top-level module should only re-export from the package module.

## Migration Checklist

- [x] Create `src/stager/` and package `__init__.py` files.
- [ ] Move `loudnorm` under `src/stager/loudnorm` or explicitly decide to keep it as a separate package.
- [x] Move domain modules first: `block_id.py`, `segment_id.py`, `segment.py`, `block.py`, `reader_block.py`, `play.py`.
- [x] Update domain imports to `stager.domain.*`.
- [x] Move matching unit tests under `tests/stager/domain/`.
- [x] Add temporary top-level wrappers for moved domain modules.
- [x] Run domain tests.
- [x] Move shared modules: `paths.py`, `play_config.py`, `build_type_resolver.py`.
- [x] Update shared imports to `stager.shared.*`.
- [x] Move matching unit tests under `tests/stager/shared/`.
- [x] Add temporary top-level wrappers for moved shared modules.
- [x] Run shared and domain tests.
- [ ] Move text artifact modules.
- [ ] Move matching unit tests under `tests/stager/text/`.
- [ ] Run text, shared, and domain tests.
- [ ] Move audio splitting/playback utility modules.
- [ ] Move matching unit tests under `tests/stager/audio/`.
- [ ] Run audio-related tests.
- [ ] Move audiobook modules.
- [ ] Move legacy MP4 cue modules to `stager.cues`.
- [ ] Move matching unit tests under `tests/stager/audiobook/` and `tests/stager/cues/`.
- [ ] Run audiobook and cue tests.
- [ ] Move verification modules.
- [ ] Move matching unit tests under `tests/stager/verification/`.
- [ ] Run verification tests.
- [ ] Move transcription modules.
- [ ] Move matching unit tests under `tests/stager/transcription/`.
- [ ] Run transcription tests that do not require model downloads.
- [ ] Move `build.py` to `stager.cli.build`.
- [ ] Update `./main` to invoke `stager.cli.build`.
- [ ] Keep current CLI commands and `--play/-p` behavior unchanged.
- [ ] Add Playbook modules under `stager.playbook` only after shared/domain boundaries are established.
- [ ] Remove temporary top-level compatibility wrappers after all imports use package paths.
- [ ] Run `.venv/bin/python run_tests.py`.
- [ ] Run `./main --help`.
- [ ] Run a representative safe CLI command such as `./main text`.

## Commit Slices

- [ ] Commit 1: add package directories, move domain modules, keep wrappers, move domain tests.
- [ ] Commit 2: move shared config/path modules and tests.
- [ ] Commit 3: move text modules and tests.
- [ ] Commit 4: move audio modules and tests.
- [ ] Commit 5: move audiobook and cue modules and tests.
- [ ] Commit 6: move verification and transcription modules and tests.
- [ ] Commit 7: move CLI entrypoint and update `./main`.
- [ ] Commit 8: remove compatibility wrappers once no imports require them.

## Notes

- Keep `CueBuilder` in the legacy cue-output package, not in Playbook code.
- Keep `PlaybookBuilder` independent of audiobook and cue packages.
- Do not do broad behavior changes in package-move commits.
- Do not update generated `build/` artifacts as part of package refactors.
