# Floor Noise Capture And Import Denoising Plan

This plan adds optional room-tone capture to LineRecorder and import-time denoising to Stager. The goal is to improve actor-submitted recordings while keeping the actor workflow simple and keeping original exported audio recoverable.

The shared file contract changes belong in [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md). This document covers implementation sequencing and behavior.

## Goals

- Capture short floor-noise recordings during microphone setup and whenever room conditions change.
- Export floor-noise WAV files with accepted line recordings.
- Associate each accepted line recording with the most recent floor-noise sample captured before the take started.
- Let Stager use the associated floor-noise sample during `recording-import` when available.
- Trim leading and trailing silence from imported line recordings.
- Preserve source package audio so imports can be undone or reprocessed with different denoise settings.

## Non-Goals

- Do not require floor-noise capture before recording.
- Do not apply browser-side denoising in LineRecorder.
- Do not overwrite actor takes in LineRecorder with processed audio.
- Do not make denoising a prerequisite for Playbook generation.
- Do not attempt to remove transient noises such as clicks, chair movement, keyboard taps, or traffic bursts in the first pass.

## Product Behavior

LineRecorder should treat floor-noise capture as a microphone setup capability:

- When the microphone starts successfully, show a `Capture Room Tone` control near the input meter.
- The control records 3-5 seconds while telling the actor to stay silent.
- On completion, show a compact status such as `Room tone captured 3:14 PM`.
- Actors can capture another room-tone sample at any time after the mic is active.
- A later sample supersedes earlier samples for subsequent takes, but earlier samples remain available for takes recorded after them and before the next sample.
- If no room-tone sample exists, recording and export still work.

LineRecorder should not hide the fact that this is optional. Suggested copy:

- Button: `Capture Room Tone`
- During capture: `Stay silent...`
- After capture: `Room tone captured`
- Export warning when none exists: no warning for MVP, because denoising is optional.

## Package Contract

`role_recordings` exports should add optional floor-noise metadata:

- `floor_noise_recordings[]`
  - `id`
  - `audio_path`
  - `recorded_at`
  - `duration_ms`
  - `sample_rate_hz`
  - `channels`
  - `device_label`
  - `mode`
- `recordings[].floor_noise_id`

The association rule is simple:

1. Sort floor-noise recordings by `recorded_at`.
2. For each accepted take, choose the newest floor-noise recording with `recorded_at <= take.recorded_at`.
3. If none exists, omit `floor_noise_id`.

LineRecorder should compute and write `floor_noise_id` during export. Stager should also be able to recompute the association from timestamps if an older package omits `floor_noise_id` but includes floor-noise recordings.

## LineRecorder Implementation

### Data Model

Add a local `FloorNoiseRecording` record:

- `id`
- `projectId`
- `blob`
- `recordedAt`
- `durationMs`
- `sampleRateHz`
- `channels`
- `deviceId`
- `deviceLabel`
- `mode`
- `inputQuality`

Store it in IndexedDB beside takes. Keep it project-scoped rather than line-scoped.

Accepted takes already need `recordedAt`; if any current take model lacks that timestamp, add it before floor-noise association work.

### Capture Flow

Reuse the existing WAV recorder path rather than adding a second audio implementation:

1. Require an active microphone setup.
2. Start a 5-second capture from the same `MediaStream`/AudioWorklet path used for line takes.
3. Disable line recording controls during room-tone capture.
4. Track level counts during capture.
5. Store the resulting WAV blob and metadata.
6. Reject captures that contain clipping or sustained voice-level energy.

For the first pass, rejection can be conservative:

- clipping count must be zero;
- most frames should be `too_quiet` or `good` at low energy;
- if the meter sees likely speech, show `Room tone was too loud. Try again while silent.`

### Export Flow

When exporting role recordings:

1. Load accepted takes.
2. Load project floor-noise recordings.
3. Write each floor-noise WAV under `noise/<floor_noise_id>.wav`.
4. Write `floor_noise_recordings[]` manifest entries.
5. For each accepted take, set `floor_noise_id` using the timestamp association rule.
6. Keep accepted line WAVs exactly as recorded under their existing `audio/segments/...` paths.

## Stager Import Implementation

### Import Options

Add an import option before making denoising automatic:

```sh
./main recording-import CHRISTINE.role-recordings.zip --denoise
```

Follow-up options can tune behavior:

```sh
./main recording-import CHRISTINE.role-recordings.zip --denoise --trim-silence
./main recording-import CHRISTINE.role-recordings.zip --no-denoise
```

Default recommendation:

- First implementation: default off, opt in with `--denoise`.
- After listening tests: consider default on when `floor_noise_id` is present.

### Validation

Stager should validate:

- every `floor_noise_recordings[].audio_path` exists in the zip;
- each floor-noise file is readable WAV audio;
- referenced `recordings[].floor_noise_id` exists;
- floor-noise duration is plausible, ideally 2-10 seconds;
- floor-noise sample rate/channel count can be converted to match the line recording.

If a referenced floor-noise file is invalid, Stager should raise for `--denoise`; without `--denoise`, it may ignore the floor-noise metadata after validating the normal recording package.

### Processing Pipeline

For each imported accepted recording:

1. Extract the original line WAV to a temporary path.
2. Resolve the floor-noise WAV:
   - use `recordings[].floor_noise_id` when present;
   - otherwise choose the newest floor-noise recording before `recorded_at`;
   - if none exists, skip denoising for that line.
3. Create a temporary processing input by prepending the floor-noise WAV to the line WAV.
4. Run FFmpeg `afftdn` with commands that sample only the prepended floor-noise interval.
5. Trim off the prepended floor-noise interval.
6. Detect and trim leading/trailing silence from the processed line recording.
7. Validate final duration and loudness.
8. Copy the processed WAV into Stager's segment tree.
9. Save import metadata that records the source package, source audio path, floor-noise id, denoise settings, trim settings, and output path.

The original imported package must remain the recoverable source. Existing import undo should restore previous segment files; future reprocessing can re-run from the saved package or a preserved extracted original.

### FFmpeg Strategy

Use `afftdn` as the first denoiser because it is FFmpeg-native, deterministic, does not require a model file, and supports measured noise profiles.

Conceptual filter chain:

```text
concat floor_noise + take
sample afftdn noise profile during floor_noise interval
apply afftdn to whole stream
atrim away the floor_noise prefix
silence-trim leading/trailing quiet
write WAV
```

Illustrative command shape:

```sh
ffmpeg -i combined.wav \
  -af "asendcmd=0.0 afftdn sn start,asendcmd=5.0 afftdn sn stop,afftdn=nr=10:nf=-50,atrim=start=5.0,silenceremove=..." \
  output.wav
```

The exact filtergraph should be built by a Stager service, not inline in CLI code. Start with conservative settings:

- `nr=6` to `nr=12`;
- `nf=-50` as initial floor, adjusted after listening tests;
- use `om=n` in development fixtures to audit what is being removed;
- avoid high reduction values until we have representative actor recordings.

### Silence Trimming

Stager should trim line recordings after denoise, not in LineRecorder:

- LineRecorder preserves the actor's raw accepted take.
- Stager has FFmpeg and can apply consistent trimming.
- Import can be re-run with adjusted thresholds.

Use FFmpeg `silenceremove` or an existing Stager audio helper if it already provides robust leading/trailing silence detection. The initial target is to remove only obvious dead air at each end, not pauses inside a line.

Suggested starting policy:

- trim leading silence below a conservative dB threshold;
- trim trailing silence below the same threshold;
- preserve a small pad, such as 100-200 ms, if FFmpeg filter support and implementation complexity allow it;
- never remove interior silence.

## Stager Code Shape

Add small services rather than embedding this in the importer:

- `RoleRecordingsManifestReader`: extend to parse optional floor-noise metadata.
- `FloorNoiseResolver`: maps each recording to its floor-noise sample by explicit id or timestamp.
- `RecordingDenoiser`: owns FFmpeg `afftdn` invocation.
- `RecordingSilenceTrimmer`: owns start/end silence trimming.
- `RecordingImportProcessor`: orchestrates validation, optional denoise, optional trim, and import copy.

Keep `RoleRecordingsImporter` responsible for package-level validation and import result reporting. It should delegate audio transformation rather than constructing FFmpeg commands directly.

## Tests

LineRecorder tests:

- captures floor noise only when mic is active;
- stores multiple floor-noise samples with timestamps;
- associates each take with the most recent previous sample;
- exports floor-noise WAVs and manifest entries;
- exports accepted takes unchanged;
- exports successfully with no floor-noise samples.

Stager tests:

- parses packages with and without `floor_noise_recordings`;
- rejects missing referenced floor-noise files when denoise is requested;
- associates recordings by explicit `floor_noise_id`;
- falls back to timestamp association when `floor_noise_id` is absent;
- invokes FFmpeg through an injectable collaborator so unit tests do not require FFmpeg;
- trims only leading/trailing silence in mocked processor tests;
- preserves import undo behavior after denoised imports.

Manual listening tests:

- clean room USB microphone;
- laptop microphone with fan noise;
- changing room noise with two room-tone samples;
- quiet actor line;
- loud actor line;
- line with deliberate pause;
- package with no room-tone samples.

## Rollout Phases

### Phase 1: Contract And Storage

- Add optional `floor_noise_recordings` and `recordings[].floor_noise_id` to manifest types and validators.
- Add LineRecorder floor-noise repository/storage.
- Add export manifest support without UI capture.
- Add fixtures that include floor-noise metadata.

### Phase 2: LineRecorder Capture

- Add `Capture Room Tone` UI.
- Record 5 seconds from the active mic.
- Store and export samples.
- Associate accepted takes with the correct sample.

### Phase 3: Stager Import Plumbing

- Parse and validate floor-noise metadata.
- Add import flags for `--denoise` and `--trim-silence`.
- Add injectable processing services with mocked tests.
- Keep default behavior unchanged.

### Phase 4: FFmpeg Processing

- Implement `afftdn` denoise from prepended room tone.
- Implement leading/trailing silence trim.
- Record processing metadata.
- Add integration tests that skip cleanly when FFmpeg is unavailable.

### Phase 5: Listening And Defaults

- Run representative listening tests.
- Tune conservative default settings.
- Decide whether `--denoise` should become default when floor-noise metadata is present.
- Document user-facing guidance for when to capture a new room-tone sample.

## Open Questions

- Should LineRecorder capture 3 seconds or 5 seconds by default?
- Should the UI show the active floor-noise sample timestamp beside the mic meter?
- Should denoise happen during Stager import, during a later `segments` build step, or both?
- Should processed imports store a sidecar manifest under `build/<play>/linerecorder/imports/` for future reprocessing?
- What silence threshold is safest across USB microphones and laptop microphones?
