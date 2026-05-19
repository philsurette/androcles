# Deployment Implementation Plan

This plan tracks the work needed to make Quince usable by a community theatre group with hosted actor web apps and an easy local Stager install.

## Milestone 1: LineRecorder Download Export

Goal: actors can export accepted recordings as a zip that lands in their normal browser download flow.

- [x] Confirm current LineRecorder export creates a `role_recordings` zip Blob and triggers a browser download from the existing **Export Recordings** button.
- [x] Extract the inline `downloadBlob` helper into a browser download service, for example `DownloadService`, that accepts `{ blob, filename }` and triggers an `<a download>` click from a user action.
- [x] Keep the same download behavior for hosted HTTPS, localhost development, and local static file use; the browser controls the final download destination in all cases.
- [x] Improve filenames so they include play id, role id, package type, and a timestamp or request id instead of only `<ROLE>.role-recordings.zip`.
- [x] Add an export completion state that shows the downloaded filename and tells the actor to email or upload that zip to the showrunner.
- [x] Preserve local accepted takes after export so an actor can retry export without re-recording.
- [x] Add unit tests for filename generation and download-service invocation.
- [x] Add a Playwright export smoke test using a browser download expectation.
- [x] Document that browsers cannot silently write to Downloads and that the download location is controlled by the user's browser settings.

Deferred enhancements:

- [ ] Add optional Web Share API support where available.
- [ ] Add optional Chromium File System Access API support for "Save as..." or repeat-save workflows.

## Milestone 2: Cuemaster Local Playbook Import Polish

Goal: actors can import a Playbook zip from disk and understand import/storage failures.

Detailed plan: [cuemaster/cloudflare_import_flow_plan.md](cuemaster/cloudflare_import_flow_plan.md).

- [x] Confirm Playbook import works from a local file input when the app is hosted on Cloudflare.
- [x] Ensure import progress is visible for large MP3 Playbooks.
- [x] Ensure extraction work stays off the main UI path for large packages.
- [x] Add clear storage error handling for quota, private browsing, blocked IndexedDB, and unsupported browser cases.
- [x] Add user-facing import success text showing the play title and available roles.
- [x] Add a browser compatibility note favoring current Chrome, Edge, Firefox, and Safari versions.
- [x] Add Playwright coverage for importing a built fixture Playbook from the hosted subdirectory base path.

## Milestone 3: Static Cloudflare Builds

Goal: both actor apps can be built as static artifacts and uploaded to Cloudflare.

Current app status:

- `cuemaster/package.json` has `build:static`, which runs `vite build --base=./`.
- `linerecorder/package.json` has `build:static`, which runs `vite build --base=./`.
- Cloudflare Workers & Pages can host each app from its built `dist/` directory.

Implementation tasks:

- [x] Add a repo script that builds Cuemaster with `npm run build:static` from `cuemaster/`.
- [x] Add a repo script that builds LineRecorder with `npm run build:static` from `linerecorder/`.
- [x] Add or keep a local publish/build script that produces these deployable directories:

  ```text
  cuemaster/dist/
  linerecorder/dist/
  ```

- [x] Build each app's `dist/` contents for static hosting.
- [x] Document the Cloudflare-hosted app URLs for actors.
- [x] Add local build steps that make the deployable `dist/` folders explicit before upload.
- [x] Add instructions for manually uploading or deploying the built `dist/` folders to Cloudflare.
- [x] Verify the deployed paths locally with Vite preview or a static file server pointed at each `dist/` folder.
- [x] Verify that app asset paths are relative and do not assume site root.

Current command shape:

```sh
cd cuemaster && npm run build:static
cd ../linerecorder && npm run build:static
```

Upload each resulting `dist/` folder through Cloudflare Workers & Pages, or deploy both apps from the command line:

```sh
mkdir -p ~/.config/quince
chmod 700 ~/.config/quince
$EDITOR ~/.config/quince/cloudflare-deploy.env
chmod 600 ~/.config/quince/cloudflare-deploy.env
scripts/deploy_webapps_to_cloudflare.sh
```

The local env file must contain `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`; it may also set `CUEMASTER_PROJECT_NAME` or `LINERECORDER_PROJECT_NAME` if the Cloudflare Pages project names differ from the local folder names.

The script builds each app with `build:static`, computes a content hash for the `dist/` folder, and skips deployment when the artifact matches the last successful deploy recorded in `.deploy/cloudflare/`. Use `--force` only when you intentionally want to create a Cloudflare deployment for an unchanged artifact.

## Milestone 4: User-Facing Deployment Docs

Goal: showrunners and actors have simple instructions.

- [x] Add an actor-facing LineRecorder quick start:
  - open app URL,
  - import Recording Request zip,
  - record lines,
  - export recording zip,
  - email/upload the zip.
- [x] Add an actor-facing Cuemaster quick start:
  - open app URL,
  - import Playbook zip,
  - choose role,
  - rehearse.
- [x] Add a showrunner Google Drive folder template:

  ```text
  01 Recording Requests/
  02 Actor Uploads/
  03 Playbooks/
  04 Archive/
  ```

- [x] Add wording that Google Drive is shared storage, not a required backend.
- [x] Add troubleshooting notes for microphone permissions, browser downloads, storage quota, and stale Playbooks.
- [x] Add a "which file do I send?" table for Recording Requests, recording packages, and Playbooks.

## Milestone 5: Stager ffmpeg Checks

Goal: packaged Stager gives clear feedback when audio prerequisites are missing.

- [x] Identify commands that require ffmpeg or ffprobe:
  - `segments`,
  - `cues`,
  - `audioplay`,
  - `playbook --audio-format mp3`,
  - audio verification commands that probe or transcode audio.
- [x] Add a small dependency-check service that uses `shutil.which("ffmpeg")` and `shutil.which("ffprobe")`.
- [x] Inject or call the check from command entry points that need those tools.
- [x] Keep commands that only parse text or write manifests from requiring ffmpeg.
- [x] Show platform-specific install guidance when the tools are missing.
- [x] Add tests that missing ffmpeg produces a clear exception or CLI diagnostic for audio commands.
- [x] Add tests that text-only commands do not require ffmpeg.

## Milestone 6: Stager Python Packaging

Goal: make Stager installable without cloning the repository manually.

- [x] Add or complete `pyproject.toml` packaging metadata for the Stager CLI.
- [x] Expose a console script entry point such as `stager = stager.cli.build:main`.
- [x] Confirm package data needed at runtime is included.
- [ ] Verify install into a fresh virtualenv.
- [x] Verify `pipx install` or equivalent local wheel install.
- [x] Add a smoke test that runs:

  ```sh
  stager --help
  stager scriptwright lock --help
  stager playbook --help
  ```

- [x] Document install/update/uninstall steps for technical showrunners.

## Milestone 7: Standalone Stager Bundle

Goal: produce a macOS and/or Windows Stager bundle that includes Python and dependencies but depends on installed ffmpeg.

Recommended starting tool: PyInstaller.

- [x] Add a PyInstaller spec or build script for the Stager CLI.
- [x] Exclude ffmpeg and ffprobe from the bundle.
- [x] Confirm pydub and audio helpers use system `ffmpeg` from `PATH`.
- [x] Add a first-run or command-run ffmpeg check with clear install instructions.
- [x] Build a macOS command-line bundle first.
- [x] Test the bundle outside the repository checkout.
- [ ] Test with a minimal sample play folder.
- [ ] Add a Windows build after macOS packaging is stable.
- [x] Document Gatekeeper, code-signing, and notarization needs for macOS distribution.
- [x] Document Windows SmartScreen/signing implications.
- [x] Decide whether to ship a CLI-only bundle or add a small launcher app for common workflows.

Acceptance criteria:

- [x] A showrunner can download the bundle, install ffmpeg separately, and run `stager --help`.
- [ ] Stager can build text artifacts from a sample `production.md`.
- [x] Stager gives a clear ffmpeg message before an audio command fails obscurely.
- [ ] Stager can build or reject a Playbook with clear required-audio diagnostics.

## Milestone 8: Optional Google Drive Integration

Goal: add Drive conveniences only after manual file workflow is proven.

Do not start here. Revisit after real productions have used manual Drive folders.

Possible later work:

- [ ] Add "Open from Google Drive" to Cuemaster using Google Picker.
- [ ] Add "Upload recording zip to Google Drive" to LineRecorder.
- [ ] Add showrunner-configured folder ids for a production.
- [ ] Add OAuth setup docs and support boundaries.
- [ ] Keep local file import/export as the primary supported path.

## Release Sequence

Recommended order:

1. LineRecorder download export.
2. Static Cloudflare publishing for both apps.
3. Actor/showrunner quick-start docs.
4. Cuemaster import polish for large MP3 Playbooks.
5. Stager ffmpeg checks.
6. Stager Python package install.
7. Stager standalone bundle.
8. Optional Drive API integration.

This order gets actors onto browser-based tools quickly while keeping Stager packaging work scoped and testable.
