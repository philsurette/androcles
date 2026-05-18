# Quince Producer CLI Implementation Plan

This is a resumable implementation plan for the producer-first `quince` CLI described in [../quince_cli_design.md](../quince_cli_design.md).

The current Stager CLI remains the expert interface. This plan adds a friendlier command surface that reuses Stager services and makes multi-production work easier.

## Goals

- Add a `quince` console command focused on producer workflows.
- Resolve workspace and active play from the current directory when safe.
- Keep `./main` and `python -m stager.cli.build` stable for expert/legacy use.
- Move shared command behavior toward service classes instead of duplicating CLI logic.
- Provide structured status output for future GUI and editor integrations.

## Non-Goals

- Do not remove existing commands.
- Do not rename existing `./main` commands in this slice.
- Do not add a hosted backend.
- Do not implement a full GUI.

## Phase 1: Context Resolution

Create a small context-resolution layer used by the new producer CLI.

Checklist:

- [x] Add `QuinceContext` dataclass with workspace root, play id, play dir, build dir, selection source, and production source mode.
- [x] Add workspace root discovery from `--workspace`, `QUINCE_WORKSPACE`, `quince.yaml`, and existing repo layout.
- [x] Add play selection from `--play`, current directory under `plays/<play_id>`, current directory under `build/<play_id>`, `quince.yaml`, `play-config.yaml`, and single-play fallback.
- [x] Add clear errors for no workspace, no plays, unknown play, and ambiguous play selection.
- [x] Add `quince.yaml` parser/writer for `version` and `active_play`.
- [x] Add tests for cwd-sensitive selection from workspace root, play dir, nested play dir, build dir, explicit `--play`, and ambiguous multi-play root.

## Phase 2: Producer CLI Skeleton

Add the new CLI without changing existing expert command behavior.

Checklist:

- [x] Add `src/stager/cli/quince.py` Typer app.
- [x] Add a `quince` console script entry point.
- [x] Keep top-level help focused on producer workflows.
- [x] Add global `--play/-p`, `--workspace`, `--format`, and `--production-source` where appropriate.
- [x] Ensure `quince --help` and every subcommand `--help` work without initializing logging or requiring a valid play.
- [x] Add smoke tests for top-level help and subcommand help.

## Phase 3: Status, List, And Use

Make the first useful commands about orientation.

Checklist:

- [x] Implement `quince list` to show available productions under the workspace.
- [x] Implement `quince use <play_id>` to write workspace-local `quince.yaml`.
- [x] Implement `quince status` using `ProductionStatusService`.
- [x] Add JSON output alongside text/YAML for status.
- [x] Include context summary in status output: workspace root, selected play, and how it was selected.
- [x] Add tests for `list`, `use`, and `status` across multi-production fixtures.

## Phase 4: Next-Step Recommendations

Make the CLI answer "what should I do next?"

Checklist:

- [x] Add a `ProductionRecommendationService` or equivalent structured model.
- [x] Recommend publish when working `production.md` differs from the current published version.
- [x] Recommend cast setup when rehearsable roles are unassigned.
- [x] Recommend recording requests when roles are missing LineRecorder segment audio.
- [x] Recommend whole-role splitting when `recording: whole-role` roles have source audio but missing canonical segments.
- [x] Recommend receiving/importing recordings only as explanatory guidance, not as an automatic action.
- [x] Recommend Playbook rebuild when Playbook version is stale or blocking-only changes are present.
- [x] Implement `quince next`.
- [x] Add tests for recommendation priority and rendered command text.

## Phase 5: Publish And Changes

Wrap production publication in producer language.

Checklist:

- [x] Implement `quince changes` from production diff data.
- [x] Group changes as "needs recording", "blocking-only", "context-only", "added", "removed", and "id issue".
- [x] Implement `quince publish`.
- [x] Prompt for change summary when interactive and not provided.
- [x] Support `--dry-run`.
- [x] Support `--recording-requests` while skipping blocking-only updates.
- [x] Preserve expert id-update controls but explain them in producer-facing wording.
- [x] Add tests for clean publish, missing summary, blocking-only publish, speech-change publish, and id-reuse errors.

## Phase 6: Cast Helpers

Reduce hand-editing mistakes in `cast.yaml` without replacing the file.

Checklist:

- [x] Implement `quince cast show`.
- [x] Implement `quince cast check`.
- [x] Implement `quince cast assign <ROLE> <actor>`.
- [x] Preserve comments and formatting where practical; otherwise document that the helper rewrites `cast.yaml`.
- [x] Validate configured actors against actor ids.
- [x] Add tests for assigning existing roles, rejecting unknown roles, and rejecting malformed actor ids.

## Phase 7: Recording Workflows

Wrap request/import/splitting workflows in producer terms.

Checklist:

- [x] Implement `quince send-requests`.
- [x] Use cast assignments for actor-facing metadata when available.
- [x] Skip `recording: whole-role` roles by default.
- [x] Support `--role`, `--actor`, `--changed-only`, and `--missing-only`.
- [x] Implement `quince receive-recordings <package.zip>`.
- [x] Print the import transaction path and post-import role status.
- [x] Implement `quince split-recordings`.
- [x] Restrict split workflow to `recording: whole-role` roles unless explicitly overridden.
- [x] Add tests for LineRecorder role requests, changed-only requests, package import dispatch, and whole-role split dispatch.

## Phase 8: Audio And Output Builders

Add producer-facing wrappers over cleanup, voice, Playbook, and audioplay outputs.

Checklist:

- [x] Implement `quince prepare-audio --dry-run`.
- [x] Report verify, cleanup, and voice-profile readiness without doing destructive promotion.
- [x] Implement safe `quince prepare-audio --run` steps for analysis/rendering where unambiguous.
- [x] Implement `quince build-playbook`.
- [x] Warn or require confirmation when building a Playbook from working source.
- [x] Implement `quince build-audioplay`.
- [x] Report output paths, production version, and selected audio source.
- [x] Add tests for strict missing-audio failures and successful build wrappers with mocked builders.

## Phase 9: Documentation And Migration

Make the new CLI the documented default.

Checklist:

- [x] Update [../quince_production_guide.md](../quince_production_guide.md) to lead with `quince` commands.
- [x] Keep expert `./main` commands in an appendix or troubleshooting section.
- [x] Add examples for managing multiple productions from workspace root and from inside `plays/<play_id>/`.
- [x] Add a short migration note: "`./main` remains supported; `quince` is the producer workflow CLI."
- [x] Update `planning/README.md`.

## Acceptance Criteria

- [x] A producer can run `quince status` from the workspace root when one play or an active play is configured.
- [x] A producer can run `quince status` from inside `plays/<play_id>/` without passing `--play`.
- [x] A multi-production workspace fails with a clear play-selection message instead of silently choosing the wrong play.
- [x] `quince next` gives one concrete next action with a runnable command.
- [x] The new CLI does not break the existing expert CLI.
- [x] Help output works without a configured play or logging side effects.
- [x] Structured status output can be consumed by future web or editor UI work.
