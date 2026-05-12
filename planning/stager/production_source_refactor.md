# Stager Production Source Refactor Plan

## Goal

Refactor Stager so normal build commands consume locked `production.md` instead of parsing `play.txt` directly.

This milestone should not change Cuemaster or LineRecorder contracts beyond what is required to keep existing builds working. Full production-id manifest adoption is tracked in [production_id_adoption.md](production_id_adoption.md).

## Source Docs

- [../specs/script_text_format.md](../specs/script_text_format.md)
- [../specs/production_script_ids.md](../specs/production_script_ids.md)
- [scriptwright.md](scriptwright.md)
- [production_pipeline.md](production_pipeline.md)

## Design Decisions

- Stager build services read locked `production.md`.
- Stager build services reject draft or idless `production.md`.
- Stager does not silently fall back to `play.txt`.
- Source-format parsing remains behind ScriptWright.
- Existing Stager models may be adapted or wrapped during the transition, but `production.md` is the source of truth.

## Milestone 1: Production Model Loading

- [x] Add a production-script loader for locked `production.md`.
- [x] Validate required metadata.
- [x] Validate every addressable script line has a production id.
- [x] Parse headings, descriptions, directions, role lines, simultaneous lines, and inline directions.
- [ ] Preserve source locations for diagnostics.
- [x] Add parser/loader tests with valid and invalid locked `production.md`.

## Milestone 2: Model Adapter

- [x] Decide whether to adapt locked production scripts into existing `Play`/`Part`/`Block`/`Segment` models or introduce a parallel production model.
- [x] Preserve enough block/segment identity for existing audio workflows during transition.
- [x] Ensure role extraction works from locked `production.md`.
- [x] Ensure narrator/context extraction works from headings, descriptions, and directions.
- [x] Add unit tests for model conversion.

## Milestone 3: CLI Source Selection

- [ ] Update normal build commands to load locked `production.md`.
- [ ] Reject missing `production.md` with a diagnostic directing users to ScriptWright.
- [ ] Reject `production_ids: draft` for normal builds.
- [ ] Avoid silent fallback to `play.txt`.
- [ ] Decide whether any diagnostic/dev command may still accept `play.txt` explicitly.
- [ ] Add CLI tests for missing, draft, and locked sources.

## Milestone 4: Existing Artifact Builds

- [x] Verify `./main text` from locked `production.md`.
- [x] Verify role markdown generation from locked `production.md`.
- [ ] Verify segment planning from locked `production.md`.
- [ ] Verify audiobook/audioplay generation still works or explicitly document any temporary unsupported command.
- [ ] Verify Playbook generation still works with current manifest shape before production-id adoption.
- [ ] Add regression tests around generated text artifacts.

## Milestone 5: Cleanup

- [ ] Move current `play.txt` parsing behind ScriptWright-only APIs.
- [ ] Update `src/format.md` to point to `planning/specs/script_text_format.md`.
- [ ] Update user-facing docs to explain the ScriptWright then Stager workflow.
- [ ] Update AGENTS.md if new CLI commands become sticky project workflow.

## Acceptance Criteria

- [ ] Normal Stager builds consume locked `production.md`.
- [ ] Normal Stager builds reject missing or draft `production.md`.
- [ ] Normal Stager builds do not silently read `play.txt`.
- [ ] Existing core build outputs can be generated from locked `production.md`.
- [ ] Tests cover loader, model conversion, CLI source selection, and at least one core artifact build.
