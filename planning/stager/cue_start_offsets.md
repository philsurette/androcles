# Stager Plan: Cue Start Offsets For Long Cues

## Goal

Let Cuemaster play the last useful portion of a long cue without cutting into the middle of a word.

Stager should compute optional cue-start offsets during Playbook generation. Cuemaster can then offer user-facing settings such as **Full cue**, **Last 20s**, **Last 15s**, **Last 10s**, and **Last 5s**, while starting playback near a low-volume boundary rather than at an exact hard timestamp.

## Non-Goals

- Do not change Stager's source play text format.
- Do not require speech recognition, transcription, or Whisper.
- Do not make Playbook generation tolerant of missing cue/response audio.
- Do not make Cuemaster analyze waveform data during import for the MVP.
- Do not require smart offsets for every audio asset before Playbooks can be generated.

## Terminology

- **Cue content duration**: existing `audio.duration_ms`, meaning audible content duration excluding codec/container padding.
- **Requested cue window**: the actor setting, e.g. "last 10 seconds".
- **Cue start offset**: timestamp in milliseconds on the cue asset's audible content timeline where playback should begin.
- **Boundary**: a low-volume point near the requested cue window, preferably between spoken words.

## Product Behavior

Cuemaster should preserve the current default: full cue playback.

When the actor chooses a max cue length:

- If the cue duration is less than or equal to the selected max length, play the full cue.
- If Stager supplied a matching cue-start offset, start cue playback at that offset.
- If no matching offset exists, fall back to `max(0, duration_ms - selectedMaxCueMs)`.
- Apply the max cue length to the final cue audio item only. Cue-depth context before the final cue can still play normally or be skipped by future Cuemaster settings.

## Manifest Shape

The Playbook manifest source of truth remains `planning/specs/playbook_manifest.md`.

Recommended extension on `ManifestAudioAsset`:

```json
{
  "path": "audio/segments/MEGAERA/0_5_2.wav",
  "duration_ms": 2430,
  "required": true,
  "cue_start_offsets": [
    {
      "requested_window_ms": 5000,
      "start_ms": 0,
      "confidence": "exact"
    }
  ]
}
```

Fields:

- `requested_window_ms`: The user-facing target window this offset supports.
- `start_ms`: Milliseconds from the start of the asset where playback should begin.
- `confidence`: `exact`, `boundary`, or `fallback`.

Rules:

- `cue_start_offsets` is optional.
- Offsets are useful for cue audio assets; response audio may omit them.
- `start_ms` must satisfy `0 <= start_ms < duration_ms`.
- `start_ms` is a content-timeline offset, not a codec/container timestamp.
- Offsets must not alter `duration_ms`.
- Stager should emit at most one offset per requested window per asset.

## Compressed Audio Compatibility

MP3 or other compressed Playbook audio can introduce encoder delay, padding, or seek behavior that does not exactly match the source WAV sample timeline. Stager must not assume a cue-start offset computed from source WAV samples is automatically valid as a seek timestamp in the packaged compressed file.

Required policy:

- `duration_ms` and `cue_start_offsets[].start_ms` are both audible content-timeline values.
- WAV packaging may use source-WAV offsets directly.
- Compressed packaging must validate, adjust, recompute, or omit offsets for the packaged asset.
- If Stager cannot verify that seeking to `start_ms` in the packaged compressed file lands near the intended boundary within tolerance, it should omit `cue_start_offsets` for that asset and let Cuemaster fall back to exact max-cue truncation.
- MP3 frame/container duration drift must not be folded into `duration_ms` or `start_ms`.

Recommended initial rule: implement and validate cue-start offsets for WAV Playbooks first. Add MP3 offset emission only after MP3 packaging has a testable seek-validation path.

## Initial Windows

Use these target windows first:

- `5000`
- `10000`
- `15000`
- `20000`

Cuemaster can expose those as **Last 5s**, **Last 10s**, **Last 15s**, and **Last 20s**.

## Boundary Algorithm

Use audio-energy analysis rather than transcription.

For each cue asset and requested window:

1. Let `target_start_ms = max(0, duration_ms - requested_window_ms)`.
2. If `target_start_ms` is `0`, emit `start_ms = 0`, `confidence = "exact"`.
3. Analyze a search region around `target_start_ms`.
4. Prefer the quietest plausible boundary in that region.
5. If no plausible boundary is found, emit `target_start_ms`, `confidence = "fallback"`.

Recommended initial search region:

- Search from `target_start_ms - 1500ms` to `target_start_ms + 1500ms`.
- Clamp to `[0, duration_ms)`.
- Prefer boundaries before `target_start_ms` when scores are similar so the actor gets at least the requested amount of cue context.

Recommended analysis:

- Convert to mono for analysis only.
- Use short RMS windows, e.g. 20-50ms.
- Smooth RMS values over neighboring windows.
- Identify local minima below a relative threshold based on the asset's median or upper-percentile RMS.
- Avoid starts too close to the end of the asset.

The exact threshold should be test-driven with real cues from Androcles and Fairies before being treated as stable.

## Stager Implementation Plan

### Phase 1: Contract And Dataclasses

- [ ] Add optional cue-start-offset dataclasses to the Playbook manifest model.
- [ ] Allow `cue_start_offsets` in manifest JSON validation.
- [ ] Add fixture tests proving existing manifests without offsets still validate.
- [ ] Add fixture tests proving offsets serialize with audio assets.

### Phase 2: Audio Analysis Service

- [ ] Add a `CueStartOffsetAnalyzer` service under the Stager Playbook package.
- [ ] Inject audio loading/duration helpers so tests can use generated tiny WAV fixtures.
- [ ] Compute offsets for the initial windows: 5s, 10s, 15s, 20s.
- [ ] Unit-test short audio where every requested window should start at `0`.
- [ ] Unit-test a synthetic cue with silence near a target boundary.
- [ ] Unit-test fallback behavior when no quiet boundary is available.

### Phase 3: Playbook Builder Integration

- [ ] Run the analyzer for cue audio assets used by rehearsable role lines.
- [ ] Attach offsets to the relevant manifest audio asset objects.
- [ ] Do not analyze response-only assets unless they are also used as cues.
- [ ] Keep Playbook generation strict: missing cue audio remains an exception.
- [ ] Verify Stager still writes valid Playbooks without requiring Cuemaster changes.

### Phase 3.5: Compressed Packaging Compatibility

- [ ] Treat source-WAV offsets as content-timeline metadata.
- [ ] If Playbook audio format is WAV, emit offsets directly.
- [ ] If Playbook audio format is MP3, do not emit offsets until packaged-file seek validation exists.
- [ ] Add tests proving MP3 packaging either validates/recomputes offsets or omits them.
- [ ] Document the accepted seek tolerance before enabling MP3 offsets.

### Phase 4: Cuemaster Integration

- [ ] Add max-cue-length session preference.
- [ ] Add a cue-length selector in the rehearsal UI.
- [ ] Use `cue_start_offsets` for the final cue item when available.
- [ ] Fall back to exact `duration_ms - selectedWindowMs` when offsets are absent.
- [ ] Persist the actor's cue-length preference.
- [ ] Update the user guide.

### Phase 5: Real Play Validation

- [ ] Generate Playbooks for Androcles and Fairies.
- [ ] Inspect long cue offsets manually.
- [ ] Confirm offsets start between words in common cases.
- [ ] Confirm short cues still play from the beginning.
- [ ] If MP3 Playbook packaging is enabled, confirm MP3 cue seeking starts near the same audible boundary as the WAV source.
- [ ] Run Cuemaster import/rehearsal tests with offset-bearing Playbooks.

## Testing Notes

Tests should not depend on real recordings, Whisper, network access, or ffmpeg. Use generated WAV fixtures or mocked audio-energy data for unit tests.

Integration validation with real Playbooks can be manual or explicitly marked as requiring local build artifacts.

## Open Questions

- Should the setting apply only to the final cue item, or should earlier cue-depth context be skipped when a max cue length is active?
- Should Stager emit offsets for every audio asset, or only assets that appear as cue audio?
- What tolerance should Stager use before allowing MP3 Playbooks to emit cue-start offsets?
- Should confidence be actor-visible, or only diagnostic metadata?
