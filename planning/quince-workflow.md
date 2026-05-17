# Quince Production Workflow

This document describes the user-facing production workflow for Quince: preparing a locked production script, collecting actor recordings, building Playbooks for Cuemaster rehearsal, and repeating the cycle when the script or recordings change.

Quince is the suite. The tools in this workflow are:

- **ScriptWright**, which creates and updates `production.md`.
- **Stager**, which builds text, audio, Recording Requests, audioplays, and Playbooks.
- **LineRecorder**, which actors use to record requested lines and export recording packages.
- **Cuemaster**, which actors use to rehearse from Playbooks.

The file contracts are defined elsewhere. The Playbook manifest source of truth is [specs/playbook_manifest.md](specs/playbook_manifest.md). The Recording Request and recording package source of truth is [specs/recording_package_manifest.md](specs/recording_package_manifest.md).

## Workflow Summary

1. Create or update `plays/<play_id>/production.md`.
2. Lock or reconcile the production script with ScriptWright.
3. Publish the production script to create a structured production version.
4. Build Stager text artifacts for review and production use.
5. Collect or import line recordings for each rehearsable role.
6. Split, verify, and fix segment audio.
7. Build cue audio and a strict Playbook.
8. Distribute the Playbook to actors for Cuemaster rehearsal.
9. When script text or recordings change, publish a successor version, issue targeted Recording Requests, import new recordings, and build a replacement Playbook.

## 1. Create The Production Script

Each play has a working directory under `plays/<play_id>/`. The canonical build source is:

```text
plays/<play_id>/production.md
```

ScriptWright creates a locked `production.md` from supported source formats, including the legacy `play.txt` source:

```sh
./main scriptwright lock --play <play_id>
```

A locked production script has stable production ids for the script units that downstream tools need to track. Once Stager is building from `production.md`, normal build commands should treat missing, draft, or idless production scripts as errors.

When the source script changes after locking, reconcile the changes instead of throwing away the existing ids:

```sh
./main scriptwright reconcile --play <play_id>
```

The goal is that actors, recording packages, Playbooks, and future re-recording requests can all refer to the same stable line and segment identities across revisions.

Publish the locked script when it is ready to become the production baseline:

```sh
./main publish-production --play <play_id> --change-summary "Initial published manuscript."
```

Publishing creates a structured version such as `1@k9f4p2x8m1qd`, stores the snapshot under `build/<play_id>/production-history/`, and back-writes the current version metadata into `plays/<play_id>/production.md`. Normal build commands copy that metadata into generated packages; they do not create new production versions or mutate the manuscript.

## 2. Build Review Artifacts

After the production script is locked, build the normal text artifacts:

```sh
./main text --play <play_id>
```

These artifacts are useful for production review and for catching obvious script or role problems before recording starts. They are generated outputs under `build/<play_id>/`; the editable source remains `plays/<play_id>/production.md`.

## 3. Request Actor Recordings

For an initial cast recording pass, create one Recording Request per rehearsable role:

```sh
./main recording-request --play <play_id> --role <ROLE>
```

Stager writes a local zip package for LineRecorder. Send that package to the actor or reader assigned to the role.

Recording Requests are intentionally text-first work orders. They include the role's recording items, production ids, Stager segment ids, display text, cue/context text where available, and expected output paths. They do not need to include audio assets. This keeps requests small and keeps audio collection separate from rehearsal Playbook distribution.

Recording Requests also carry the production version they were created from. LineRecorder preserves that metadata when exporting role recording packages so Stager can warn if an actor returns recordings from a different published script version.

The actor imports the request in LineRecorder, records and reviews each line, accepts the usable takes, and exports a role recording package. LineRecorder may export a complete package or an explicitly partial package.

Import the returned recording package into Stager:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip
```

Stager imports accepted WAV files into the play's segment-audio area and writes an import transaction. If the import needs to be reversed, use the transaction file:

```sh
./main recording-import-undo --play <play_id> path/to/transaction.json
```

## 4. Prepare And Verify Audio

Stager's audio build works from segment recordings. If recordings are being managed through full-role source files or Audacity exports, split them into per-segment files:

```sh
./main segments --play <play_id>
```

Then verify that split audio matches the production script closely enough for the next build:

```sh
./main verify --play <play_id>
./main check-recording --play <play_id>
```

Use deeper audio verification when transcription-based checks are appropriate for the production:

```sh
./main verify-audio --play <play_id>
```

Fix missing, extra, stale, or badly split recordings before building a Playbook. Playbook generation is strict: every rehearsable non-meta role line must have required cue audio and response audio.

## 5. Build Cues

Cuemaster rehearsal depends on cue audio as well as response audio. Build cue files from the prepared segment audio:

```sh
./main cues --play <play_id>
```

Cue selection rules and cue-window behavior are described in [cuemaster/cue_generation.md](cuemaster/cue_generation.md). This workflow only describes when cue assets are produced.

## 6. Build The Playbook

Build the Cuemaster Playbook after text, segments, and cue audio are ready:

```sh
./main playbook --play <play_id>
```

For a smaller distribution package, build with MP3 audio:

```sh
./main playbook --play <play_id> --audio-format mp3
```

Stager writes both an unpacked inspection directory and a distributable zip:

```text
build/<play_id>/app/
build/<play_id>/<play_id>.playbook.zip
```

Distribute the `.playbook.zip` file to actors. Actors import it into Cuemaster, select their role, and rehearse with the cue and response audio packaged in the Playbook.

## Audioplay Output

An audioplay can be built as its own production artifact:

```sh
./main audioplay --play <play_id>
```

It is best thought of as a sibling output of the same prepared script and segment audio, not as the source for Playbook creation. The Playbook builder uses the shared play and segment assets directly so Cuemaster does not depend on MP4 chapter metadata or audiobook assembly.

A production may build an audioplay for review, publication, or quality control before or after building the Playbook. When `audioplay` is run with preparation enabled, it may also refresh text and segment artifacts that the Playbook workflow needs.

## 7. Distribute To Actors

Actors receive different package types for different jobs:

- Send a **Recording Request** when an actor needs to record or re-record lines in LineRecorder.
- Send a **Playbook** when an actor needs to rehearse in Cuemaster.
- Do not use a Playbook as a recording package and do not use a Recording Request as a rehearsal package.

This separation matters because Playbooks are complete rehearsal artifacts with required cue and response audio, while Recording Requests are work orders that may cover a full role or only selected lines.

## 8. Update The Production

Production changes usually fall into one of three categories:

- The script text changed.
- A recording is missing, stale, technically bad, or director-rejected.
- The Playbook settings changed, such as the requested audio format.

For script text changes, update or reconcile `production.md` first:

```sh
./main scriptwright reconcile --play <play_id>
./main text --play <play_id>
```

Then identify the affected roles and recording items. For targeted re-recording, create a selected Recording Request:

Publish a successor production version before creating release re-recording requests:

```sh
./main publish-production --play <play_id> --change-summary "Describe the script change."
```

If the working file was edited from an out-of-date published version or local history contains a fork, Stager stops and reports the lineage problem instead of assigning a new version.

```sh
./main recording-request --play <play_id> --role <ROLE> --item <PRODUCTION_SEGMENT_ID> --reason script_changed
```

Repeat `--item` for multiple selected items:

```sh
./main recording-request --play <play_id> --role <ROLE> --item <ID_1> --item <ID_2> --reason director_request
```

The actor records only the requested items in LineRecorder and exports a new role recording package. Import it into Stager:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip
```

Re-run the audio preparation steps needed by the change:

```sh
./main verify --play <play_id>
./main check-recording --play <play_id>
./main cues --play <play_id>
./main playbook --play <play_id> --audio-format mp3
```

Distribute the new Playbook zip to actors. Cuemaster should treat it as a replacement version of the rehearsal package for that play.

## Operational Notes

- Keep `production.md` as the canonical editable script. Generated files under `build/<play_id>/` can be rebuilt.
- Keep actor-facing output pipelines separate. LineRecorder collects recordings; Cuemaster rehearses from Playbooks; audioplay generation assembles publication or review audio.
- Prefer selected Recording Requests for corrections. Full-role requests are useful for initial recording or when a role needs to be completely redone.
- Partial LineRecorder exports are allowed, but a complete Playbook is not partial. Stager must fail Playbook generation if required cue or response audio is missing.
- Use `--play <play_id>` consistently when working on more than one production.
