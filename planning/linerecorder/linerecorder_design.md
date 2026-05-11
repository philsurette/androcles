# LineRecorder — Design & Implementation Document

## Overview

LineRecorder is the actor-facing recording tool in the Quince production system.

It helps actors record clean, line-by-line audio for their assigned role without using Audacity, manual silence gaps, or file-renaming workflows. Stager prepares a role-specific recording pack; LineRecorder guides the actor through each user-facing line while preserving Stager `segment_id` identity; the actor records, reviews, accepts, retries, and later exports a package of recordings that can be imported back into Stager.

LineRecorder is not intended to be a full audio editor or a studio production tool. Its purpose is to make role recording simple, reliable, and segment-aware while keeping the UI actor-friendly.

The output is used primarily for:

- Cuemaster cue/reference playback,
- other actors' rehearsal cues,
- the recording actor's own baseline performance reference,
- production-managed Playbook generation.

Studio quality is not required. Usability, correct segment-to-file mapping, and reliable recording are more important.

---

## Relationship to the Quince Tool Suite

The initial Quince production suite consists of three main tools:

```text
Stager        → curate and structure the script
LineRecorder  → record role segment audio
Cuemaster     → rehearse from Playbooks
```

### Stager

Stager is used by the stage manager, director, or production organizer to curate a script in a human-readable play markup format. This markup identifies roles, spoken lines, stage directions, act/scene headers, and special syntax such as simultaneous speech.

Stager is the source of truth for the script and for the mapping between:

- role IDs,
- block IDs,
- segment IDs,
- expected audio filenames,
- Playbook manifest data.

Stager exports role-specific recording packs for LineRecorder.

### LineRecorder

LineRecorder consumes a role recording pack from Stager. It presents each recording item to the actor as a line, records one segment-backed item at a time, stores accepted takes locally, allows re-recording of individual items, and exports a recording package.

LineRecorder does not need to understand the full script. It only needs the role-specific recording item list and the metadata required to name and package each segment recording correctly.

### Cuemaster

Cuemaster consumes finished Playbooks and helps actors rehearse. Cuemaster may later export re-recording request files when an actor discovers that a line recording is wrong, out of date, or no longer reflects their intended delivery. LineRecorder should be able to import these request files and guide the actor directly to the relevant lines.

---

## Core Principles

- **No required server.** The Quince production system must work without server infrastructure, accounts, cloud sync, or hosted production services.
- **File-based handoff.** Stager, LineRecorder, and Cuemaster exchange local files such as zips, manifests, and audio assets.
- **Browser first, Capacitor later.** LineRecorder is built as a browser web app first. A Capacitor wrapper may be added later, but the core workflow must not depend on it.
- **Segment-aware recording.** The actor sees lines, but LineRecorder knows exactly which Stager segment ID each recording belongs to.
- **Easy re-recording.** Actors can replace individual segment recordings as their interpretation changes.
- **Simple audio expectations.** The goal is useful rehearsal audio, not studio mastering.
- **No GPL-family dependencies.** The shipped app must avoid GPL, LGPL, AGPL, SSPL, BUSL, unclear-license, and unlicensed dependencies.
- **Actor-friendly microphone setup.** The tool should detect common microphone problems before the actor records many unusable takes.
- **Local privacy.** Recordings stay local until the actor explicitly exports or shares them.

---

## Technology Strategy

LineRecorder should use the same broad approach as Cuemaster:

```text
React + Vite + TypeScript
Browser web app first
Capacitor-compatible architecture
Local file import/export
No backend dependency
```

### Approved Initial Stack

| Layer | Choice |
|---|---|
| UI framework | React |
| Build tool | Vite |
| Language | TypeScript |
| State management | Zustand |
| Styling | Plain CSS or CSS modules |
| Microphone access | Browser `getUserMedia` behind a small platform adapter |
| Audio capture | Web Audio API + AudioWorklet |
| Source recording format | WAV |
| Local draft storage | IndexedDB, likely through Dexie for consistency with Cuemaster |
| Package import/export | Browser File API + `jszip` or `fflate`, chosen deliberately before implementation |
| Unit testing | Vitest |
| Browser flow testing | Playwright |

Cuemaster now has a concrete browser app in this repository. LineRecorder should copy its proven local-first app boundaries where they fit: domain code outside React, platform adapters for browser capabilities, repository-style storage, browser flow tests, and dependency license auditing. If LineRecorder diverges from Cuemaster choices such as Dexie or `jszip`, record the reason in this document or a decision note.

### Why Browser First

The browser-first approach lets an actor use LineRecorder without installing a native application:

```text
Open LineRecorder
Import role recording pack
Allow microphone
Record lines
Export recordings
Send file to stage manager
```

The app can later be wrapped with Capacitor to improve mobile filesystem access, microphone permissions, sharing, and local storage. However, the core design must not assume a server or native wrapper.

---

## Licensing Policy

LineRecorder must remain eligible for both permissive open-source release and paid commercial distribution. The shipped application must not include:

- GPL,
- LGPL,
- AGPL,
- SSPL,
- BUSL,
- Commons Clause,
- unclear-license packages,
- unlicensed packages.

Preferred dependency licenses:

- MIT,
- BSD,
- ISC,
- Apache-2.0.

Any runtime dependency, audio-processing dependency, encoding library, or native/Capacitor plugin must be reviewed before adoption.

---

## Local / Offline Workflow

The baseline workflow is fully local and file-based:

```text
1. Stager exports a role recording pack.
2. Actor imports the pack into LineRecorder.
3. Actor records and accepts segment-backed line takes.
4. Actor exports a role recording package.
5. Actor shares the package by email, USB stick, AirDrop, shared drive, etc.
6. Stage manager imports the package into Stager.
7. Stager validates recordings and builds the Playbook.
8. Cuemaster imports the Playbook.
```

No accounts, hosted services, shared databases, or production servers are required.

Optional hosted/server workflows may be considered in the future, but they must never be required for the core community-theatre use case.

---

## Input Package: Role Recording Pack

Stager exports a role-specific recording pack for each actor or role. The authoritative contract is [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md).

A recording pack is a zip archive with a root `manifest.json`. The manifest contains enough information for LineRecorder to present actor-facing lines and produce correctly named segment recordings. Each recording item maps to a Stager `segment_id`; if a displayed source line contains multiple speakable segments, Stager should export multiple recording items with shared context.

Stager now emits first-class Playbook `sections` for Cuemaster. Recording packs should use the same parsed play structure for section and scene context so LineRecorder navigation matches Cuemaster rehearsal navigation. Recording packs do not need Playbook cue-start offsets or MP3 asset metadata; LineRecorder's source recording output remains WAV for Stager import.

---

## Output Package: Role Recording Package

LineRecorder exports a role recording package that Stager can import. The authoritative contract is [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md).

The output manifest lets Stager validate completeness, match recordings to Stager segment IDs, and avoid relying on file order. LineRecorder may export partial packages, but the package must explicitly report missing segment IDs so Stager does not treat partial input as complete Playbook-ready audio.

---

## Audio Capture Design

### Recording Method

LineRecorder should use:

```text
getUserMedia → Web Audio API → AudioWorklet → WAV encoding
```

This is preferred over relying only on `MediaRecorder` because `MediaRecorder` output formats vary by browser. For Stager import, predictable WAV output is more useful.

### Source Format

Initial source recording format:

```text
WAV
mono
44.1kHz or 48kHz
16-bit PCM or equivalent encoded WAV output
```

The app should not fight the device too hard. If browser capture produces a different sample rate, Stager can resample later during final processing. LineRecorder should record cleanly and document the actual sample rate in the output manifest.

### Audio Cleanup in LineRecorder

LineRecorder should provide light recording assistance, not full mastering.

MVP features:

- input level meter,
- clipping warning,
- too-quiet warning,
- optional microphone test recording,
- playback review before accepting,
- leading/trailing silence trimming if simple and reliable,
- optional browser-level noise suppression mode.

Not MVP:

- advanced noise reduction,
- multiband EQ,
- compression,
- manual waveform editing,
- LibriVox-style mastering inside the browser,
- AI performance scoring.

### Audio Cleanup in Stager

Stager or a companion local build step should handle production-side batch processing:

- loudness normalization,
- duration validation,
- clipping detection,
- resampling,
- optional format conversion,
- optional future noise reduction.

If FFmpeg is used, the project must use a license-safe build and must not bundle GPL-enabled FFmpeg binaries.

---

## Microphone Setup

Microphone setup is one of the most important parts of LineRecorder.

The app should guide the actor through:

1. Choose microphone.
2. Show live input meter.
3. Warn if there is no signal.
4. Warn if input is too quiet.
5. Warn if input clips.
6. Record a short test phrase.
7. Play the test back.
8. Confirm before starting line recording.

Cuemaster already has narrow microphone access for tempo timing in `cuemaster/src/platform/microphone.ts` and app-owned voice activity detection. LineRecorder needs deeper microphone behavior than Cuemaster because it records and exports audio, but the shared boundary should be:

- permission and secure-context checks,
- device enumeration and selected input device,
- constraint presets for clean/noisy modes,
- live level metering,
- no-signal, too-quiet, and clipping classification,
- clean shutdown of tracks and audio contexts.

LineRecorder-specific code should own WAV capture, take lifecycle, accepted-take storage, and export metadata. Cuemaster-specific code should own tempo timing and later voice-command recognition. The first LineRecorder implementation may copy small Cuemaster microphone pieces, but it should keep file/module boundaries clear enough that shared microphone code can later move into a common Quince browser module without changing product behavior.

### Recording Modes

Expose simple recording modes rather than raw browser audio terms.

#### Clean Recording Mode

For quiet rooms and decent microphones.

Suggested constraints:

```json
{
  "echoCancellation": false,
  "noiseSuppression": false,
  "autoGainControl": false
}
```

#### Noisy Room Mode

For laptop microphones or imperfect rooms.

Suggested constraints:

```json
{
  "echoCancellation": true,
  "noiseSuppression": true,
  "autoGainControl": true
}
```

The app should explain that Noisy Room Mode may reduce background noise but can also affect vocal quality.

---

## Local Draft Storage

Accepted takes should be stored locally in IndexedDB so the actor can leave and return without losing progress.

Local state should include:

- imported recording pack manifest,
- current role,
- current recording item,
- accepted take per segment,
- rejected/replaced take metadata if retained,
- recording settings,
- microphone preference where possible,
- export status,
- per-line notes if supported.

The app should not assume network access or cloud sync.

---

## Line Status Model

Each actor-facing line or recording item should have a clear status:

```text
Not recorded
Recorded
Accepted
Needs re-record
Changed in script
```

MVP may use only:

```text
Missing
Accepted
```

But the data model should leave room for richer statuses.

### Per-Segment Recording State

```ts
type SegmentRecordingState = {
  lineId: string;
  segmentId: string;
  status: "missing" | "recorded" | "accepted" | "needs_rerecord" | "changed";
  acceptedTakeId?: string;
  takes: RecordingTake[];
};

type RecordingTake = {
  takeId: string;
  recordedAt: string;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
  blobKey: string;
  notes?: string;
};
```

---

## Main Screens

### 1. Welcome / Library

Shows local recording projects.

Actions:

- import recording pack,
- resume existing recording project,
- delete local project,
- export existing project.

### 2. Import Recording Pack

Allows the actor to select a `.zip` recording pack from Stager.

Displays:

- play title,
- role name,
- number of recording items,
- package version,
- any warnings.

### 3. Microphone Setup

Guides the actor through selecting and testing the microphone.

Displays:

- microphone selector,
- live input meter,
- clipping/quiet warnings,
- recording mode,
- test record/playback,
- continue button.

### 4. Line Recording Screen

Primary screen.

Displays:

- play title,
- role name,
- current line number,
- scene/act context if available,
- cue text if available,
- stage directions if available,
- line text,
- recording status.

Controls:

- record,
- stop,
- play take,
- accept,
- retry,
- previous line,
- next line,
- line list,
- mark needs re-record,
- export.

### 5. Line List / Progress Screen

Shows all lines with status.

Functions:

- jump to any line,
- filter missing recording items,
- filter accepted recording items,
- filter needs re-record items,
- show changed items,
- show export readiness.

### 6. Export Screen

Shows package completeness and export options.

Displays:

- total lines,
- accepted recording items,
- missing recording items,
- warnings,
- export role recordings zip.

MVP should allow export even if some recording items are missing, but the package should clearly report missing segment IDs in the manifest.

---

## Re-Recording Model

Actors should be able to re-record individual segment-backed lines at any time.

Reasons include:

- actor fumbled the line,
- actor changed their interpretation,
- actor wants different emphasis,
- source line changed during rehearsal,
- original recording is too quiet/clipped/noisy,
- Cuemaster revealed that the reference recording is wrong or out of date.

Re-recording should replace the accepted take for that segment, but the app may retain older takes locally until export or cleanup.

### Re-Recording Flow

```text
Actor opens line list
Actor selects line
Actor records new take
Actor listens
Actor accepts
LineRecorder marks new take as accepted
Old accepted take becomes replaced
Export package includes only current accepted take by default
```

---

## Cuemaster Re-Recording Requests

Cuemaster should not initially include the full LineRecorder interface. The tools should remain separate for MVP.

However, the file contract should support this future workflow:

```text
Actor rehearses in Cuemaster
Actor finds a bad/outdated recording
Actor marks line for re-recording
Cuemaster exports a re-record request file
LineRecorder imports the request
Actor records replacement segments
LineRecorder exports replacement package
Stager imports replacement package
Stager rebuilds Playbook
```

### Re-Recording Request File

The authoritative future contract is [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md). LineRecorder should eventually import these files and open directly to the requested segment-backed recording items.

---

## Export and Sharing

LineRecorder does not upload recordings.

The actor exports a local file and shares it however the production prefers:

- email,
- USB stick,
- AirDrop,
- shared drive,
- Dropbox,
- Google Drive,
- local network share,
- other file transfer.

The exported package should be self-describing so Stager can validate it without relying on actor instructions.

---

## Stager Import Expectations

When Stager imports a LineRecorder package, it should validate:

- play ID matches,
- play version if required,
- role ID matches,
- segment IDs exist,
- required audio files are present,
- audio files are readable,
- durations are plausible,
- files are not silent,
- files are not clipped beyond acceptable limits,
- package may be partial if production allows it and the manifest marks it incomplete.

Stager should produce a clear report:

```text
Imported 42 accepted recordings for CENTURION.
Missing 3 lines.
2 files appear clipped.
1 file is unusually quiet.
```

---

## MVP Scope

LineRecorder MVP should include:

- import role recording pack,
- microphone setup,
- record one segment-backed line at a time,
- playback current take,
- accept/retry,
- move next/back,
- jump to any line,
- re-record accepted lines,
- persist draft recordings locally,
- export WAV recording package,
- show missing-item checklist,
- no server dependency.

MVP should not include:

- cloud upload,
- accounts,
- automatic synchronization,
- MP3 export,
- advanced noise reduction,
- waveform editing,
- multi-user collaboration,
- integrated Cuemaster recording,
- Capacitor native app,
- AI performance scoring.

---

## Later Enhancements

Potential future features:

- optional MP3 export,
- Capacitor mobile wrapper,
- improved native filesystem access,
- improved mobile microphone support,
- batch export of changed lines only,
- re-record request import from Cuemaster,
- local package signing/checksums,
- optional RNNoise-based noise suppression if licensing and quality are acceptable,
- automatic silence trimming,
- multiple accepted styles/takes per line,
- director notes in recording packs,
- changed-line update workflow,
- side-by-side comparison with previous take,
- export validation report.

---

## Open Questions

1. **WAV encoding path:** Implement app-owned WAV encoding from AudioWorklet PCM, or use a small permissively licensed helper?
2. **Sample rate:** Prefer 48kHz mono, but should LineRecorder preserve the device sample rate and let Stager resample?
3. **Noise suppression default:** Should Clean Recording Mode or Noisy Room Mode be default?
4. **Partial exports:** Should actors be allowed to export incomplete packages? Initial answer: yes, with clear missing-segment metadata.
5. **Take retention:** Should old takes be retained after a line is re-recorded? Initial answer: locally yes, exported no.
6. **Changed lines:** How should Stager communicate changed lines to an actor after a recording pack has already been started?
7. **MP3 export:** Should this be built into LineRecorder or left to Stager?
8. **Mobile browser support:** Which mobile browsers are acceptable for MVP?
9. **Capacitor timing:** When should native wrappers be explored? Initial answer: after MVP recording/export works in desktop browsers.

---

## Definition of Done for MVP

LineRecorder MVP is complete when:

- [ ] A user can import a role recording pack from Stager.
- [ ] The app validates and displays the role recording item list.
- [ ] The user can select and test a microphone.
- [ ] The app warns about no signal, too-quiet input, and clipping.
- [ ] The user can record a line.
- [ ] The user can play back the recorded take.
- [ ] The user can accept or retry the take.
- [ ] The user can advance through the role recording item list.
- [ ] The user can jump back and re-record an accepted line.
- [ ] Accepted recordings persist locally after reload.
- [ ] The user can export a role recording package as a zip.
- [ ] Exported audio files are named according to Stager segment IDs.
- [ ] Exported manifest maps recordings to segment IDs and preserves actor-facing line IDs where useful.
- [ ] Stager can import and validate the package.
- [ ] No server is required.
- [ ] No GPL-family runtime dependency is included.
