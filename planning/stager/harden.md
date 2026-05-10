# Codebase Hardening Plan

This plan prepares Stager, the current CLI codebase, for reliable Cuemaster Playbook generation. It is written as a resumable checklist: complete each item, commit in small logical chunks, and leave notes under the relevant section if work is paused.

## Goals

- Preserve the existing Stager CLI workflows for markdown, segment splitting, verification, timings, cues, and audioplay.
- Make legacy MP4 cue generation correct and tested for actors who use general-purpose audio players.
- Introduce a stable Cuemaster-facing export boundary rather than requiring the mobile app to infer structure from markdown, spreadsheets, or MP4 chapter metadata.
- Build Playbooks from shared play/segment data, not from legacy audiobook or MP4 cue assembly internals.
- Reduce coupling in the Stager CLI so future Playbook packaging can reuse domain services directly.
- Make Playbook builds fail on missing required cue or response audio unless explicitly running in a diagnostic mode.

## Non-Goals

- Do not build the iOS or Android app in this phase.
- Do not change the custom play text format unless a design doc explicitly identifies a required format change.
- Do not remove existing audio verification, Librivox, or markdown outputs.
- Do not require network access, downloaded Whisper models, or real recordings in normal tests.

## Current Findings To Address

- `CueBuilder` likely returns empty audio because helper methods receive an `AudioSegment` and use `+=`, which rebinds locally instead of mutating the caller's value.
- Missing segment audio is sometimes logged and represented as zero-length clips instead of failing the build.
- There is no versioned Cuemaster manifest or Playbook format.
- Existing `src/` modules are heavily oriented around audiobook/audio-play assembly; Playbook work needs a separate output layer over shared play and segment models.
- Existing modules are top-level files with bare imports; package boundaries should be introduced before substantial Playbook implementation.
- `src/stager/cli/build.py` is too large and mixes Typer/Stager CLI concerns with orchestration and domain behavior.
- `paths.py` still exposes import-time default play state and backwards-compatible global aliases.
- Some library-style modules still use `print()` instead of logging or caller-owned output.

## Phase 0: Design Docs First

Create these design documents before changing production behavior. Keep them short and concrete.

- [x] Create `planning/cuemaster/app_manifest.md`.
- [x] Document the intended consumer: Cuemaster, offline-first, per-role Playbook.
- [x] Define manifest versioning, e.g. `"schema_version": 1`.
- [x] Define Playbook layout, e.g. `build/<play>/app/manifest.json`, `build/<play>/app/audio/...`.
- [x] Define role payloads: role id, display name, reader, part list, cue/line sequence.
- [x] Define line item fields: block id, segment ids, speaker, cue text, response text, direction text, audio paths, duration ms, offsets if applicable.
- [x] Define how simultaneous lines are represented.
- [x] Define how narrator, caller, and announcer are represented or excluded for actor rehearsal.
- [x] Define whether Playbook paths are relative to the manifest.
- [x] Define strict Playbook behavior for missing cue and response audio.
- [x] Align `planning/cuemaster/product_design.md` with the Stager manifest and Playbook design.

- [x] Create `planning/cuemaster/cue_generation.md`.
- [x] Document current cue behavior: previous speech block as prompt, optional callout, cropped cue audio, response delay, expected response playback.
- [x] Define desired cue behavior for first line in a part or scene.
- [x] Define whether stage directions are prompts, context text, playable audio, or ignored.
- [x] Define whether caller/announcer snippets are included in Cuemaster Playbooks.
- [x] Define expected chapter or item boundaries for generated cue media.
- [x] Define deterministic test fixtures for cue audio without using real recordings.

- [x] Create `planning/stager/service_boundaries.md`.
- [x] Define domain services to extract from `src/stager/cli/build.py`.
- [x] Proposed services: `TextArtifactBuilder`, `SegmentBuildService`, `TimingBuildService`, `AudioPlayBuildService`, `CueBuildService`, `PlaybookBuilder`.
- [x] Define which services may call ffmpeg, pydub, Whisper, or Audacity.
- [x] Define which services are pure enough for fast tests.
- [x] Define Stager CLI ownership: Typer validates options and delegates to services; services raise exceptions.
- [x] Define path/config ownership: all services receive `paths.PathConfig` and never rely on `paths.current()`.
- [x] Define shared, audiobook/legacy cue-output, and Playbook module categories.

- [x] Create `planning/stager/package_refactor.md`.
- [x] Propose source package structure.
- [x] Propose mirrored unit-test package structure.
- [x] Define compatibility-wrapper migration strategy.
- [x] Define package dependency rules for Playbook, audiobook, cues, shared, and domain code.
- [x] Define package-refactor commit slices.

- [x] Create `planning/stager/missing_audio_policy.md`.
- [x] Define required versus optional audio categories.
- [x] Required for Playbooks: cue audio and response audio for every rehearsable non-meta role line.
- [x] Required when enabled: callouts, announcer, narrator, Librivox preamble/epilog snippets.
- [x] Optional or diagnostic: timing previews with missing audio placeholders, if still needed.
- [x] Define Stager CLI flags for diagnostic mode, e.g. `--allow-missing-audio`.
- [x] Define exact exception type or error message style for missing required audio.

## Phase 1: Fix CueBuilder Correctness

Target outcome: cue generation returns non-empty audio and correct chapter boundaries for roles with available segment audio.

- [x] Add failing tests that reproduce the current `AudioSegment` accumulation issue.
- [x] Use tiny generated WAV files in `tmp_path` fixtures so tests do not require real recordings.
- [x] Test that `build_cues_for_role("A")` returns audio length greater than zero when role A has response audio.
- [x] Test that cue chapters include both `CUE <role> <segment>` and `LINE <role> <segment>` when prompts are enabled and a previous speaker exists.
- [x] Test that cue generation works when prompts are disabled.
- [ ] Test that first-line behavior matches `planning/cuemaster/cue_generation.md`.
- [x] Refactor `CueBuilder` helpers to return updated audio and chapter data instead of trying to mutate `AudioSegment` parameters.
- [x] Keep `CueBuilder` as a dataclass.
- [x] Avoid adding defensive fallbacks; raise exceptions for missing required audio according to the policy design.
- [x] Verify `run_cues()` still writes cue files through the Stager CLI.
- [x] Run targeted tests: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_alignment_gaps.py`.
- [x] Run full tests: `.venv/bin/python run_tests.py`.

## Phase 1.5: Introduce Package Boundaries

Target outcome: Stager has explicit Python package boundaries before new Playbook implementation expands the codebase.

Follow `planning/stager/package_refactor.md`.

- [x] Create `src/stager/` package directories.
- [x] Move domain modules and matching unit tests first.
- [x] Move shared config/path modules and matching unit tests.
- [x] Move text artifact modules and matching unit tests.
- [x] Move audio splitting/playback modules, Audacity export, and matching unit tests.
- [x] Move audiobook modules and matching unit tests.
- [x] Move legacy MP4 cue modules and matching unit tests.
- [x] Move verification modules and matching unit tests.
- [x] Move transcription modules and matching unit tests.
- [x] Move `loudnorm` under `stager.loudnorm`.
- [x] Move cleanup utility under `stager.cli.clean`.
- [x] Move CLI entrypoint to `stager.cli.build` and update `./main`.
- [x] Use temporary top-level compatibility wrappers only during migration.
- [x] Remove compatibility wrappers once imports are package-based.
- [x] Run package-specific targeted tests after each package move.
- [x] Run `.venv/bin/python run_tests.py`.
- [x] Run `./main --help`.

## Phase 2: Add Cuemaster Manifest Domain Model

Target outcome: the app gets a structured data model independent of markdown formatting.

- [x] Create dataclasses for app export records, one primary class per new file.
- [x] Proposed files: `src/stager/playbook/app_manifest.py`, `src/stager/playbook/app_role.py`, `src/stager/playbook/app_line.py`, `src/stager/playbook/app_audio_asset.py`.
- [x] Keep Playbook dataclasses independent of `CueBuilder`, `PlayBuilder`, and MP4 chapter models.
- [x] Include `schema_version` in the manifest model.
- [x] Use stable ids based on existing `SegmentId` and `BlockId`.
- [x] Represent cue text separately from expected response text.
- [x] Represent display text separately from audio asset paths.
- [x] Represent required cue and response audio explicitly; do not emit rehearsable Playbook lines with missing audio.
- [x] Add JSON serialization via a class method or writer class, not ad hoc dict construction in the Stager CLI.
- [x] Add tests for JSON shape using a small in-memory `Play`.
- [x] Add tests for solo reading and dramatic reading reader metadata.
- [x] Add tests for inline directions and top-level directions.
- [x] Run targeted Cuemaster manifest tests.
- [x] Run full tests.

## Phase 3: Build Playbook Exporter

Target outcome: `build/<play>/app/manifest.json` can be generated by Stager and consumed by Cuemaster.

- [x] Create `src/stager/playbook/playbook_builder.py`.
- [x] Inject `Play`, `PathConfig`, and any audio-length helper.
- [x] Reuse shared play, block, segment, and audio path models directly rather than invoking legacy MP4 cue generation.
- [x] Build package directory at `build/<play>/app`.
- [x] Write `manifest.json` with paths relative to the Playbook root.
- [x] Decide whether to copy audio assets into `build/<play>/app/audio` or reference existing `build/<play>/audio/segments` paths.
- [x] Prefer copying or hard-linking assets for a self-contained package if practical.
- [x] Include segment durations without loading the same file repeatedly.
- [x] Fail on missing required role cue or response audio by default.
- [x] Support diagnostic mode only if defined in `planning/stager/missing_audio_policy.md`.
- [x] Add fixture tests that create tiny WAV files and assert manifest assets exist.
- [x] Add tests that missing required audio fails with a clear exception.
- [x] Add tests that relative paths resolve from `manifest.json`.
- [x] Run targeted tests.
- [x] Run full tests.

## Phase 4: Add Stager CLI Command For Playbook Export

Target outcome: the future Playbook is generated by an explicit Stager CLI command without bloating `src/stager/cli/build.py` further.

- [x] Add a `playbook` or `package-playbook` command in `src/stager/cli/build.py`.
- [x] Keep Typer code thin: parse options, build `PathConfig`, call `PlaybookBuilder`.
- [x] Support `--play/-p`.
- [x] Do not add `--role`; the current design exports complete Playbooks.
- [x] Do not add `--allow-missing-audio`; Playbook generation is strict by default.
- [x] Log generated manifest path using `paths.display_path()`.
- [x] Add Stager CLI-level tests if the existing suite has a Typer test pattern; otherwise test the service directly.
- [x] Run `./main --help` manually and confirm command appears.
- [x] Run `./main playbook --help` or the final command equivalent.
- [x] Run full tests.

## Phase 5: Enforce Missing Audio Policy

Target outcome: builds that produce user-consumable audio/Playbooks do not silently succeed with zero-length placeholders.

- [ ] Replace zero-length clip behavior in Playbook generation with exceptions.
- [ ] Review [play_plan_builder.py](../src/play_plan_builder.py) missing snippet handling.
- [ ] Decide whether audioplay should also fail by default or preserve current diagnostic behavior behind a flag.
- [ ] If changing audioplay behavior, add `allow_missing_audio` plumbing through the relevant builder/service.
- [ ] Add tests for missing role segment audio.
- [ ] Add tests for missing simultaneous segment audio.
- [ ] Add tests for missing callout audio when callouts are enabled.
- [ ] Add tests for missing announcer/Librivox snippets when Librivox is enabled.
- [ ] Run full tests.

## Phase 6: Extract Build Services From Stager CLI

Target outcome: Typer commands become thin Stager wrappers over reusable services.

- [ ] Create `TextArtifactBuilder`.
- [ ] Move `run_text`, `run_write_play`, `run_write_roles`, `run_write_callout_script`, and `run_write_announcer` behavior into the service.
- [ ] Keep backwards-compatible helper functions in `src/stager/cli/build.py` temporarily if tests or scripts import them.
- [ ] Create `SegmentBuildService`.
- [ ] Move `run_segments` behavior into the service.
- [ ] Create `TimingBuildService`.
- [ ] Move `run_generate_timings` behavior into the service.
- [ ] Create `AudioPlayBuildService`.
- [ ] Move `run_audioplay` behavior into the service.
- [ ] Create `CueBuildService`.
- [ ] Move `run_cues` behavior into the service.
- [ ] Ensure each service receives `PathConfig` explicitly.
- [ ] Ensure service classes use `logging.getLogger(__name__)`.
- [ ] Keep `src/stager/cli/build.py` focused on Typer/Stager option parsing and service invocation.
- [ ] Run targeted tests after each extracted service.
- [ ] Run full tests after all service extraction.

## Phase 7: Reduce Global Path State

Target outcome: Cuemaster/Playbook-oriented services and tests do not depend on import-time global play configuration.

- [ ] Audit remaining `paths.current()` usage.
- [ ] Replace `paths.current()` in newly extracted services with required `PathConfig` constructor arguments.
- [ ] Keep legacy aliases in `paths.py` only for existing compatibility.
- [ ] Avoid adding new imports of `BUILD_DIR`, `SEGMENTS_DIR`, `RECORDINGS_DIR`, or similar aliases.
- [ ] Consider changing `DEFAULT_PLAY_NAME = PlayConfig.load().play_id` to a function if import-time config becomes a test or app-packaging problem.
- [ ] Add tests that construct two `PathConfig` instances for different plays in the same process and verify no cross-contamination in Playbook export.
- [ ] Run full tests.

## Phase 8: Clean Library Output

Target outcome: reusable code does not print directly.

- [ ] Review remaining `print()` calls.
- [ ] Keep `typer.echo()` in Stager CLI code for deliberate user-facing output.
- [ ] Convert library `print()` calls to logging or returned strings.
- [ ] Update tests or add tests for returned summaries where needed.
- [ ] Review warning/error logging that should become exceptions under the missing-audio policy.
- [ ] Run full tests.

## Phase 9: Documentation And Developer Workflow

Target outcome: future work can resume without rediscovering conventions.

- [ ] Update `AGENTS.md` if new commands are added.
- [ ] Add Stager CLI examples for Playbook generation.
- [ ] Add a short `planning/stager/playbook_usage.md` or update an existing user-facing doc with generated Playbook layout.
- [ ] Document the test command for Playbook fixtures.
- [ ] Document any expected external dependencies for Playbook generation, such as ffmpeg if audio transcoding is used.
- [ ] Run `./main text` for the configured play if text output behavior changes.
- [ ] Run any new Playbook command against the configured play if fixture audio is available.

## Suggested Commit Slices

- [ ] Commit 1: design docs under `planning/`.
- [ ] Commit 2: `CueBuilder` correctness fix and tests.
- [ ] Commit 3: package boundaries and package-aligned unit tests.
- [ ] Commit 4: Cuemaster manifest dataclasses and JSON writer tests.
- [ ] Commit 5: Playbook builder and service tests.
- [ ] Commit 6: Stager CLI command for Playbook export.
- [ ] Commit 7: missing-audio policy enforcement.
- [ ] Commit 8: service extraction from `src/stager/cli/build.py`.
- [ ] Commit 9: path/global cleanup and print/logging cleanup.
- [ ] Commit 10: documentation updates.

## Resume Checklist

When resuming after interruption:

- [ ] Read this file.
- [ ] Check `git status --short`.
- [ ] Run the most relevant targeted test for the phase in progress.
- [ ] Run `.venv/bin/python run_tests.py` before moving to the next phase.
- [ ] Update completed checkboxes in this file.
- [ ] Add a short note below if the implementation differs from the design docs.

## Notes

- Use `.venv/bin/python`, not global Python.
- Use `./main` for normal Stager CLI runs.
- Keep generated `build/` artifacts out of commits unless there is a deliberate fixture update.
- Prefer small services with explicit `PathConfig` injection over new module-level helpers.
