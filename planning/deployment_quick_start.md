# Quince Deployment Quick Start

This guide is for a production using hosted Quince actor apps and local Stager builds.

Use these files for the normal handoffs:

| File | Built By | Used By | Purpose |
|---|---|---|---|
| Recording Request zip | Stager | LineRecorder | Tells an actor which lines to record. |
| Role recordings zip | LineRecorder | Stager | Contains accepted actor recordings to import. |
| Playbook zip | Stager | Cuemaster | Contains rehearsal audio and manifest data for actors. |

## Actor: Record Lines With LineRecorder

Open:

```text
https://linerecorder.phil-surette.workers.dev/
```

Steps:

1. Download the Recording Request zip from the production email or shared folder.
2. Open LineRecorder.
3. Choose **Import Request** and select the Recording Request zip.
4. Start the microphone and record each requested line.
5. Listen back and accept the usable take for each line.
6. Choose **Export Recordings**.
7. Send the downloaded role recordings zip to the showrunner.

The exported zip usually goes to the browser's Downloads folder. Some browsers ask where to save it. LineRecorder cannot silently choose the Downloads folder because browsers require the user to control file downloads.

If the actor needs to send a partial recording package, that is allowed. The export will say how many requested lines are still missing.

## Actor: Rehearse With Cuemaster

Open:

```text
https://cuemaster.phil-surette.workers.dev/
```

Steps:

1. Download the Playbook zip from the production email or shared folder.
2. Open Cuemaster.
3. Import the Playbook zip.
4. Select the role to rehearse.
5. Rehearse from the imported Playbook.

After import, Cuemaster stores the Playbook locally in the browser. The actor should not need to download the same Playbook again unless the showrunner sends an updated version.

## Showrunner: Suggested Google Drive Layout

Create one shared production folder:

```text
Production Folder/
  01 Recording Requests/
  02 Actor Uploads/
  03 Playbooks/
  04 Archive/
```

Use the folders this way:

- Put Stager-generated Recording Request zips in `01 Recording Requests/`.
- Ask actors to upload LineRecorder exports to `02 Actor Uploads/`.
- Put current Cuemaster Playbook zips in `03 Playbooks/`.
- Move old requests, uploads, and Playbooks to `04 Archive/` when they are replaced.

Google Drive is shared storage for files, not a required Quince backend. Actors can also send files by email or another file-sharing service.

## Showrunner: Build And Collect Recordings

Create a Recording Request for each role:

```sh
./main recording-request --play <play_id> --role <ROLE>
```

Upload the resulting zip to `01 Recording Requests/` or send it directly to the actor.

When the actor returns a role recordings zip, import it:

```sh
./main recording-import --play <play_id> path/to/<ROLE>-role-recordings.zip
```

Then run the normal verification and Playbook build workflow:

```sh
./main verify --play <play_id>
./main check-recording --play <play_id>
./main cues --play <play_id>
./main playbook --play <play_id> --audio-format mp3
```

Upload the Playbook zip from `build/<play_id>/<play_id>.playbook.zip` to `03 Playbooks/`.

## Showrunner: Publish The Hosted Apps

Build each static app:

```sh
cd cuemaster
npm run build:static
cd ../linerecorder
npm run build:static
```

Upload the built folders to their Cloudflare apps:

```text
cuemaster/dist/     -> cuemaster
linerecorder/dist/  -> linerecorder
```

In Cloudflare, use **Workers & Pages**, choose the app, and upload the matching `dist/` folder. The hosted apps still do not contain production data; actors import Recording Request and Playbook zips separately from local files.

For command-line deployment after the Cloudflare Pages projects exist, set a Cloudflare API token and account id, then run:

```sh
CLOUDFLARE_ACCOUNT_ID=<account-id> CLOUDFLARE_API_TOKEN=<token> scripts/deploy_webapps_to_cloudflare.sh
```

## Troubleshooting

**The browser asks where to save the recording zip.**
This is normal. The browser controls downloads. Save the zip somewhere easy to find, then email or upload it.

**The actor cannot find the exported zip.**
Check the browser's Downloads list first. The filename includes the play id, role id, and `role-recordings`.

**The microphone does not work.**
Use the hosted HTTPS app URL, not an insecure local copy. Check browser microphone permissions and the selected input device.

**Cuemaster says storage is unavailable or full.**
Try a current Chrome, Edge, Firefox, or Safari release outside private browsing. Make sure browser storage is allowed for the Cuemaster site. MP3 Playbooks are smaller and should be preferred for distribution.

**An actor is rehearsing an old version.**
Ask the actor to import the newest Playbook zip from `03 Playbooks/`. Cuemaster can replace a compatible older Playbook while preserving local rehearsal progress. Archive old Playbooks so there is only one obvious current package.

**Stager rejects Playbook generation.**
Playbook generation is strict. Verify that every rehearsable role line has required cue audio and response audio.
