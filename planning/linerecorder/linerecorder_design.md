# LineRecorder — Design & Implementation Document

## Overview

LineRecorder is the actor-facing recording tool in the Quince production system.

It helps actors record clean, line-by-line audio for their assigned role without using Audacity, manual silence gaps, or file-renaming workflows. Stager prepares a role-specific recording package; LineRecorder guides the actor through each line; the actor records, reviews, accepts, retries, and later exports a package of recordings that can be imported back into Stager.

LineRecorder is not intended to be a full audio editor or a studio production tool. Its purpose is to make role-line recording simple, reliable, and line-aware.

The output is used primarily for:

- Cuemaster cue/reference playback,
- other actors' rehearsal cues,
- the recording actor's own baseline performance reference,
- production-managed Playbook generation.

Studio quality is not required. Usability, correct line-to-file mapping, and reliable recording are more important.

---

## Relationship to the Quince Tool Suite

The initial Quince production suite consists of three main tools:

```text
Stager        → curate and structure the script
LineRecorder  → record role-line audio
Cuemaster     → rehearse from Playbooks
```

### Stager

Stager is used by the stage manager, director, or production organizer to curate a script in a human-readable play markup format. This markup identifies roles, spoken lines, stage directions, act/scene headers, and special syntax such as simultaneous speech.

Stager is the source of truth for the script and for the mapping between:

- role IDs,
- line IDs,
- block IDs,
- segment IDs,
- expected audio filenames,
- Playbook manifest data.

Stager exports role-specific recording packs for LineRecorder.

### LineRecorder

LineRecorder consumes a role recording pack from Stager. It presents each line to the actor, records one line at a time, stores accepted takes locally, allows re-recording of individual lines, and exports a recording package.

LineRecorder does not need to understand the full script. It only needs the role-specific line list and the metadata required to name and package each recording correctly.

### Cuemaster

Cuemaster consumes finished Playbooks and helps actors rehearse. Cuemaster may later export re-recording request files when an actor discovers that a line recording is wrong, out of date, or no longer reflects their intended delivery. LineRecorder should be able to import these request files and guide the actor directly to the relevant lines.

---

## Core Principles

- **No required server.** The Quince production system must work without server infrastructure, accounts, cloud sync, or hosted production services.
- **File-based handoff.** Stager, LineRecorder, and Cuemaster exchange local files such as zips, manifests, and audio assets.
- **Browser first, Capacitor later.** LineRecorder is built as a browser web app first. A Capacitor wrapper may be added later, but the core workflow must not depend on it.
- **Line-aware recording.** The actor records one line at a time, and LineRecorder knows exactly which line and segment ID each recording belongs to.
- **Easy re-recording.** Actors can replace individual line recordings as their interpretation changes.
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
| Microphone access | Browser `getUserMedia` |
| Audio capture | Web Audio API + AudioWorklet |
| Source recording format | WAV |
| Local draft storage | IndexedDB |
| Package import/export | Browser File API + `fflate` |
| Unit testing | Vitest |
| Browser flow testing | Playwright |

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
3. Actor records and accepts line takes.
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

Stager exports a role-specific recording pack for each actor or role.

A recording pack should be a zip archive, for example:

```text
CENTURION-recording-pack.zip
├── manifest.json
└── optional/
    └── context files if needed later
```

The manifest contains enough information for LineRecorder to present the actor's lines and produce correctly named recordings.

### Conceptual Manifest Shape

```json
{
  "schema_version": 1,
  "package_type": "role_recording_pack",
  "play": {
    "id": "androcles",
    "title": "Androcles and the Lion",
    "version": "2026-05-10"
  },
  "role": {
    "id": "CENTURION",
    "display_name": "Centurion"
  },
  "recording": {
    "preferred_sample_rate_hz": 48000,
    "preferred_channels": 1,
    "source_format": "wav"
  },
  "lines": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "sequence": 1,
      "text": "Halt! Orders from the Captain.",
      "cue_text": "A bugle is heard far behind on the road.",
      "stage_directions": "stopping",
      "output_path": "audio/segments/CENTURION/0_12_1.wav"
    }
  ]
}
```

### Required Line Fields

Each line should include:

- `line_id`,
- `block_id`,
- `segment_id`,
- sequence/order value,
- line text,
- expected output path.

Optional fields may include:

- cue text,
- scene/act heading,
- stage directions,
- notes from Stager,
- previous recording metadata,
- changed-line flag,
- target delivery duration,
- target hesitation,
- simultaneous speech metadata.

---

## Output Package: Role Recording Package

LineRecorder exports a role recording package that Stager can import.

Example:

```text
CENTURION-recordings.zip
├── manifest.json
└── audio/
    └── segments/
        └── CENTURION/
            ├── 0_12_1.wav
            ├── 0_14_1.wav
            └── 0_19_1.wav
```

### Conceptual Output Manifest

```json
{
  "schema_version": 1,
  "package_type": "role_recordings",
  "play": {
    "id": "androcles",
    "title": "Androcles and the Lion",
    "version": "2026-05-10"
  },
  "role": {
    "id": "CENTURION",
    "display_name": "Centurion"
  },
  "recordings": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "audio_path": "audio/segments/CENTURION/0_12_1.wav",
      "recorded_at": "2026-05-10T14:30:00Z",
      "duration_ms": 1840,
      "sample_rate_hz": 48000,
      "channels": 1,
      "status": "accepted"
    }
  ]
}
```

The output manifest lets Stager validate completeness, match recordings to script lines, and avoid relying on file order.

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
- current line,
- accepted take per line,
- rejected/replaced take metadata if retained,
- recording settings,
- microphone preference where possible,
- export status,
- per-line notes if supported.

The app should not assume network access or cloud sync.

---

## Line Status Model

Each line should have a clear status:

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

### Per-Line Recording State

```ts
type LineRecordingState = {
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
- number of lines,
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
- filter missing lines,
- filter accepted lines,
- filter needs re-record,
- show changed lines,
- show export readiness.

### 6. Export Screen

Shows package completeness and export options.

Displays:

- total lines,
- accepted lines,
- missing lines,
- warnings,
- export role recordings zip.

MVP should allow export even if some lines are missing, but the package should clearly report missing lines in the manifest.

---

## Re-Recording Model

Actors should be able to re-record individual lines at any time.

Reasons include:

- actor fumbled the line,
- actor changed their interpretation,
- actor wants different emphasis,
- line changed during rehearsal,
- original recording is too quiet/clipped/noisy,
- Cuemaster revealed that the reference recording is wrong or out of date.

Re-recording should replace the accepted take for that line, but the app may retain older takes locally until export or cleanup.

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
Actor records replacement lines
LineRecorder exports replacement package
Stager imports replacement package
Stager rebuilds Playbook
```

### Re-Recording Request File

Conceptual shape:

```json
{
  "schema_version": 1,
  "package_type": "rerecord_request",
  "playbook_id": "androcles",
  "playbook_version": "2026-05-10",
  "role": {
    "id": "CENTURION",
    "display_name": "Centurion"
  },
  "lines": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "text": "Halt! Orders from the Captain.",
      "reason": "outdated",
      "note": "Take should be faster and less angry."
    }
  ]
}
```

LineRecorder should eventually import these files and open directly to the requested line set.

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
- line IDs exist,
- segment IDs exist,
- required audio files are present,
- audio files are readable,
- durations are plausible,
- files are not silent,
- files are not clipped beyond acceptable limits,
- package may be partial if production allows it.

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
- record one line at a time,
- playback current take,
- accept/retry,
- move next/back,
- jump to any line,
- re-record accepted lines,
- persist draft recordings locally,
- export WAV recording package,
- show missing-line checklist,
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
4. **Partial exports:** Should actors be allowed to export incomplete packages? Initial answer: yes, with clear missing-line metadata.
5. **Take retention:** Should old takes be retained after a line is re-recorded? Initial answer: locally yes, exported no.
6. **Changed lines:** How should Stager communicate changed lines to an actor after a recording pack has already been started?
7. **MP3 export:** Should this be built into LineRecorder or left to Stager?
8. **Mobile browser support:** Which mobile browsers are acceptable for MVP?
9. **Capacitor timing:** When should native wrappers be explored? Initial answer: after MVP recording/export works in desktop browsers.

---

## Definition of Done for MVP

LineRecorder MVP is complete when:

- [ ] A user can import a role recording pack from Stager.
- [ ] The app validates and displays the role line list.
- [ ] The user can select and test a microphone.
- [ ] The app warns about no signal, too-quiet input, and clipping.
- [ ] The user can record a line.
- [ ] The user can play back the recorded take.
- [ ] The user can accept or retry the take.
- [ ] The user can advance through the role line list.
- [ ] The user can jump back and re-record an accepted line.
- [ ] Accepted recordings persist locally after reload.
- [ ] The user can export a role recording package as a zip.
- [ ] Exported audio files are named according to Stager segment IDs.
- [ ] Exported manifest maps recordings to line IDs and segment IDs.
- [ ] Stager can import and validate the package.
- [ ] No server is required.
- [ ] No GPL-family runtime dependency is included.
