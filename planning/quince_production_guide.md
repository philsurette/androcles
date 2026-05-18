# Producing A Play With Quince

This guide describes the showrunner-facing workflow for producing a play with Quince, from the first `production.md` through Recording Requests, returned actor recordings, cleanup, voice profiles, Playbooks, audioplays, and later script revisions.

Quince is the overall production suite. In the current workflow:

- **ScriptWright** creates and reconciles locked `production.md` files.
- **Stager** builds packages, imports recordings, cleans audio, renders voice profiles, and produces Playbooks and audioplays.
- **LineRecorder** is the actor-facing recording tool for Recording Requests.
- **Cuemaster** is the actor-facing rehearsal app for Playbooks.

This document is operational. File contracts live in the shared specs:

- Recording Request and recording package contract: [specs/recording_package_manifest.md](specs/recording_package_manifest.md)
- Playbook contract: [specs/playbook_manifest.md](specs/playbook_manifest.md)
- Production and package versioning: [specs/versioning.md](specs/versioning.md)
- Audio cleanup design: [specs/audio_cleanup.md](specs/audio_cleanup.md)
- Voice profile design: [specs/voice_profiles.md](specs/voice_profiles.md)

## Production Directory

Each play lives under:

```text
plays/<play_id>/
```

The canonical Stager build source is:

```text
plays/<play_id>/production.md
```

Generated artifacts are written under:

```text
build/<play_id>/
```

Normal build commands should consume `production.md`; they should not create new production versions or mutate the manuscript. Publishing is the explicit step that assigns a new structured production version.

## End-To-End Workflow

The typical production loop is:

1. Create or update `plays/<play_id>/production.md`.
2. Lock or reconcile the production with ScriptWright.
3. Publish the production to assign a structured version.
4. Build review text artifacts.
5. Create Recording Requests for actors.
6. Actors record in LineRecorder and return recording packages.
7. Import returned recordings into Stager.
8. Verify segment coverage and text/audio alignment.
9. Optionally clean recordings.
10. Optionally configure and render voice profiles.
11. Optionally build legacy cue files for general-purpose audio players.
12. Build a Playbook for Cuemaster.
13. Build an audioplay for review or release.
14. Repeat the loop when script text, recordings, cleanup, or voice choices change.

## 1. Create The Initial Production

Start with a play directory:

```text
plays/<play_id>/
```

If the play starts from a supported source such as the legacy `play.txt` format, create a locked `production.md`:

```sh
./main scriptwright lock --play <play_id>
```

The locked production file contains stable production ids. Those ids are what let Stager, Recording Requests, LineRecorder exports, Playbooks, and future re-recording requests continue to refer to the same script units across revisions.

If you edit the source script after locking, reconcile rather than throwing away ids:

```sh
./main scriptwright reconcile --play <play_id>
```

Use `production.md` as the showrunner-edited manuscript once the production has moved into Stager. Keep edits intentional: changing spoken text can make existing recordings stale and may require new Recording Requests.

## 2. Publish A Production Version

When `production.md` is ready to become the baseline for recording or rehearsal, publish it:

```sh
./main publish-production --play <play_id> --change-summary "Initial published manuscript."
```

Publishing:

- allocates a structured production version such as `1@k9f4p2x8m1qd`,
- writes the version metadata back into `plays/<play_id>/production.md`,
- stores a snapshot under `build/<play_id>/production-history/`,
- gives Recording Requests and Playbooks a stable production version to reference.

The change summary should be short and useful to a future producer, for example:

```text
Initial published manuscript.
```

For later revisions:

```sh
./main production-diff --play <play_id>
./main publish-production --play <play_id> --change-summary "Cut two MEGAERA lines and revised Act II entrance."
```

If Stager reports that the working production is based on an older published version, stop and resolve the lineage issue before publishing. Two producers editing from the same parent version can create a fork; the structured production version exists to make that visible.

Useful history commands:

```sh
./main production-history --play <play_id>
./main restore-production --play <play_id> <version>
```

## 3. Build Text Artifacts For Review

Build text artifacts after locking or publishing:

```sh
./main text --play <play_id>
```

These artifacts help review role files, narrator/caller/announcer output, and production formatting. They are generated output; edit `plays/<play_id>/production.md`, then rebuild.

## 4. Assign Actors To Roles

At the production level, keep cast assignment in:

```text
plays/<play_id>/cast.yaml
```

This file connects roles to actors, the expected recording path, and optional voice-profile ids.

Example:

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

Use `recording: linerecorder` for the normal actor-facing package workflow. Use `recording: whole-role` when the producer records or imports a full-role audio file and uses Stager splitting. Both paths converge into the same canonical segment audio before verification, cleanup, Playbook, and audioplay builds.

Common cases:

- One actor reads one role: create one Recording Request for that role.
- One actor reads multiple roles: send one request per role, or coordinate multiple role packages with that actor.
- Multiple actors may read the same role at different times: use actor-specific voice profiles and select the actor explicitly when rendering.

If a role can be recorded by more than one actor, use clear actor names consistently in `voice_profiles.yaml` and command options. For example:

```sh
./main voice-render --play <play_id> --role MEGAERA --actor phil
./main playbook --play <play_id> --voice-profiles --voice-actor phil
```

Check cast and recording readiness at any point:

```sh
./main production-status --play <play_id>
```

## 5. Send Recording Requests

Create a Recording Request for each role that needs actor audio:

```sh
./main recording-request --play <play_id> --role <ROLE>
```

For a selected re-recording request:

```sh
./main recording-request --play <play_id> --role <ROLE> --item <ITEM_ID> --reason director_request
```

Repeat `--item` for multiple targeted items:

```sh
./main recording-request --play <play_id> --role <ROLE> --item <ID_1> --item <ID_2> --reason script_changed
```

Add actor-facing notes when useful:

```sh
./main recording-request --play <play_id> --role <ROLE> --notes "Please keep the tempo brisk and leave a beat before the final phrase."
```

Send the generated zip to the actor. The actor imports it into LineRecorder, records requested lines, accepts usable takes, records room tone when the room changes, and exports a recording package.

Recording Requests are work orders, not rehearsal packages. They include text and identifiers needed for recording. Playbooks are separate rehearsal packages with cue and response audio.

## 6. Import Returned Recordings

When an actor returns a LineRecorder recording package, import it:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip
```

Stager imports accepted segment WAV files into the play's segment area and writes an import transaction manifest. Keep the transaction path from the command output.

Undo an import if needed:

```sh
./main recording-import-undo --play <play_id> path/to/transaction.json
```

If the LineRecorder package contains room-tone recordings, Stager can use them later during audio cleanup. Multiple room-tone recordings are useful when the actor records in more than one session or room.

Import-time repair options exist for specific cases:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip --denoise
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip --trim-silence
```

Prefer the normal import first unless you know the package needs import-time repair. The richer cleanup workflow is non-destructive and easier to review.

## 7. Verify Recording Coverage

After importing recordings, verify coverage and alignment:

```sh
./main verify --play <play_id>
./main check-recording --play <play_id>
```

Use transcription-backed verification when appropriate:

```sh
./main verify-audio --play <play_id>
```

Fix missing, stale, or incorrect recordings before building a final Playbook. Playbook generation is strict: every rehearsable non-meta role line must have required cue audio and response audio.

If recordings are still managed from full-role audio files or Audacity exports, split them into segments:

```sh
./main segments --play <play_id>
```

LineRecorder packages already contain segment-aware recordings, so the import flow is usually the cleaner path for actor-recorded lines.

## 8. Clean Up Audio

Audio cleanup is optional and non-destructive. Use it for recording-quality repair: denoise, declick, de-ess, light gating, boundary review, and loudness normalization. Do not use cleanup for character voices; that is the voice-profile layer.

Check FFmpeg support:

```sh
./main audio-cleanup doctor --play <play_id>
```

Plan the cleanup pass:

```sh
./main audio-cleanup plan --play <play_id>
```

Analyze current segment audio:

```sh
./main audio-cleanup analyze --play <play_id>
```

Render cleaned audio:

```sh
./main audio-cleanup render --play <play_id>
```

Cleanup output is generated under:

```text
build/<play_id>/audio/cleaned/
```

It does not overwrite canonical segment audio. By default, Playbook and audioplay builds use `--audio-source auto`: reviewed cleaned audio is used when complete and current; otherwise canonical audio is used. If a cleanup review exists but is stale or incomplete, Stager should fail rather than silently mixing sources.

Force a source when reviewing:

```sh
./main playbook --play <play_id> --audio-source canonical
./main playbook --play <play_id> --audio-source cleaned
./main audioplay --play <play_id> --audio-source canonical
./main audioplay --play <play_id> --audio-source cleaned
```

Promote cleaned audio only after listening and review:

```sh
./main audio-cleanup promote --play <play_id> --confirm
```

Promotion is the step that replaces canonical segment audio with reviewed cleaned output. It writes backups and a transaction under the cleanup output area.

## 9. Configure Voice Profiles

Voice profiles are optional, creative, non-destructive transforms. They are for characterization: higher or deeper voices, brighter or darker tone, subtle gender-presentation shifts, reverb, ghostly voices, godlike voices, or other role-specific effects.

Voice profiles live in:

```text
plays/<play_id>/voice_profiles.yaml
```

Use voice profiles after canonical recordings exist and, if applicable, after cleanup has been rendered. Voice rendering can consume canonical audio or reviewed cleaned audio.

Check FFmpeg support:

```sh
./main voice-profiles doctor --play <play_id>
```

Analyze an actor-role recording set for suggested observed tempo and rough pitch values:

```sh
./main voice-analyze --play <play_id> --actor <actor_name> --role <ROLE>
```

The analysis report is written under:

```text
build/<play_id>/audio/voice_analysis/
```

Analysis is advisory. It does not rewrite `voice_profiles.yaml`. Use it to decide whether a pitch shift can safely be linked with speed or must preserve the actor's recorded tempo.

A minimal profile file has three conceptual parts:

- actor baselines,
- role targets,
- actor-role cast profiles.

Example:

```yaml
version: 1

actors:
  phil:
    baseline:
      pitch_center_hz: 115

role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
      preset: female_bright_subtle
      tempo_policy:
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.08
        min_confidence: 0.75
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true

observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: 178
    confidence: 0.9
    source: analysis

cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
```

Render voice-profile audio:

```sh
./main voice-render --play <play_id>
./main voice-render --play <play_id> --role MEGAERA --actor phil
```

Render from a specific source layer:

```sh
./main voice-render --play <play_id> --audio-source canonical
./main voice-render --play <play_id> --audio-source cleaned
```

Generated voice audio is written under:

```text
build/<play_id>/audio/rendered/
```

It does not overwrite canonical or cleaned segment audio.

## 10. Tweak Voice Profiles

Voice-profile tuning is iterative:

1. Start with a built-in preset or a small explicit transform.
2. Render one role or actor-role pair.
3. Listen in isolation and in the assembled audioplay.
4. Adjust pitch, EQ, compression, reverb, or strategy.
5. Re-render and review.

Useful render commands:

```sh
./main voice-render --play <play_id> --role <ROLE> --actor <actor_name>
./main audioplay --play <play_id> --voice-profiles --voice-actor <actor_name>
./main playbook --play <play_id> --voice-profiles --voice-actor <actor_name>
```

Guidelines:

- Do not use voice profiles to fix noise, mouth clicks, or loudness problems. Use audio cleanup first.
- Do not normalize an actor's tempo just because it is different from another actor's tempo.
- Use tempo analysis only to decide whether linked pitch/speed is safe for a given actor-role transform.
- Keep transforms modest when possible. Large pitch shifts without formant-aware tooling can sound artificial.
- If two actors record the same role, define actor-specific cast profiles and select the actor explicitly during rendering/builds.

## 11. Optional Legacy Cue Audio

Build legacy cue audio files when you want standalone cue files for general-purpose audio players:

```sh
./main cues --play <play_id>
```

This is separate from Cuemaster Playbook packaging. Playbook generation builds required cue and response assets directly from the shared play model and selected segment audio; it must not depend on legacy `CueBuilder` output or MP4 chapter metadata.

Cuemaster cue-selection behavior is described in [cuemaster/cue_generation.md](cuemaster/cue_generation.md).

## 12. Build A Playbook

Build a Cuemaster Playbook:

```sh
./main playbook --play <play_id>
```

Build a smaller MP3 Playbook:

```sh
./main playbook --play <play_id> --audio-format mp3
```

Build using reviewed cleaned audio when available:

```sh
./main playbook --play <play_id> --audio-source auto
```

Build using voice-profile rendered audio:

```sh
./main playbook --play <play_id> --voice-profiles
./main playbook --play <play_id> --voice-profiles --voice-actor <actor_name>
```

Stager writes:

```text
build/<play_id>/app/
build/<play_id>/<play_id>.playbook.zip
```

Send the `.playbook.zip` to actors for Cuemaster rehearsal.

## 13. Build An Audioplay

Build an assembled audioplay for review or release:

```sh
./main audioplay --play <play_id>
```

Review cleaned audio:

```sh
./main audioplay --play <play_id> --audio-source cleaned
```

Review rendered voice profiles:

```sh
./main audioplay --play <play_id> --voice-profiles
./main audioplay --play <play_id> --voice-profiles --voice-actor <actor_name>
```

The audioplay is a sibling artifact of the Playbook, not the source for Playbook generation. Playbooks use the shared play model and segment assets directly.

## 14. Revise The Production

When the manuscript changes:

1. Edit `plays/<play_id>/production.md`.
2. Review the diff.
3. Publish a new production version.
4. Generate targeted Recording Requests for changed spoken lines.
5. Import returned recordings.
6. Re-run verification, cleanup, voice rendering, cues, Playbook, and audioplay as needed.

Recommended command sequence:

```sh
./main production-diff --play <play_id>
./main publish-production --play <play_id> --change-summary "Describe the change."
./main text --play <play_id>
```

If you want Stager to generate Recording Requests for changed and added role lines during publication:

```sh
./main publish-production --play <play_id> --recording-requests --change-summary "Describe the change."
```

For manual targeted requests:

```sh
./main recording-request --play <play_id> --role <ROLE> --item <ITEM_ID> --reason script_changed
```

If publishing recommends production-id updates because spoken text changed under reused ids, review the recommendations. When they make sense:

```sh
./main publish-production --play <play_id> --apply-id-updates --change-summary "Describe the change."
```

Avoid `--allow-id-reuse` unless you are deliberately keeping changed text under the same ids and understand the downstream recording implications.

## 15. Decide What Must Be Rebuilt

Use this as a practical rebuild checklist.

When `production.md` text changes:

- publish a new production version,
- rebuild text artifacts,
- create targeted Recording Requests for changed spoken lines,
- import new recordings,
- verify,
- rebuild Playbook and audioplay.

When only recordings change:

- import the new recording package,
- verify,
- rerun cleanup if using cleaned audio,
- rerender voice profiles if using voice profiles,
- rebuild Playbook and audioplay.

When only cleanup settings change:

- rerun cleanup analysis/render,
- review cleaned output,
- rebuild Playbook and audioplay with `--audio-source auto` or `cleaned`,
- rerender voice profiles if they consume cleaned audio.

When only voice-profile settings change:

- rerun `voice-render`,
- rebuild Playbook or audioplay with `--voice-profiles`.

When only Cuemaster packaging choices change:

- rebuild Playbook with the desired options, such as `--audio-format mp3`.

## 16. Package Types To Send To Actors

Send the right package for the job:

- **Recording Request zip**: actor records or re-records lines in LineRecorder.
- **Recording package zip**: actor returns accepted LineRecorder takes to the producer.
- **Playbook zip**: actor rehearses in Cuemaster.

Do not use a Playbook as a recording request. Do not use a Recording Request as a rehearsal package.

## 17. Troubleshooting Checklist

If Recording Requests do not match the current script:

- run `./main production-diff --play <play_id>`,
- publish the current manuscript if needed,
- rebuild the Recording Request.

If imports warn about production versions:

- check whether the actor recorded against an older Recording Request,
- decide whether the returned takes still apply,
- issue a new targeted request if the text changed.

If Playbook generation fails for missing audio:

- run `verify` and `check-recording`,
- import or re-record missing segments,
- confirm the selected canonical, cleaned, or rendered segment audio exists,
- confirm meta roles are not being treated as rehearsable roles unexpectedly.

If cleaned audio is not being used:

- check whether `audio-cleanup render` completed,
- check whether the cleanup review is current,
- use `--audio-source cleaned` to force a clear failure when reviewed cleaned audio is unavailable.

If voice-profile audio is not being used:

- run `voice-profiles doctor`,
- run `voice-render`,
- build with `--voice-profiles`,
- pass `--voice-actor` when more than one actor profile can match the same role.

If a progress indicator looks incomplete but the command succeeded:

- rerun after the progress reporter fix is present,
- check the command output and generated artifact path before rerunning expensive audio work.

## Recommended First Production Pass

For a first complete pass on a new play:

```sh
./main scriptwright lock --play <play_id>
./main publish-production --play <play_id> --change-summary "Initial published manuscript."
./main text --play <play_id>
./main recording-request --play <play_id> --role <ROLE>
```

After actors return recordings:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-recordings.zip
./main verify --play <play_id>
./main check-recording --play <play_id>
./main audio-cleanup doctor --play <play_id>
./main audio-cleanup analyze --play <play_id>
./main audio-cleanup render --play <play_id>
./main playbook --play <play_id> --audio-format mp3
./main audioplay --play <play_id>
```

When the production wants creative role voices:

```sh
./main voice-profiles doctor --play <play_id>
./main voice-analyze --play <play_id> --actor <actor_name> --role <ROLE>
./main voice-render --play <play_id> --role <ROLE> --actor <actor_name>
./main audioplay --play <play_id> --voice-profiles --voice-actor <actor_name>
./main playbook --play <play_id> --voice-profiles --voice-actor <actor_name>
```
