# Voice Profiles

This document defines the Quince design for actor, role, and actor-role voice profiles. Voice profiles let Stager render non-destructive transformed audio for role characterization, such as higher or deeper voices, brighter or darker tone, subtle gender presentation shifts, ghostly reverberation, or godlike space.

Implementation sequencing belongs in [../stager/voice_profiles_implementation_plan.md](../stager/voice_profiles_implementation_plan.md). This document is the source of truth for profile concepts and future file contracts.

## Goals

- Preserve original actor recordings as the source of truth.
- Let one actor read multiple roles with different rendered voices.
- Let a different actor later read the same role without redefining the role's intended sound.
- Support both explicit transforms and computed baseline-to-target transforms.
- Make FFmpeg the first rendering backend.
- Keep expensive rendering cacheable and reproducible.
- Avoid baking creative effects into LineRecorder exports or canonical segment recordings.

## Non-Goals

- Real-time voice conversion in LineRecorder or Cuemaster.
- ML voice cloning or identity imitation.
- Automatic gender classification.
- Perfect formant-preserving voice conversion in the first implementation.
- Replacing director/producer listening judgment with analysis.

## Core Model

Voice rendering has three distinct layers:

```text
actor recording -> actor/source baseline -> role target -> actor-role render profile -> rendered audio
```

The layers must remain separate.

- **Actor/source baseline** describes the source voice or recording set.
- **Role target** describes the desired role sound independent of who reads it.
- **Actor-role render profile** describes how a specific actor reading a specific role should be transformed.
- **Rendered audio** is generated output and can always be rebuilt from source recordings plus profile config.

This separation handles the main casting use case:

- Phil records `ANDROCLES`, `MEGAERA`, and `LION`.
- Each role can have a different rendered voice.
- Later Alex records `MEGAERA`.
- `MEGAERA` keeps the same role target, but Alex gets a different actor-role transform because Alex's source voice is different.

## Source Audio Layers

Stager should treat audio in layers:

1. **Original recording package content**
   - Raw accepted files exported by LineRecorder.
   - Preserved in import transactions for undo and reprocessing.
   - Never overwritten by voice effects.

2. **Canonical segment audio**
   - The current accepted segment WAVs under the play's segment-audio area.
   - May be denoised or trimmed by explicit import options.
   - Remains the verification and stale-recording source where possible.

3. **Rendered voice-profile audio**
   - Generated build artifacts created by Stager.
   - Used by audioplay, Playbook response audio, and optionally cue audio.
   - Safe to delete and rebuild.

Voice effects belong in layer 3 unless a future command explicitly creates a new canonical recording.

Recording-quality cleanup is a separate concern defined in [audio_cleanup.md](audio_cleanup.md). Voice profiles may consume cleaned audio when a build opts into cleanup, but this spec owns only creative actor/role voice rendering.

## Profile File

The first profile file should be:

```text
plays/<play_id>/voice_profiles.yaml
```

The file is optional. If it is absent, Stager uses canonical segment audio with no role voice rendering.

## Example

```yaml
version: 1

actors:
  phil:
    display_name: Phil
    baseline:
      pitch_center_hz: 115
      speaking_rate_wpm: 155
      brightness: neutral

role_targets:
  ANDROCLES:
    description: Warm, gentle adult male.
    target:
      pitch_center_hz: 130
      speaking_rate_wpm: 145
      tempo_policy:
        mode: preserve_performance
        acceptable_range_wpm: [120, 165]
        max_linked_speed_change: 0.06
      tone: warm

  MEGAERA:
    description: Brighter, sharper adult female presentation.
    target:
      pitch_center_hz: 205
      speaking_rate_wpm: 165
      tempo_policy:
        mode: preserve_performance
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.08
      tone: bright
      preset: female_bright
      max_pitch_shift_semitones: 6
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true

  GOD:
    description: Deep, resonant, otherworldly.
    target:
      pitch_center_hz: 95
      tone: dark
      preset: godlike_hall
      max_pitch_shift_semitones: 5
      tempo_policy:
        mode: preserve_performance
        acceptable_range_wpm: [80, 135]
        max_linked_speed_change: 0.04

cast_profiles:
  phil@ANDROCLES:
    actor: phil
    role: ANDROCLES
    mode: computed

  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
    overrides:
      pitch_shift_semitones: 5.5
      speed_factor: 1.02

  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: explicit
    transforms:
      - type: pitch
        semitones: 1.5
        preserve_tempo: true
      - type: preset
        name: female_bright_subtle
```

## Actor Baselines

An actor baseline describes the source recording voice. It is not a judgment about the actor and should not be inferred as identity metadata beyond this production workflow.

Useful baseline fields:

- `pitch_center_hz`: representative voiced pitch, such as median F0 over a calibration sample or accepted recordings.
- `speaking_rate_wpm`: approximate delivery rate.
- `brightness`: coarse producer-authored label such as `dark`, `neutral`, or `bright`.
- `notes`: optional producer note.

Pitch baseline is the most useful first field because pitch shift is highly source-dependent. Speed baseline is useful but should not drive automatic timing changes by default; acting choices and line rhythm are often more important than global WPM.

Baseline values may be entered manually at first. Later, Stager can add an analysis command that estimates pitch and speaking rate from reference audio or accepted role recordings.

## Role Targets

A role target describes the intended role sound independent of the actor.

Useful target fields:

- `pitch_center_hz`
- `speaking_rate_wpm`
- `tone`
- `preset`
- `max_pitch_shift_semitones`
- `tempo_policy`
- `pitch_strategy`
- `notes`

The role target should be stable across casting changes. Actor-specific differences belong in `cast_profiles`.

`speaking_rate_wpm` and `tempo_policy` are not tempo-normalization instructions. They describe the role's acceptable delivery range so the renderer can decide whether a pitch strategy that also changes speed is safe.

Useful `tempo_policy` fields:

- `mode`: initially `preserve_performance`. This means keep the actor's recorded timing unless a linked speed/pitch strategy stays within the role's tolerance.
- `acceptable_range_wpm`: optional `[min, max]` range for the role's performed speech rate.
- `max_linked_speed_change`: maximum speed factor delta that may be introduced by a linked pitch strategy, such as `0.08` for plus or minus 8%.
- `min_confidence`: optional confidence threshold for using observed tempo analysis in automatic strategy selection.

Useful `pitch_strategy` fields:

- `prefer_linked_speed_pitch_when_safe`: use a linked pitch/speed transform when the resulting tempo stays within policy.
- `fallback`: `preserve_tempo` by default, meaning preserve recorded timing if linked pitch/speed would violate tempo policy.

## Cast Profiles

A cast profile binds one actor to one role. It determines the actual transform used for that actor's recordings.

Supported modes:

- `none`: use canonical segment audio unchanged.
- `explicit`: use the listed transform chain as-is.
- `computed`: compute transform values from the actor baseline and role target, then apply the role target preset and any overrides.

Computed pitch shift:

```text
semitones = 12 * log2(target_pitch_center_hz / actor_pitch_center_hz)
```

The computed result must be clamped by `max_pitch_shift_semitones` when provided. Large pitch shifts can sound artificial, especially without formant-aware processing.

Overrides in a computed profile may replace or clamp computed values. This lets the producer start from a calculated value and tune by ear.

### Tempo-Aware Pitch Strategy

Some pitch-shift methods change both pitch and speed. FFmpeg's portable `asetrate`/`aresample` path can sound cleaner than preserving tempo because it avoids an additional time-stretch step, but it changes the actor's delivery timing. That is acceptable only when the resulting tempo remains within the role's tempo policy.

Tempo analysis is therefore an input to transform selection, not a normalization target. Stager should not decide that a role is "too slow" or "too fast" and correct it automatically. It should answer a narrower question:

```text
Given the observed reading tempo and the pitch shift needed for this actor-role profile,
is it safe to use a linked speed/pitch transform, or must the renderer preserve tempo?
```

For a computed profile, the resolver should:

1. Estimate or load observed speech rate for the actor-role recording set when available.
2. Compute the pitch shift needed to move from source baseline toward role target.
3. Compute the speed factor implied by a linked pitch/speed transform.
4. Predict the post-transform speech rate.
5. Use linked speed/pitch only when:
   - `prefer_linked_speed_pitch_when_safe` is enabled,
   - the observed tempo estimate meets the configured confidence threshold,
   - the speed change is within `max_linked_speed_change`, and
   - the predicted speech rate stays within `acceptable_range_wpm` when that range is configured.
6. Otherwise preserve the actor's recorded tempo and warn when the chosen pitch method may introduce artifacts.

Example:

```text
Observed MEGAERA reading: 178 WPM
Role acceptable range: 145-190 WPM
Linked pitch strategy would speed by 6%
Predicted tempo: 189 WPM
Decision: linked speed/pitch is safe.
```

Counterexample:

```text
Observed MEGAERA reading: 178 WPM
Role acceptable range: 145-190 WPM
Linked pitch strategy would speed by 12%
Predicted tempo: 199 WPM
Decision: preserve tempo and use the independent pitch path.
```

For small roles or sparse recordings, the observed tempo estimate should be low confidence. In that case the safe default is to preserve tempo unless the producer explicitly selects a linked strategy.

## Transform Types

Initial transform types should be small and FFmpeg-native:

- `pitch`: shift pitch by semitones with `strategy: auto`, `linked_speed`, or `preserve_tempo`.
- `speed`: change duration by `speed_factor`.
- `highpass`: remove low frequencies below a cutoff.
- `lowpass`: remove high frequencies above a cutoff.
- `eq`: one or more parametric EQ bands.
- `filter_curve`: named or point-based EQ curve compiled to FFmpeg equalizer filters.
- `compressor`: dynamics compression.
- `reverb`: room or hall effect.
- `delay`: echo/delay effect.
- `gain`: level adjustment.
- `loudnorm`: required final loudness normalization.
- `preset`: expand to a named transform chain.

Presets should compile to ordinary transforms. Presets are convenience names, not a separate rendering system.

## Gender-Presentation Transforms

The project should avoid claims that FFmpeg can truly change the speaker's gender. The practical target is a stylized gender-presentation shift suitable for theatrical characterization.

Useful components for a more feminine presentation:

- modest upward pitch shift,
- high-pass filtering to reduce low-frequency weight,
- EQ presence lift,
- compression tuned for clarity,
- optional brightness curve.

Useful components for a more masculine presentation:

- modest downward pitch shift,
- lower-mid warmth,
- reduced high-frequency brightness when needed,
- compression tuned to preserve weight.

High-quality transformation often requires formant-aware processing. The MVP must use FFmpeg's portable LGPL-compatible baseline, approximating voice presentation with pitch, EQ, and compression. Rubber Band support is a follow-on feature, not part of the MVP.

Gender-presentation presets should participate in tempo-aware pitch strategy selection. A "female bright" or "male warm" preset may suggest an upward or downward pitch shift, but the resolver should still decide whether the pitch shift can be linked with speed based on the actor-role recording's observed tempo and the role target's tempo policy. The goal is to preserve performance timing unless the cleaner linked pitch/speed path remains within the role's acceptable delivery range.

## FFmpeg Capabilities

Quince will not include FFmpeg. Users must install FFmpeg and FFprobe separately, and Stager must verify required filters before rendering. Required voice-profile rendering must work with a normal LGPL-compatible FFmpeg installation.

The first voice-profile implementation should require only filters that are normally present in mainstream FFmpeg builds:

- `aresample`: resample after pitch operations.
- `asetrate`: portable pitch-shift building block.
  - `atempo`: restore tempo after `asetrate` pitch shifts, implement speed changes, and preserve tempo when linked speed/pitch is unsafe.
- `highpass`: low-frequency shaping.
- `lowpass`: high-frequency shaping.
- `equalizer`: parametric EQ bands and filter-curve approximation.
- `acompressor`: dynamics compression.
- `volume`: gain changes.
- `alimiter`: final clipping protection.
- `aecho`: portable first-pass echo/reverb style effects.
- `atrim` and `asetpts`: tail handling, padding workflows, and future batch rendering.
- `concat`: future batch rendering and test fixtures.
- `loudnorm`: required final loudness normalization so rendered voices have consistent perceived level.

Optional quality filters and compile-time features:

- `firequalizer`: useful for smoother filter-curve support, but not required because `equalizer` chains can approximate curves.
- `afir`: useful for convolution reverb with impulse responses, but not required for the first implementation.
- `ladspa` or `lv2`: plugin-host filters; explicitly out of scope for the first implementation because they make installation and support much harder.

Quince must not bundle GPL-enabled FFmpeg or Rubber Band. Rubber Band integration is a follow-on feature and must remain optional user-managed tooling if it is added later.

Stager should provide a capability diagnostic command or render preflight that reports:

- FFmpeg path,
- FFmpeg version,
- FFprobe path,
- required filters present or missing,
- optional filters present or missing,
- whether optional effects filters are available.

The renderer should fail when required filters are missing. It should warn, not fail, when optional filters are missing and a fallback exists.

Stager already contains a Lorick-derived `stager.loudnorm` package that performs two-pass FFmpeg loudness normalization: first measuring input loudness, true peak, loudness range, and threshold, then passing those measured values back into `loudnorm` during normalization. Voice-profile rendering should reuse that package rather than inventing a single-pass `loudnorm` filter string. Before it becomes part of the voice-profile pipeline, the package should be hardened with tests, explicit target presets, and clearer failure handling for unnormalizable audio.

## Audacity Macro Mapping

Existing Audacity macros should be represented as named presets. For example, a producer's "female voice" macro with high-pass, filter curve, and compression can become:

```yaml
presets:
  female_bright:
    transforms:
      - type: highpass
        frequency_hz: 120
      - type: compressor
        threshold_db: -18
        ratio: 2.5
        attack_ms: 5
        release_ms: 80
      - type: filter_curve
        points:
          - [120, -6]
          - [250, -3]
          - [3000, 3]
          - [6000, 4]
      - type: compressor
        threshold_db: -16
        ratio: 2
```

Stager should keep the preset language abstract enough that a later renderer can improve implementation details without changing the producer-facing profile.

## Rendering Strategy

### Per-Segment Rendering

Per-segment rendering runs FFmpeg once for each segment.

Benefits:

- Simple implementation.
- Simple cache invalidation.
- Works naturally with LineRecorder's accepted segment files.
- Easy to parallelize later.

Costs:

- Process startup dominates many tiny files.
- Repeated decode/filter/encode can be slow for large productions.
- Effects with tails, such as reverb and delay, need padding or tail handling per segment.

Per-segment rendering is the recommended first implementation because it is correct, inspectable, and cacheable.

### Role-Batch Rendering

Role-batch rendering concatenates a role's segment sources, applies a profile once, then splits output back into segment files.

Benefits:

- Much faster for many short segments.
- Closer to Audacity macro workflow on a single presegmented role recording.
- Effects and compressors can behave more consistently across the role.

Costs:

- More complex split-boundary accounting.
- Reverb and delay tails can bleed across segment boundaries unless silence padding is inserted.
- Harder to cache individual changed segments.
- More fragile when accepted role audio comes from many separately recorded takes.

Role-batch rendering should be a later optimization. The profile schema should not expose whether rendering is per-segment or batched.

### Full Source Recording Rendering

Rendering the original full-role recording before segmentation is only possible when Stager still has one continuous source recording. It can be efficient and may match existing Audacity workflows, but it does not fit LineRecorder's segment-first package model. It should remain an optional future path, not the default design.

## Cache Model

Rendered files should live under:

```text
build/<play_id>/audio/rendered/<render_profile_id>/<ROLE>/<segment_id>.wav
```

The cache key should include:

- source audio content hash or stable file fingerprint,
- source segment id,
- production segment id and content hash when available,
- actor id,
- role id,
- resolved render profile id,
- resolved transform chain,
- renderer backend and relevant FFmpeg capabilities,
- output format.

If the key is unchanged and the rendered output exists, Stager should skip re-rendering.

Stager should write a render manifest near the generated files so cache decisions are inspectable:

```text
build/<play_id>/audio/rendered/<render_profile_id>/manifest.json
```

## Build Integration

Voice profile rendering should be opt-in at first:

```sh
./main voice-render --play <play_id>
./main voice-render --play <play_id> --role MEGAERA
./main audioplay --play <play_id> --voice-profiles
./main playbook --play <play_id> --voice-profiles
```

Eventually, if `voice_profiles.yaml` exists, release-oriented commands may enable profiles by default with an explicit escape hatch:

```sh
./main playbook --play <play_id> --no-voice-profiles
```

Playbooks should record whether response audio is rendered with a voice profile. The detailed profile contract for Playbook manifests should be added to [playbook_manifest.md](playbook_manifest.md) only when implementation begins.

## Cue Audio Policy

Voice profiles should apply to response audio first.

Cue audio has two possible policies:

- **Rendered cues**: cues use the transformed voice of the cue speaker. This sounds most like the final production and is probably best for rehearsal immersion.
- **Canonical cues**: cues use unmodified segment audio. This can be clearer for rehearsal and avoids compounding effects.

The first implementation should choose one policy per build with a CLI option, defaulting to rendered cues when voice profiles are enabled for Playbook/audioplay output.

## Verification Policy

Text/audio verification should use canonical segment audio by default, not rendered voice-profile audio. Pitch shifting, filtering, reverb, and compression can degrade transcription and make diagnostics harder to interpret.

Rendered audio validation should focus on technical checks:

- output exists,
- duration is reasonable relative to source,
- audio is not silent,
- audio does not clip,
- output path is safe,
- render manifest matches the expected cache key.

## Voice Analysis

Voice-profile analysis may estimate actor and actor-role characteristics, but analysis results should be suggestions and render inputs, not automatic rewrites of producer-authored profile files.

Pitch analysis should estimate a representative voiced pitch center when enough voiced material is available.

Tempo analysis should estimate observed speech rate for the recording set that will be transformed. It should use speech-active duration where possible, not total file duration, because leading/trailing silence and cleanup padding would distort WPM. The text side can start with a simple word count. Later versions may use syllable or alignment-aware measures if needed.

Tempo estimates should include confidence. Suggested first thresholds:

- at least 60 seconds of speech-active audio, or
- at least 150 words, and
- enough segments that one dramatic line does not dominate the estimate.

Below those thresholds, Stager should mark tempo as low confidence and avoid using it to choose linked speed/pitch automatically unless the producer explicitly opts in.

## Diagnostics

Stager should fail for:

- malformed `voice_profiles.yaml`,
- unknown actor ids,
- unknown role ids,
- duplicate actor-role cast profiles,
- computed profiles missing required baseline or target pitch,
- invalid tempo policies,
- invalid transform parameters,
- unsupported transform types,
- unsafe output paths,
- missing FFmpeg for commands that render,
- missing required FFmpeg filters when no fallback exists.

Stager may warn for:

- large pitch shifts after clamping,
- linked speed/pitch rejected because it would move delivery outside the role tempo policy,
- independent pitch selected because tempo confidence is too low for linked speed/pitch,
- unavailable optional FFmpeg filters,
- profile definitions that are not used by the current play.

## Future LineRecorder Integration

LineRecorder should not apply voice profiles during recording. It may eventually:

- include optional actor id metadata in `role_recordings`,
- capture an optional reference line for baseline analysis,
- show the target role voice direction to the actor,
- export baseline analysis hints if they were measured locally.

Those are later workflow improvements. The first implementation should keep voice rendering in Stager.
