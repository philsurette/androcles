# LineRecorder Use Cases

## Purpose

This document describes the primary use cases for LineRecorder, the actor-facing recording tool in the Quince production system.

LineRecorder helps actors record their role lines one at a time from a Stager-generated recording pack. In the UI these are lines; in package contracts and Stager code they are segment-backed recording items. The actor can review, accept, retry, re-record individual items, and export a package of audio files for the stage manager or director to import back into Stager.

The system must work without server infrastructure. All core workflows are local, offline-capable, and file-based.

The authoritative file contract for recording packs, recording packages, and future re-record requests is [recording_package_manifest.md](recording_package_manifest.md).

---

## User Roles

### Actor

The primary user. The actor imports a recording pack, records their lines, reviews takes, re-records as needed, and exports the finished or partial segment recordings.

### Stage Manager / Director / Production Organizer

Creates or manages the Stager script, exports recording packs, receives actor recordings, imports recordings into Stager, and builds Playbooks.

### Cuemaster User

Usually the actor. While rehearsing in Cuemaster, the user may discover that a line recording is wrong or outdated and mark it for re-recording in LineRecorder.

---

## Core Recording Use Cases

### UC-001: Import a Role Recording Pack

**Actor goal:** Start recording a role from a Stager-generated package.

**Scenario:**

1. The actor receives a role recording pack from the stage manager.
2. The actor opens LineRecorder.
3. The actor chooses **Import Recording Pack**.
4. The actor selects the local zip file.
5. LineRecorder validates the package.
6. LineRecorder displays the play title, role name, and recording item count.

**Notes:**

- The package is local and file-based.
- No account, server, or hosted service is required.
- The package should include enough metadata for correct segment audio filenames.

---

### UC-002: Resume an Existing Recording Project

**Actor goal:** Continue a partially completed role recording session.

**Scenario:**

1. The actor opens LineRecorder.
2. The app shows local recording projects.
3. The actor selects a project.
4. LineRecorder restores the line list, accepted segment takes, and current position.

**Notes:**

- Accepted takes should persist locally in IndexedDB.
- The actor should not need to re-import the pack every time.

---

### UC-003: Select and Test a Microphone

**Actor goal:** Confirm that the microphone works before recording lines.

**Scenario:**

1. LineRecorder shows available microphones.
2. The actor selects a microphone.
3. The app shows a live input meter.
4. The actor records a short test.
5. The actor plays the test back.
6. The actor confirms the setup.

**Notes:**

- The app should warn if there is no input.
- The app should warn if input is too quiet.
- The app should warn if the signal clips.
- This is one of the most important usability features.

---

### UC-004: Choose Recording Mode

**Actor goal:** Pick a simple audio setup appropriate to the environment.

**Scenario:**

1. The actor reaches microphone setup.
2. The app offers simple modes:
   - Clean Recording Mode,
   - Noisy Room Mode.
3. The actor chooses a mode.
4. The app applies appropriate browser microphone constraints.

**Notes:**

- Clean Recording Mode is better for quiet rooms and decent microphones.
- Noisy Room Mode may help laptop microphones or imperfect rooms.
- The UI should not expose confusing browser audio terminology.

---

### UC-005: Record the Current Line

**Actor goal:** Record one assigned line.

**Scenario:**

1. LineRecorder displays the current line text.
2. The actor presses **Record**.
3. The actor reads the line.
4. The actor presses **Stop**.
5. The app saves the take locally.

**Notes:**

- Manual start/stop is sufficient for MVP.
- The app should associate the recording with the correct actor-facing line ID and Stager segment ID.

---

### UC-006: Play Back the Recorded Take

**Actor goal:** Hear whether the take is acceptable.

**Scenario:**

1. The actor records a take.
2. The actor presses **Play**.
3. LineRecorder plays the take back.
4. The actor decides whether to accept or retry.

**Notes:**

- Playback review is essential because the app is not judging performance.
- The actor remains responsible for accepting the take.

---

### UC-007: Accept a Take

**Actor goal:** Mark the current recording as the usable version for that line.

**Scenario:**

1. The actor listens to the take.
2. The actor presses **Accept**.
3. LineRecorder marks the take as accepted.
4. The line status updates.
5. The app advances to the next line or offers to advance.

**Notes:**

- Export should include the accepted take for each segment by default.
- Older takes may remain locally but should not be exported unless explicitly requested later.

---

### UC-008: Retry a Take

**Actor goal:** Replace a fumbled or unsatisfactory take.

**Scenario:**

1. The actor records a line.
2. The actor decides the take is not acceptable.
3. The actor presses **Retry**.
4. LineRecorder records a new take for the same line.
5. The actor reviews the new take.

**Notes:**

- Retrying should be fast and obvious.
- The actor should never need to manage filenames manually.

---

### UC-009: Advance to the Next Line

**Actor goal:** Move through the recording list efficiently.

**Scenario:**

1. The actor accepts a take.
2. The actor presses **Next** or the app offers to continue.
3. LineRecorder displays the next line.

**Notes:**

- Auto-advance after accept may be configurable.
- The actor should be able to move manually if preferred.

---

### UC-010: Go Back to a Previous Line

**Actor goal:** Review or replace an earlier recording.

**Scenario:**

1. The actor presses **Back**.
2. LineRecorder displays the previous line.
3. The actor can play the accepted take or record a new one.

**Notes:**

- Re-recording earlier lines is core behavior, not an edge case.

---

## Re-Recording Use Cases

### UC-011: Re-Record an Accepted Line

**Actor goal:** Replace a segment-backed line after changing their interpretation.

**Scenario:**

1. The actor opens the line list.
2. The actor selects an already accepted line.
3. The actor records a new take.
4. The actor listens to the new take.
5. The actor accepts it.
6. The new take becomes the current accepted recording for that segment.

**Notes:**

- Actors may change emphasis, pacing, tone, or intention during rehearsal.
- The tool should support evolving performance choices.

---

### UC-012: Re-Record a Line Because the Script Changed

**Actor goal:** Replace a recording for a changed source line or segment.

**Scenario:**

1. The stage manager sends an updated recording pack or re-record request.
2. LineRecorder marks changed recording items.
3. The actor records only the changed segment-backed items.
4. The actor exports a replacement package.

**Notes:**

- Full script-update handling may be later than MVP.
- The data model should leave room for changed-item status.

---

### UC-013: Re-Record a Line Flagged from Cuemaster

**Actor goal:** Replace a line after discovering a problem during rehearsal.

**Scenario:**

1. The actor rehearses with Cuemaster.
2. The actor hears a reference line that is wrong, stale, or no longer useful.
3. The actor marks the line for re-recording.
4. Cuemaster exports a local re-record request file.
5. The actor imports that request into LineRecorder.
6. LineRecorder opens the requested line or list of segment-backed recording items.
7. The actor records replacements.
8. The actor exports a replacement package.

**Notes:**

- This workflow should be file-based.
- Cuemaster should not need to contain the full LineRecorder UI in MVP.
- Stager remains responsible for incorporating replacements into the official Playbook.

---

### UC-014: Export Only Replacement Lines

**Actor goal:** Send only the changed or re-recorded segments to the stage manager.

**Scenario:**

1. The actor re-records one or more segment-backed items.
2. The actor chooses **Export Replacements**.
3. LineRecorder creates a package containing only those segment recordings.
4. The actor sends the package to the stage manager.
5. Stager imports and validates the replacements.

**Notes:**

- This is likely a post-MVP feature.
- It reduces file size and confusion during active production changes.

---

## Navigation and Progress Use Cases

### UC-015: View Recording Progress

**Actor goal:** Know how much recording remains.

**Scenario:**

1. The actor opens the progress screen.
2. LineRecorder shows:
   - total recording items,
   - accepted items,
   - missing items,
   - needs re-record items,
   - changed items where applicable.

**Notes:**

- Progress should be visible before export.
- The actor should not accidentally send a package thinking it is complete when lines are missing.

---

### UC-016: Jump to Any Line

**Actor goal:** Move directly to a specific line.

**Scenario:**

1. The actor opens the line list.
2. The actor selects a line.
3. LineRecorder opens that segment-backed line on the recording screen.

**Notes:**

- This is important for re-recording and partial work sessions.
- The line list should show status clearly.

---

### UC-017: Filter Missing Lines

**Actor goal:** Record only lines not yet completed.

**Scenario:**

1. The actor opens the line list.
2. The actor selects the **Missing** filter.
3. LineRecorder shows only unrecorded items.
4. The actor records them.

**Notes:**

- This helps actors finish incomplete projects quickly.

---

### UC-018: Filter Lines Needing Re-Record

**Actor goal:** Focus on lines that need replacement.

**Scenario:**

1. The actor opens the line list.
2. The actor selects **Needs Re-Record**.
3. LineRecorder shows only flagged recording items.
4. The actor records new takes.

**Notes:**

- This supports Cuemaster re-record requests and production updates.

---

## Export and Sharing Use Cases

### UC-019: Export a Complete Role Recording Package

**Actor goal:** Send all accepted recordings to the stage manager.

**Scenario:**

1. The actor finishes recording all lines.
2. The actor opens the export screen.
3. LineRecorder confirms all required segment-backed items are accepted.
4. The actor exports a zip package.
5. The actor shares the file by email, USB, AirDrop, shared drive, or another file-transfer method.

**Notes:**

- No upload service is required.
- The zip should contain audio files and a manifest.

---

### UC-020: Export an Incomplete Package

**Actor goal:** Send partial work when not all lines are ready.

**Scenario:**

1. The actor records some lines.
2. The actor opens export.
3. LineRecorder warns that some recording items are missing.
4. The actor chooses to export anyway.
5. The output manifest clearly lists missing segment IDs.

**Notes:**

- This should be allowed because production workflows are messy.
- The package should not pretend to be complete.

---

### UC-021: Share Recordings Without Server Infrastructure

**Actor goal:** Deliver files using whatever method the production prefers.

**Scenario:**

1. The actor exports the package.
2. The actor sends it by:
   - email,
   - USB stick,
   - AirDrop,
   - Dropbox,
   - Google Drive,
   - local shared folder,
   - another file-transfer tool.
3. The stage manager imports the file into Stager.

**Notes:**

- Quince must not require a production server.
- Optional hosted workflows may exist later, but local file sharing must always work.

---

### UC-022: Export WAV Files

**Actor goal:** Provide predictable source audio.

**Scenario:**

1. The actor exports recordings.
2. LineRecorder packages accepted takes as WAV files.
3. Stager imports the WAV files and can process them further.

**Notes:**

- WAV is preferred for MVP because it is predictable and avoids MP3 encoder complications.
- MP3 export may be added later as an optional convenience.

---

## Stage Manager / Stager Use Cases

### UC-023: Export Recording Packs from Stager

**Stage manager goal:** Prepare segment-backed line lists for actors to record.

**Scenario:**

1. The stage manager curates the play in Stager.
2. Stager identifies each role's actor-facing lines and segment IDs.
3. Stager exports a recording pack for a role.
4. The stage manager sends the pack to the actor.

**Notes:**

- Recording packs should be small because they contain metadata, not all production audio.
- The pack should be human-debuggable where possible.

---

### UC-024: Import Actor Recordings into Stager

**Stage manager goal:** Bring actor recordings into the production audio asset set.

**Scenario:**

1. The stage manager receives a role recording package.
2. The stage manager imports it into Stager.
3. Stager validates play ID, role ID, segment IDs, optional line IDs, and audio files.
4. Stager places audio in the correct production asset paths.
5. Stager reports missing, clipped, silent, or suspicious files.

**Notes:**

- Stager should not rely only on file order.
- The manifest should map audio files to segment IDs and preserve actor-facing line IDs where useful.

---

### UC-025: Validate Recording Completeness

**Stage manager goal:** Know whether the actor submitted all required lines.

**Scenario:**

1. Stager imports a recording package.
2. Stager compares recordings with the role segment list.
3. Stager reports:
   - recorded segments,
   - missing segments,
   - extra/unrecognized segments.

**Notes:**

- This prevents silent production errors.
- Partial imports may be allowed but should be explicit.

---

### UC-026: Run Final Audio Processing

**Stage manager goal:** Prepare actor recordings for Playbook use.

**Scenario:**

1. Stager imports recordings.
2. Stager runs local audio processing.
3. Processing may include:
   - loudness normalization,
   - resampling,
   - clipping checks,
   - silence trimming,
   - format conversion.
4. Stager writes final audio segments for Playbook generation.

**Notes:**

- This is better handled in Stager than in LineRecorder.
- Any audio processing tools must satisfy the Quince licensing policy.

---

## Privacy and Trust Use Cases

### UC-027: Record Locally Without Uploading Audio

**Actor goal:** Trust that recordings remain under local control.

**Scenario:**

1. The actor records lines.
2. LineRecorder stores recordings locally.
3. The app does not upload audio.
4. The actor explicitly exports a package when ready.

**Notes:**

- This is important for community theatres and cautious users.
- The app should clearly explain that recordings stay local.

---

### UC-028: Use LineRecorder Without an Account

**Actor goal:** Record lines without creating a login.

**Scenario:**

1. The actor opens LineRecorder.
2. The actor imports a local recording pack.
3. The actor records and exports files.
4. No account is created.

**Notes:**

- Accounts are out of scope for the core workflow.

---

### UC-029: Delete Local Recording Data

**Actor goal:** Remove local recordings from the browser.

**Scenario:**

1. The actor opens project/library management.
2. The actor chooses to delete a recording project.
3. LineRecorder confirms deletion.
4. The app removes local manifests, takes, and exported-state data.

**Notes:**

- The app should distinguish deleting local drafts from deleting already exported files outside the app.

---

## Error and Recovery Use Cases

### UC-030: Microphone Permission Denied

**Actor goal:** Understand why recording is unavailable and how to fix it.

**Scenario:**

1. The actor attempts microphone setup.
2. Browser permission is denied.
3. LineRecorder shows a clear explanation.
4. The app gives browser-specific guidance if possible.

**Notes:**

- The app should not fail silently.
- The actor should still be able to view the line list.

---

### UC-031: Microphone Produces No Signal

**Actor goal:** Detect a bad microphone setup before recording lines.

**Scenario:**

1. The actor selects a microphone.
2. The input meter shows no signal.
3. The app warns that no voice is detected.
4. The actor selects another microphone or fixes the system setting.

**Notes:**

- This avoids recording many silent takes.

---

### UC-032: Recording Is Too Quiet

**Actor goal:** Avoid unusably quiet recordings.

**Scenario:**

1. The actor records or tests the microphone.
2. The app detects consistently low input.
3. The app warns the actor.
4. The actor moves closer, changes microphone, or adjusts settings.

**Notes:**

- The warning should be simple and actionable.

---

### UC-033: Recording Clips

**Actor goal:** Avoid distorted recordings.

**Scenario:**

1. The actor records a loud take.
2. The app detects clipping or near-clipping.
3. The app warns the actor.
4. The actor re-records at a lower level or farther from the microphone.

**Notes:**

- Clipping detection is more valuable than fancy cleanup.

---

### UC-034: Browser Storage Is Full

**Actor goal:** Recover from storage quota problems.

**Scenario:**

1. The actor records many lines.
2. Browser storage quota is reached.
3. LineRecorder warns the actor.
4. The actor exports current work or deletes old projects.

**Notes:**

- WAV files can be large.
- The app should avoid pretending saves succeeded when they did not.

---

### UC-035: Export Fails

**Actor goal:** Avoid losing work if export does not complete.

**Scenario:**

1. The actor starts export.
2. The export fails.
3. LineRecorder reports the failure.
4. Local accepted takes remain stored.
5. The actor can retry export.

**Notes:**

- Export failure should not corrupt local recordings.

---

## Out-of-Scope Use Cases for MVP

The following should not drive MVP implementation:

- server upload,
- user accounts,
- cloud sync,
- live collaboration,
- waveform editing,
- advanced noise reduction,
- studio mastering,
- automatic acting/performance scoring,
- automatic speech correctness scoring,
- native mobile app,
- MP3 export,
- direct integration inside Cuemaster,
- director dashboard.

---

## MVP Use Cases

The MVP should support:

- import role recording pack,
- resume local recording project,
- select/test microphone,
- record current line,
- play back take,
- accept/retry take,
- next/back navigation,
- jump to any line,
- re-record accepted line,
- view missing/accepted progress,
- export WAV zip package,
- share package through external file transfer,
- delete local project.

---

## Later Use Cases

Good later candidates:

- import Cuemaster re-record request,
- export replacement-only package,
- mark changed lines from updated Stager pack,
- optional MP3 export,
- Capacitor mobile wrapper,
- improved mobile microphone support,
- multiple saved takes per line,
- compare old and new takes,
- local audio cleanup options,
- RNNoise-based optional noise suppression if licensing and quality are acceptable,
- export validation report,
- project checksum/signature support.

---

## Key Product Principles Reinforced by These Use Cases

1. **LineRecorder knows the segment identity.** The actor should not manage filenames, order, or silence gaps manually.

2. **Recording should be local and trustworthy.** No account, server, or upload is required.

3. **Re-recording is normal.** Actors refine their line readings as rehearsal progresses.

4. **Microphone setup matters.** Preventing bad recordings is more valuable than trying to repair them later.

5. **Stager remains the production source of truth.** LineRecorder captures role audio by segment ID; Stager validates and integrates it.

6. **Cuemaster integration should be file-based first.** Re-record requests should move between tools as local files, not through a server.

7. **The tool should not become Audacity.** The goal is guided line capture, not general-purpose audio editing.

8. **WAV first.** Predictable source audio is more important than small files in MVP.

9. **No GPL-family dependencies.** Licensing must preserve the option for open-source or paid distribution.
