# Rehearsal Workflow Readiness Plan

Status: refreshed after blocking MVP, audio cleanup, voice profiles, and the producer `quince` CLI landed. This plan now treats `ProductionStatusService` as the readiness data layer, `./main production-status` as the expert/status API, `quince status` as the producer-facing summary, and `quince next` as the next-action recommender.

The user-facing overview belongs in [../quince_production_guide.md](../quince_production_guide.md). Shared file contracts remain in [../specs/](../specs/). This plan covers implementation work.

## Goals

- Make one status model answer whether a production is ready to send to actors.
- Let `quince next` recommend the next highest-priority producer action from that status model.
- Keep cast assignment, recording freshness, cleanup review state, voice-profile render state, Playbook freshness, and blocking-only updates visible in one place.
- Preserve whole-role recording and splitting as an advanced producer path, while keeping LineRecorder as the default actor handoff path.

## Non-Goals

- Do not require a hosted backend, accounts, or sync service.
- Do not remove existing whole-role recording/splitting.
- Do not make Playbooks depend on legacy cue-file output.
- Do not add a full GUI production manager in this slice.
- Do not run expensive audio analysis or rendering from a status command.

## Phase 1: Cast Configuration

`plays/<play_id>/cast.yaml` is the producer-authored cast source of truth.

Implemented shape:

```yaml
version: 1
actors:
  phil:
    display_name: Phil
    email: phil@example.com
roles:
  MEGAERA:
    actor: phil
    recording: linerecorder
    voice_profile: phil@MEGAERA
  ANDROCLES:
    actor: phil
    recording: whole-role
```

Checklist:

- [x] Add parser/dataclasses for `cast.yaml`.
- [x] Treat missing `cast.yaml` as an empty config.
- [x] Validate unknown top-level version and malformed actor/role entries.
- [x] Expose role assignment lookup by role id.
- [x] Validate configured roles against the loaded `Play`.
- [x] Add producer `quince cast` helpers that reduce YAML mistakes.
- [x] Validate configured actor ids against `voice_profiles.yaml` when cast roles reference voice profiles.
- [x] Validate configured `voice_profile` ids against known voice cast profiles.
- [x] Let Recording Request generation use cast assignments to include actor-facing metadata.
- [x] Let voice rendering use cast assignments as the default `--voice-actor` where unambiguous.
- [x] Ensure [../quince_production_guide.md](../quince_production_guide.md) stays aligned with the implemented cast fields.

## Phase 2: Production Status Data Model

`./main production-status --play <play_id>` is the expert readiness dashboard and `quince status` should present the same facts in producer language.

It should answer:

- Which production version is current?
- Does the working `production.md` differ from the current published version?
- Which rehearsable roles exist?
- Which roles are assigned in `cast.yaml`?
- Which recording path is expected for each role: LineRecorder or whole-role split?
- How many expected response segments exist for each role?
- How many canonical segment files are present?
- Are any imported recordings stale because their saved content hashes no longer match the current production text?
- Is the cleanup review missing, incomplete, or current?
- Is voice-profile rendered audio missing or current for configured cast profiles?
- Are Playbook and audioplay outputs current enough to distribute?
- Is the next likely action publish, cast, record, verify, cleanup, render voices, build Playbook, or distribute?

Checklist:

- [x] Add a basic `production-status` service.
- [x] Report current published version, working version, and unpublished-change flag.
- [x] Report per-role cast assignment and basic segment audio coverage.
- [x] Add CLI text output.
- [x] Add `--format yaml` for automation.
- [x] Report Playbook build metadata and whether it matches the current production version.
- [x] Report whole-role source recording presence for `recording: whole-role` roles.
- [x] Report blocking-only changes that require a Playbook rebuild.
- [x] Report stale imported recordings by content hash, not only missing files.
- [x] Report cleanup review coverage and warnings/fallback counts.
- [x] Report voice-profile rendered-audio coverage for configured profiles.
- [x] Report audioplay build freshness.
- [x] Add status tests for stale recordings, cleanup review, voice renders, and recommendations.

## Phase 3: Targeted Recommendations

`quince next` already exists and uses `ProductionRecommendationService`, but it currently reasons over a small subset of readiness signals.

Checklist:

- [x] Recommend publish when `production.md` has unpublished changes.
- [x] Recommend cast work when roles are unassigned.
- [x] Recommend whole-role source recording when a whole-role role has no source file.
- [x] Recommend recording requests/imports when canonical segment audio is missing.
- [x] Recommend Playbook rebuild when the Playbook is missing or stale against the published production.
- [x] Recommend re-recording or re-import when imported segment files are stale by content hash.
- [x] Recommend cleanup render/review when cleanup is configured or review exists but is incomplete.
- [x] Recommend voice-profile render when configured rendered audio is missing or stale.
- [x] Recommend Playbook rebuild for blocking-only changes even when speech audio is current.
- [x] Recommend audioplay rebuild when audioplay output is stale or missing.
- [x] Include the reason and command in both `quince next` and any status summary.

## Phase 4: Cuemaster Playbook Update UX

Cuemaster must make script/blocking freshness visible to actors.

Checklist:

- [x] Show production version/source in the Library row.
- [x] Show an "unpublished/working source" warning for non-published Playbooks.
- [x] Before replacing an installed Playbook, compare old/new production metadata.
- [x] Confirm replacement when the new package is older, from a different production fork, or from a working source.
- [x] Preserve role selection, session cursor, timing attempts, and bookmarks when replacing with a successor version where line ids still match.
- [x] Show "what changed" after import when the Playbook carries production change metadata.
- [x] Add tests for same-version rebuild, newer version replacement, older version warning, and fork warning.

## Phase 5: Blocking-Only Update Workflow

Blocking changes should update actor rehearsal material without creating unnecessary recording work.

Checklist:

- [x] Ensure publication reports classify blocking-only changes separately from speech changes.
- [x] Ensure `publish-production --recording-requests` skips blocking-only changes.
- [x] Include blocking-change summaries in `production-status`.
- [x] Include blocking changes in Playbook build metadata or a companion changelog.
- [x] Surface changed blocking clearly in Cuemaster after Playbook replacement.
- [x] Add tests that blocking-only publication creates no Recording Requests but does mark Playbook rebuild needed.

## Phase 6: Whole-Role Recording Path Preservation

Whole-role recording and splitting remains supported as an advanced producer workflow.

Checklist:

- [x] Represent whole-role recording choice in `cast.yaml`.
- [x] Make `production-status` report missing full-role source recordings separately from missing segment files.
- [x] Keep `./main segments` as the convergence point from whole-role source audio into canonical segment audio.
- [x] Ensure all downstream steps consume canonical segments identically regardless of whether audio came from LineRecorder or splitting.
- [x] Document when to use LineRecorder versus whole-role recording.

## Acceptance Criteria

- [x] A producer can run `quince status` and understand what blocks actor distribution.
- [x] A producer can run `quince next` and get a specific next action with a concrete command.
- [x] A cast file can drive role ownership without duplicating role/actor choices in multiple places.
- [x] Status distinguishes missing recordings from stale imported recordings.
- [x] Status distinguishes canonical audio, cleanup review audio, and voice-profile rendered audio readiness.
- [x] Actors can see which production version is installed in Cuemaster.
- [x] Importing a replacement Playbook is explicit when version lineage is risky.
- [x] Blocking-only updates produce updated rehearsal material without unnecessary recording requests.
- [x] Whole-role recording remains available but does not create a second downstream pipeline.
