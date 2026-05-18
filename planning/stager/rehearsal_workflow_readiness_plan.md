# Rehearsal Workflow Readiness Plan

This is a resumable implementation plan for making Quince practical as a real rehearsal tool: actors can practice from the current script and blocking, producers can keep the cast synchronized, and showrunners can see what must be rebuilt or redistributed.

The user-facing overview belongs in [../quince_production_guide.md](../quince_production_guide.md). Shared file contracts remain in [../specs/](../specs/). This plan covers implementation work.

## Goals

- Add a first-class cast configuration that connects actors, roles, Recording Requests, Playbooks, and voice profiles.
- Add a `production-status` command that shows whether the production is ready to send to actors.
- Improve Cuemaster's Playbook update experience so actors know when a package replaces an older script/blocking version.
- Make blocking-only changes a clear Playbook update workflow without triggering unnecessary re-recording.
- Preserve whole-role recording and splitting as an advanced producer path, while keeping LineRecorder as the default actor handoff path.

## Non-Goals

- Do not require a hosted backend, accounts, or sync service.
- Do not remove existing whole-role recording/splitting.
- Do not make Playbooks depend on legacy cue-file output.
- Do not add a full GUI production manager in this slice.

## Phase 1: Cast Configuration

Add `plays/<play_id>/cast.yaml` as the producer-authored cast source of truth.

Recommended shape:

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
- [ ] Validate configured roles against the loaded `Play`.
- [ ] Validate configured actors against voice-profile actor ids when voice profiles are enabled.
- [ ] Let Recording Request generation use cast assignments to include actor-facing metadata.
- [ ] Let voice rendering use cast assignments as the default `--voice-actor` where unambiguous.
- [ ] Document cast config in the production guide.

## Phase 2: Production Status Command

Add `./main production-status --play <play_id>` as the showrunner's readiness dashboard.

It should answer:

- Which production version is current?
- Does the working `production.md` differ from the current published version?
- Which rehearsable roles exist?
- Which roles are assigned in `cast.yaml`?
- Which recording path is expected for each role: LineRecorder or whole-role split?
- How many expected response segments exist for each role?
- How many canonical segment files are present?
- Are cleanup, voice-profile, Playbook, and audioplay outputs current enough to distribute?
- Is the next likely action publish, record, verify, cleanup, render voices, or build Playbook?

Checklist:

- [x] Add a basic `production-status` service.
- [x] Report current published version, working version, and unpublished-change flag.
- [x] Report per-role cast assignment and basic segment audio coverage.
- [x] Add CLI text output.
- [ ] Add `--format yaml` for automation.
- [ ] Report stale recordings by content hash, not only missing files.
- [ ] Report cleanup review status.
- [ ] Report voice-profile rendered-audio status.
- [ ] Report Playbook build metadata and whether it matches the current production version.
- [ ] Report whole-role source recording presence for `recording: whole-role` roles.
- [ ] Add targeted rebuild recommendations.

## Phase 3: Cuemaster Playbook Update UX

Cuemaster must make script/blocking freshness visible to actors.

Current issue: importing a Playbook with the same play id replaces the local one directly. That is simple, but it hides whether the actor just imported a new production version, a new build of the same version, or an older package.

Checklist:

- [ ] Show production version and published timestamp in the Library row.
- [ ] Show an "unpublished/working source" warning for non-published Playbooks.
- [ ] Before replacing an installed Playbook, compare old/new production metadata.
- [ ] Confirm replacement when the new package is older, from a different production fork, or from a working source.
- [ ] Preserve role selection, session cursor, timing attempts, and bookmarks when replacing with a successor version where line ids still match.
- [ ] Show "what changed" after import when the Playbook carries production change metadata.
- [ ] Add tests for same-version rebuild, newer version replacement, older version warning, and fork warning.

## Phase 4: Blocking-Only Update Workflow

Blocking changes should update actor rehearsal material without creating unnecessary recording work.

Checklist:

- [ ] Ensure publication reports classify blocking-only changes separately from speech changes.
- [ ] Ensure `publish-production --recording-requests` skips blocking-only changes.
- [ ] Include blocking-change summaries in `production-status`.
- [ ] Include blocking changes in Playbook build metadata or a companion changelog.
- [ ] Surface changed blocking clearly in Cuemaster after Playbook replacement.
- [ ] Add tests that blocking-only publication creates no Recording Requests but does mark Playbook rebuild needed.

## Phase 5: Whole-Role Recording Path Preservation

Whole-role recording and splitting remains supported as an advanced producer workflow.

Checklist:

- [ ] Represent whole-role recording choice in `cast.yaml`.
- [ ] Make `production-status` report missing full-role source recordings separately from missing segment files.
- [ ] Keep `./main segments` as the convergence point from whole-role source audio into canonical segment audio.
- [ ] Ensure all downstream steps consume canonical segments identically regardless of whether audio came from LineRecorder or splitting.
- [ ] Document when to use LineRecorder versus whole-role recording.

## Acceptance Criteria

- [ ] A producer can run one status command and understand what is blocking actor distribution.
- [ ] A cast file can drive role ownership without duplicating role/actor choices in multiple places.
- [ ] Actors can see which production version is installed in Cuemaster.
- [ ] Importing a replacement Playbook is explicit when version lineage is risky.
- [ ] Blocking-only updates produce updated rehearsal material without unnecessary recording requests.
- [ ] Whole-role recording remains available but does not create a second downstream pipeline.
