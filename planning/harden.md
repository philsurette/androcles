# Codebase Hardening Plan

This plan prepares Stager, the current CLI codebase, for reliable Cuemaster Playbook generation. It is written as a resumable checklist: complete each item, commit in small logical chunks, and leave notes under the relevant section if work is paused.

## Goals

- Preserve the existing Stager CLI workflows for markdown, segment splitting, verification, timings, cues, and audioplay.
- Make cue generation correct, tested, and suitable as the foundation for an actor line-learning workflow.
- Introduce a stable Cuemaster-facing export boundary rather than requiring the mobile app to infer structure from markdown, spreadsheets, or MP4 chapter metadata.
- Reduce coupling in the Stager CLI so future Playbook packaging can reuse domain services directly.
- Make package builds fail on missing required audio unless explicitly running in a diagnostic mode.

## Non-Goals

- Do not build the iOS or Android app in this phase.
- Do not change the custom play text format unless a design doc explicitly identifies a required format change.
- Do not remove existing audio verification, Librivox, or markdown outputs.
- Do not require network access, downloaded Whisper models, or real recordings in normal tests.

## Current Findings To Address

- `CueBuilder` likely returns empty audio because helper methods receive an `AudioSegment` and use `+=`, which rebinds locally instead of mutating the caller's value.
- Missing segment audio is sometimes logged and represented as zero-length clips instead of failing the build.
- There is no versioned Cuemaster manifest or Playbook format.
- `src/build.py` is too large and mixes Typer/Stager CLI concerns with orchestration and domain behavior.
- `paths.py` still exposes import-time default play state and backwards-compatible global aliases.
- Some library-style modules still use `print()` instead of logging or caller-owned output.

## Phase 0: Design Docs First

Create these design documents before changing production behavior. Keep them short and concrete.

- [x] Create `planning/app_manifest.md`.
- [x] Document the intended consumer: Cuemaster, offline-first, per-role Playbook.
- [x] Define manifest versioning, e.g. `"schema_version": 1`.
- [x] Define Playbook layout, e.g. `build/<play>/app/manifest.json`, `build/<play>/app/audio/...`.
- [x] Define role payloads: role id, display name, reader, part list, cue/line sequence.
- [x] Define line item fields: block id, segment ids, speaker, cue text, response text, direction text, audio paths, duration ms, offsets if applicable.
- [x] Define how simultaneous lines are represented.
- [x] Define how narrator, caller, and announcer are represented or excluded for actor rehearsal.
- [x] Define whether Playbook paths are relative to the manifest.
- [x] Define compatibility behavior for missing optional audio versus missing required response audio.
- [x] Align `planning/cueline-design.md` with the Stager manifest and Playbook design.

- [ ] Create `planning/cue_generation.md`.
- [ ] Document current cue behavior: previous speech block as prompt, optional callout, cropped cue audio, response delay, expected response playback.
- [ ] Define desired cue behavior for first line in a part or scene.
- [ ] Define whether stage directions are prompts, context text, playable audio, or ignored.
- [ ] Define whether caller/announcer snippets are included in Cuemaster Playbooks.
- [ ] Define expected chapter or item boundaries for generated cue media.
- [ ] Define deterministic test fixtures for cue audio without using real recordings.

- [ ] Create `planning/service_boundaries.md`.
- [ ] Define domain services to extract from `src/build.py`.
- [ ] Proposed services: `TextArtifactBuilder`, `SegmentBuildService`, `TimingBuildService`, `AudioPlayBuildService`, `CueBuildService`, `PlaybookBuilder`.
- [ ] Define which services may call ffmpeg, pydub, Whisper, or Audacity.
- [ ] Define which services are pure enough for fast tests.
- [ ] Define Stager CLI ownership: Typer validates options and delegates to services; services raise exceptions.
- [ ] Define path/config ownership: all services receive `paths.PathConfig` and never rely on `paths.current()`.

- [ ] Create `planning/missing_audio_policy.md`.
- [ ] Define required versus optional audio categories.
- [ ] Required: role response segments used in Playbooks and audioplay.
- [ ] Required when enabled: callouts, announcer, narrator, Librivox preamble/epilog snippets.
- [ ] Optional or diagnostic: timing previews with missing audio placeholders, if still needed.
- [ ] Define Stager CLI flags for diagnostic mode, e.g. `--allow-missing-audio`.
- [ ] Define exact exception type or error message style for missing required audio.

## Phase 1: Fix CueBuilder Correctness

Target outcome: cue generation returns non-empty audio and correct chapter boundaries for roles with available segment audio.

- [ ] Add failing tests that reproduce the current `AudioSegment` accumulation issue.
- [ ] Use tiny generated WAV files in `tmp_path` fixtures so tests do not require real recordings.
- [ ] Test that `build_cues_for_role("A")` returns audio length greater than zero when role A has response audio.
- [ ] Test that cue chapters include both `CUE <role> <segment>` and `LINE <role> <segment>` when prompts are enabled and a previous speaker exists.
- [ ] Test that cue generation works when prompts are disabled.
- [ ] Test that first-line behavior matches `planning/cue_generation.md`.
- [ ] Refactor `CueBuilder` helpers to return updated audio and chapter data instead of trying to mutate `AudioSegment` parameters.
- [ ] Keep `CueBuilder` as a dataclass.
- [ ] Avoid adding defensive fallbacks; raise exceptions for missing required audio according to the policy design.
- [ ] Verify `run_cues()` still writes cue files through the Stager CLI.
- [ ] Run targeted tests: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_alignment_gaps.py`.
- [ ] Run full tests: `.venv/bin/python run_tests.py`.

## Phase 2: Add Cuemaster Manifest Domain Model

Target outcome: the app gets a structured data model independent of markdown formatting.

- [ ] Create dataclasses for app export records, one primary class per new file.
- [ ] Proposed files: `src/app_manifest.py`, `src/app_role.py`, `src/app_line.py`, `src/app_audio_asset.py`.
- [ ] Include `schema_version` in the manifest model.
- [ ] Use stable ids based on existing `SegmentId` and `BlockId`.
- [ ] Represent cue text separately from expected response text.
- [ ] Represent display text separately from audio asset paths.
- [ ] Represent missing optional audio explicitly if the policy allows optional assets.
- [ ] Add JSON serialization via a class method or writer class, not ad hoc dict construction in the Stager CLI.
- [ ] Add tests for JSON shape using a small in-memory `Play`.
- [ ] Add tests for solo reading and dramatic reading reader metadata.
- [ ] Add tests for inline directions and top-level directions.
- [ ] Run targeted Cuemaster manifest tests.
- [ ] Run full tests.

## Phase 3: Build Playbook Exporter

Target outcome: `build/<play>/app/manifest.json` can be generated by Stager and consumed by Cuemaster.

- [ ] Create `src/playbook_builder.py`.
- [ ] Inject `Play`, `PathConfig`, and any audio-length helper.
- [ ] Build package directory at `build/<play>/app`.
- [ ] Write `manifest.json` with paths relative to the Playbook root.
- [ ] Decide whether to copy audio assets into `build/<play>/app/audio` or reference existing `build/<play>/audio/segments` paths.
- [ ] Prefer copying or hard-linking assets for a self-contained package if practical.
- [ ] Include segment durations without loading the same file repeatedly.
- [ ] Fail on missing required role response audio by default.
- [ ] Support diagnostic mode only if defined in `planning/missing_audio_policy.md`.
- [ ] Add fixture tests that create tiny WAV files and assert manifest assets exist.
- [ ] Add tests that missing required audio fails with a clear exception.
- [ ] Add tests that relative paths resolve from `manifest.json`.
- [ ] Run targeted tests.
- [ ] Run full tests.

## Phase 4: Add Stager CLI Command For Playbook Export

Target outcome: the future Playbook is generated by an explicit Stager CLI command without bloating `src/build.py` further.

- [ ] Add a `playbook` or `package-playbook` command in `src/build.py`.
- [ ] Keep Typer code thin: parse options, build `PathConfig`, call `PlaybookBuilder`.
- [ ] Support `--play/-p`.
- [ ] Support `--role` if the design allows single-role exports.
- [ ] Support `--allow-missing-audio` only if the policy design keeps diagnostic mode.
- [ ] Log generated manifest path using `paths.display_path()`.
- [ ] Add Stager CLI-level tests if the existing suite has a Typer test pattern; otherwise test the service directly.
- [ ] Run `./main --help` manually and confirm command appears.
- [ ] Run `./main package-playbook --help` or the final command equivalent.
- [ ] Run full tests.

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
- [ ] Keep backwards-compatible helper functions in `src/build.py` temporarily if tests or scripts import them.
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
- [ ] Keep `src/build.py` focused on Typer/Stager option parsing and service invocation.
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
- [ ] Add a short `planning/playbook_usage.md` or update an existing user-facing doc with generated Playbook layout.
- [ ] Document the test command for Playbook fixtures.
- [ ] Document any expected external dependencies for Playbook generation, such as ffmpeg if audio transcoding is used.
- [ ] Run `./main text` for the configured play if text output behavior changes.
- [ ] Run any new Playbook command against the configured play if fixture audio is available.

## Suggested Commit Slices

- [ ] Commit 1: design docs under `planning/`.
- [ ] Commit 2: `CueBuilder` correctness fix and tests.
- [ ] Commit 3: Cuemaster manifest dataclasses and JSON writer tests.
- [ ] Commit 4: Playbook builder and service tests.
- [ ] Commit 5: Stager CLI command for Playbook export.
- [ ] Commit 6: missing-audio policy enforcement.
- [ ] Commit 7: service extraction from `src/build.py`.
- [ ] Commit 8: path/global cleanup and print/logging cleanup.
- [ ] Commit 9: documentation updates.

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
