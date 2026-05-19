# Quince Deployment

This document describes a practical deployment model for community theatre groups with limited time, technical support, and budget.

The recommended path is:

1. Actors use hosted LineRecorder and Cuemaster web apps.
2. Showrunners use Stager locally.
3. Recording Requests, recording packages, and Playbooks move as zip files.
4. Google Drive is used as shared storage and human workflow glue, not as the first version of the app backend.

This keeps the system explainable: actors receive a link to a web app and a package file, while showrunners keep control of the production source and build outputs.

## Goals

- Actors should not need to install software.
- Actors should be able to use the tools from a normal browser link.
- Actors should be able to return recordings as a single zip file.
- Showrunners should not need to manage servers, user accounts, OAuth credentials, or cloud storage APIs.
- Stager should remain local-first and file-based.
- The workflow should still work if a production uses email, Google Drive, Dropbox, USB sticks, or another file-sharing method.

## Hosted Actor Apps

LineRecorder and Cuemaster are good fits for static web hosting.

The actor-facing URLs can be simple Cloudflare-hosted app URLs:

```text
https://linerecorder.phil-surette.workers.dev/
https://cuemaster.phil-surette.workers.dev/
```

Deployment should be a static upload of each app's built `dist/` directory to its matching Cloudflare app:

```text
linerecorder/dist/ -> linerecorder app
cuemaster/dist/    -> cuemaster app
```

Both apps already have `build:static` scripts that run Vite with `--base=./`. That remains the right default for static hosting because asset URLs stay relative to each app directory.

## LineRecorder Web Workflow

LineRecorder should be deployed as a hosted static web app:

1. The actor opens the LineRecorder URL.
2. The actor imports a Recording Request zip from their computer.
3. LineRecorder stores the project and accepted takes locally in browser storage.
4. The actor records and reviews each requested line.
5. The actor exports one role recording zip.
6. The actor emails the zip or uploads it to the production's shared folder.

This model does not require accounts or server storage. The app must be served over HTTPS so browsers allow microphone capture.

### Saving To Downloads

A browser app cannot silently write to a user's Downloads folder. Browser security requires a user action.

LineRecorder can still make export easy:

- Generate the role recording package as a zip in the browser.
- Trigger a normal browser download using a generated object URL and an `<a download>` action.
- Use a predictable filename such as `<play-id>-<role>-recordings.zip`.
- Show a completion screen telling the actor which file was downloaded and where to send it.

Most browsers save this file to the user's Downloads folder unless the user has configured the browser to ask for a location.

An optional later enhancement is the File System Access API on Chromium browsers. That would let the user choose a destination explicitly and allow a nicer "save again" flow, but it should not be required because it is not universally supported.

The Web Share API can also be an optional convenience on supported devices, but the reliable baseline should remain "download a zip and send/upload it."

## Cuemaster Web Workflow

Cuemaster should also be deployed as a hosted static web app:

1. The actor opens the Cuemaster URL.
2. The actor imports a Playbook zip.
3. Cuemaster extracts and stores the Playbook locally.
4. The actor rehearses from local browser storage, including when offline after import.

For community theatre use, MP3 Playbooks are important because they reduce download size, import time, and browser storage pressure:

```sh
./main playbook --play <play_id> --audio-format mp3
```

Cuemaster should show clear import progress and clear storage errors. The app should not assume network access after a Playbook is imported.

## Google Drive Workflow

Google Drive should be used first as shared file storage, not as the app backend.

A practical folder layout is:

```text
Production Folder/
  01 Recording Requests/
  02 Actor Uploads/
  03 Playbooks/
  04 Archive/
```

Recommended workflow:

1. The showrunner builds Recording Request zips in Stager.
2. The showrunner uploads them to `01 Recording Requests`.
3. Actors download their request zip and import it into LineRecorder.
4. Actors export recording zips from LineRecorder.
5. Actors upload recording zips to `02 Actor Uploads` or email them.
6. The showrunner downloads and imports those zips into Stager.
7. The showrunner builds a Playbook zip and uploads it to `03 Playbooks`.
8. Actors download the Playbook zip and import it into Cuemaster.

This requires no Google API integration, no OAuth consent screen, no app verification, and no special permissions beyond normal Drive sharing.

### Direct Drive Integration

Direct Google Drive integration is possible but should be deferred.

A browser app can use Google Identity Services, the Google Picker, and the Drive API to open or upload files. That adds real support costs:

- Google Cloud project setup.
- OAuth consent configuration.
- Scope selection and possible app verification.
- Multiple-account confusion for actors.
- Workspace or school account restrictions.
- Failure modes that are harder to explain than file upload/download.

The first version should keep Drive optional and manual. Later, LineRecorder could add "Upload to Google Drive" and Cuemaster could add "Open from Google Drive" as convenience features without changing the file-based core workflow.

### Working Inside A Synced Drive Folder

Stager can probably be used inside a local Google Drive Desktop synced folder, but it should not depend on that.

Risks include:

- Partially synced zip files.
- Conflicting copies when two people edit or build at once.
- Large generated audio artifacts syncing during builds.
- Confusion between source files and generated files.

The safer recommendation is that Stager works in a local project folder and Drive is used for explicit intake and distribution packages. If a production stores the project in Drive Desktop anyway, only one showrunner should edit/build that play at a time.

## Stager Packaging

Stager is a Python command-line application. For showrunners, the packaging goal is an "easy enough" local app that does not require them to clone a repository or understand virtual environments.

The recommended packaging path is staged:

1. Add an installer-oriented CLI release for technical users.
2. Add a standalone app bundle for macOS and Windows using PyInstaller or an equivalent packager.
3. Keep ffmpeg as an external prerequisite instead of bundling it.
4. Add a small launcher or GUI later if the CLI remains too intimidating.

### ffmpeg Policy

The standalone Stager package should not bundle ffmpeg initially.

Instead, Stager should:

- Check for `ffmpeg` and `ffprobe` on startup for commands that need audio encoding or probing.
- Show a clear install message when they are missing.
- Document platform install steps.

This avoids licensing and redistribution questions, keeps the app bundle smaller, and makes packaging less fragile.

Example install guidance:

- macOS: install ffmpeg with Homebrew or a signed ffmpeg package.
- Windows: install ffmpeg from an approved distribution and add it to `PATH`.
- Linux: install ffmpeg from the system package manager.

### Standalone Bundle Shape

A standalone Stager bundle should provide:

- A `stager` executable or app launcher.
- The Python runtime and Stager dependencies.
- A first-run check for ffmpeg.
- A first-run check for writable production/build folders.
- A command reference or shortcut to common workflows.
- A sample project or import path for creating a new play folder.

The bundle can still operate on normal folders:

```text
my-production/
  plays/
    <play_id>/
      production.md
  build/
    <play_id>/
```

The important point is that generated Recording Request, recording import, audioplay, and Playbook outputs remain regular files that the showrunner can upload or email.

## Recommended First Release Shape

The first production-friendly release should have:

- Hosted Cuemaster at `https://cuemaster.phil-surette.workers.dev/`.
- Hosted LineRecorder at `https://linerecorder.phil-surette.workers.dev/`.
- LineRecorder export as a browser download zip.
- Cuemaster import from a local Playbook zip.
- A documented Google Drive folder workflow.
- A Stager local install path with explicit ffmpeg checks.
- A later milestone for standalone Stager bundles.

This path keeps the operational burden low while preserving local ownership of scripts and recordings.
