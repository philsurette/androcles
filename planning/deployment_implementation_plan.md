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

- [ ] Confirm Playbook import works from a local file input when the app is hosted from a GitHub Pages subdirectory.
- [ ] Ensure import progress is visible for large MP3 Playbooks.
- [ ] Ensure extraction work stays off the main UI path for large packages.
- [ ] Add clear storage error handling for quota, private browsing, blocked IndexedDB, and unsupported browser cases.
- [ ] Add user-facing import success text showing the play title and available roles.
- [ ] Add a browser compatibility note favoring current Chrome, Edge, Firefox, and Safari versions.
- [ ] Add Playwright coverage for importing a built fixture Playbook from the hosted subdirectory base path.

## Milestone 3: Static GitHub Pages Builds

Goal: both actor apps can be built and copied into `../philsurette.github.io`.

Current app status:

- `cuemaster/package.json` has `build:static`, which runs `vite build --base=./`.
- `linerecorder/package.json` has `build:static`, which runs `vite build --base=./`.
- `../philsurette.github.io` is a simple static repository and can host subdirectories directly.

Implementation tasks:

- [x] Add a repo script that builds Cuemaster with `npm run build:static` from `cuemaster/`.
- [x] Add a repo script that builds LineRecorder with `npm run build:static` from `linerecorder/`.
- [x] Add a publish script that removes and recreates only these target directories:

  ```text
  ../philsurette.github.io/cuemaster/
  ../philsurette.github.io/linerecorder/
  ```

- [x] Copy each app's `dist/` contents into its matching target directory.
- [x] Add or update `../philsurette.github.io/index.md` links for the hosted apps.
- [x] Keep the publish script from touching unrelated files such as `dayafter.html` and `otherlondon.html`.
- [x] Add a dry-run mode that prints source and destination paths before copying.
- [x] Add instructions for manually reviewing the sibling repo diff before committing the GitHub Pages update.
- [x] Verify the deployed paths locally with a static file server pointed at `../philsurette.github.io`.
- [x] Verify that app asset paths are relative and do not assume site root.

Suggested command shape:

```sh
./scripts/publish_webapps_to_pages.sh --dry-run
./scripts/publish_webapps_to_pages.sh
```

The script should fail if the sibling repo is missing, dirty in the target directories, or if either app build fails.

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

- [ ] Add a PyInstaller spec or build script for the Stager CLI.
- [ ] Exclude ffmpeg and ffprobe from the bundle.
- [ ] Confirm pydub and audio helpers use system `ffmpeg` from `PATH`.
- [ ] Add a first-run or command-run ffmpeg check with clear install instructions.
- [ ] Build a macOS command-line bundle first.
- [ ] Test the bundle outside the repository checkout.
- [ ] Test with a minimal sample play folder.
- [ ] Add a Windows build after macOS packaging is stable.
- [ ] Document Gatekeeper, code-signing, and notarization needs for macOS distribution.
- [ ] Document Windows SmartScreen/signing implications.
- [ ] Decide whether to ship a CLI-only bundle or add a small launcher app for common workflows.

Acceptance criteria:

- [ ] A showrunner can download the bundle, install ffmpeg separately, and run `stager --help`.
- [ ] Stager can build text artifacts from a sample `production.md`.
- [ ] Stager gives a clear ffmpeg message before an audio command fails obscurely.
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
2. Static GitHub Pages publishing for both apps.
3. Actor/showrunner quick-start docs.
4. Cuemaster import polish for large MP3 Playbooks.
5. Stager ffmpeg checks.
6. Stager Python package install.
7. Stager standalone bundle.
8. Optional Drive API integration.

This order gets actors onto browser-based tools quickly while keeping Stager packaging work scoped and testable.
