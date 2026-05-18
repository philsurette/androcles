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

Stager's audio build works from canonical segment recordings. If recordings are being managed through full-role source files or Audacity exports, split them into per-segment files:

```sh
./main segments --play <play_id>
```

LineRecorder imports and whole-role splitting converge at the same output path:

```text
build/<play_id>/audio/segments/<ROLE>/<segment_id>.wav
```

Downstream verification, cleanup, voice rendering, Playbook generation, cue generation, and audioplay builds consume that canonical segment layer. Keep `./main segments` as the only whole-role splitting path; do not add a parallel full-role-only downstream build path.

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

## 5. Clean Up Recordings

Audio cleanup is optional, but when cleanup output exists Stager can use it automatically for Playbook and audioplay builds. Cleanup is for recording-quality repair such as light denoising, click cleanup, de-essing, boundary review, and loudness normalization. It is separate from creative voice effects.

Run the doctor command first when setting up a machine:

```sh
./main audio-cleanup doctor --play <play_id>
```

Then analyze the current segment audio:

```sh
./main audio-cleanup analyze --play <play_id>
```

The analysis report is written under:

```text
build/<play_id>/audio/cleanup_analysis/
```

Render cleaned audio into generated cleanup artifacts:

```sh
./main audio-cleanup render --play <play_id>
```

This writes cleaned segment files, batch manifests, and a review report under:

```text
build/<play_id>/audio/cleaned/
```

Generated cleanup output does not overwrite canonical segment audio. The default Playbook and audioplay audio source is `auto`: if no cleanup review exists, Stager uses canonical segment audio; if a complete cleanup review exists, Stager uses reviewed cleaned audio; if a review exists but is incomplete or stale, Stager fails instead of silently mixing cleaned and canonical segments.

Force a specific audio source when needed:

```sh
./main playbook --play <play_id> --audio-source canonical
./main playbook --play <play_id> --audio-source cleaned
./main audioplay --play <play_id> --audio-source canonical
./main audioplay --play <play_id> --audio-source cleaned
```

Promote cleaned output into canonical segment storage only after review:

```sh
./main audio-cleanup promote --play <play_id> --confirm
```

Promotion writes a transaction with backups under `build/<play_id>/audio/cleaned/promotions/`. Promotion is never automatic.

Examples:

- For generally noisy recordings, start with the default flow: `audio-cleanup analyze`, then `audio-cleanup render`, then listen through `audioplay --audio-source cleaned`.
- For click-heavy recordings, add or select a profile with medium declicking in `plays/<play_id>/audio_cleanup.yaml`, then render with `--profile <profile_name>` for a focused pass.
- For floor-noise-backed denoising, capture room tone in LineRecorder before recording or whenever the room changes, import the package, then run analysis and render. Stager associates each segment with the applicable room-tone sample from the LineRecorder import metadata.

LineRecorder room-tone capture and recording-package metadata are described in [linerecorder/floor_noise_reduction_plan.md](linerecorder/floor_noise_reduction_plan.md).

## 6. Render Voice Profiles

Voice profiles are optional creative effects for actor/role characterization, such as brighter or deeper voices, reverb, or stylized gender-presentation shifts. They are separate from audio cleanup. Voice-profile rendering never overwrites canonical segment audio or LineRecorder recording packages.

Define profiles in:

```text
plays/<play_id>/voice_profiles.yaml
```

Check FFmpeg support:

```sh
./main voice-profiles doctor --play <play_id>
```

Analyze accepted role recordings when you want suggested observed tempo and rough pitch values:

```sh
./main voice-analyze --play <play_id> --actor phil --role MEGAERA
```

The analysis report is written under:

```text
build/<play_id>/audio/voice_analysis/
```

Analysis output is a suggestion. It does not rewrite `voice_profiles.yaml`.

Render voice-profile audio:

```sh
./main voice-render --play <play_id>
./main voice-render --play <play_id> --role MEGAERA --actor phil
```

Rendered voice audio is generated under:

```text
build/<play_id>/audio/rendered/
```

Use `--audio-source canonical`, `--audio-source cleaned`, or the default `auto` to choose whether voice effects are rendered from canonical segment audio or reviewed cleaned audio.

## 7. Build Cues

Cuemaster rehearsal depends on cue audio as well as response audio. Build cue files from the prepared segment audio:

```sh
./main cues --play <play_id>
```

Cue selection rules and cue-window behavior are described in [cuemaster/cue_generation.md](cuemaster/cue_generation.md). This workflow only describes when cue assets are produced.

## 8. Build The Playbook

Build the Cuemaster Playbook after text, segments, and cue audio are ready:

```sh
./main playbook --play <play_id>
```

For a smaller distribution package, build with MP3 audio:

```sh
./main playbook --play <play_id> --audio-format mp3
```

Build with voice-profile audio when a production wants Cuemaster response and cue assets to use rendered role voices:

```sh
./main playbook --play <play_id> --voice-profiles
./main playbook --play <play_id> --voice-profiles --voice-actor phil
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

To review rendered role voices in the assembled audioplay:

```sh
./main audioplay --play <play_id> --voice-profiles
```

It is best thought of as a sibling output of the same prepared script and segment audio, not as the source for Playbook creation. The Playbook builder uses the shared play and segment assets directly so Cuemaster does not depend on MP4 chapter metadata or audiobook assembly.

A production may build an audioplay for review, publication, or quality control before or after building the Playbook. When `audioplay` is run with preparation enabled, it may also refresh text and segment artifacts that the Playbook workflow needs.

## 9. Distribute To Actors

Actors receive different package types for different jobs:

- Send a **Recording Request** when an actor needs to record or re-record lines in LineRecorder.
- Send a **Playbook** when an actor needs to rehearse in Cuemaster.
- Do not use a Playbook as a recording package and do not use a Recording Request as a rehearsal package.

This separation matters because Playbooks are complete rehearsal artifacts with required cue and response audio, while Recording Requests are work orders that may cover a full role or only selected lines.

## 9. Update The Production

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
