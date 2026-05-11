# LineRecorder Recording Manifests

This document is the source of truth for file contracts exchanged between Stager, LineRecorder, and future Cuemaster recording request workflows.

LineRecorder uses actor-facing language such as "line" in the UI, but manifest identity is segment-based. A recording item maps to one Stager `segment_id` and one expected output audio file. If a displayed source line contains multiple speakable segments, Stager should export multiple recording items with shared context and distinct `segment_id` values.

## Package Types

Schema version 1 defines two local file contracts:

- `recording_request`: Stager or Cuemaster to LineRecorder. Contains the recording items an actor should record. A request may contain every segment for a role or only selected changed/problem segments.
- `role_recordings`: LineRecorder to Stager. Contains accepted WAV recordings and import metadata.

All packages are zip archives with a `manifest.json` at the root. Paths inside manifests are relative to the zip root.

## Recording Request

A Recording Request is a work order for LineRecorder. Stager exports full-role requests for initial recording and selected-segment requests when a stage manager or director needs changed lines re-recorded. Future Cuemaster workflows may also export selected-segment requests after an actor flags a stale or bad line during rehearsal.

Use "Recording Request" in user-facing UI. Avoid "recordRequest" except as a code identifier when a language convention requires camelCase.

LineRecorder should not require cue audio in a Recording Request. Text context is required enough for MVP. Optional audio references may be added when Stager has suitable assets.

Example archive:

```text
CENTURION-recording-request.zip
├── manifest.json
└── optional/
    ├── cues/
    │   └── context audio if included later
    └── previous/
        └── previous takes if included later
```

Example manifest:

```json
{
  "schema_version": 1,
  "package_type": "recording_request",
  "request": {
    "id": "androcles-CENTURION-full-2026-05-10",
    "kind": "full_role",
    "created_at": "2026-05-10T14:00:00Z",
    "created_by": "stager",
    "notes": "Initial role recording"
  },
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
  "items": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "sequence": 1,
      "display_text": "Halt! Orders from the Captain.",
      "segment_text": "Halt! Orders from the Captain.",
      "cue_text": "A bugle is heard far behind on the road.",
      "cue_speaker": "_NARRATOR",
      "previous_text": "Stand back there.",
      "previous_speaker": "FERROVIUS",
      "next_text": "Who goes there?",
      "next_speaker": "ANDROCLES",
      "section_id": "part-0",
      "section_title": "Act I",
      "stage_directions": ["stopping"],
      "reason": "initial_recording",
      "output_path": "audio/segments/CENTURION/0_12_1.wav"
    }
  ]
}
```

Required request fields:

- `id`: Stable request id for local storage and export traceability.
- `kind`: `full_role`, `selected_segments`, or `rerecord`.
- `created_at`: ISO-8601 timestamp.
- `created_by`: Tool or person that created the request, such as `stager`.

Required recording item fields:

- `line_id`: User-facing stable item id. This may include role identity.
- `block_id`: Stager block id such as `0.12`.
- `segment_id`: Stager segment id and primary audio identity, such as `0_12_1`.
- `sequence`: Role-local display order.
- `display_text`: Text shown to the actor for this recording item.
- `segment_text`: Exact text represented by this `segment_id`.
- `output_path`: Expected path for the accepted WAV in exported recording packages.

Optional recording item fields:

- `cue_text`
- `cue_speaker`
- `previous_text`
- `previous_speaker`
- `next_text`
- `next_speaker`
- `section_id`: Stager/Cuemaster-compatible section id such as `play` or `part-0`.
- `section_title`: Actor-facing section title for navigation and context.
- `scene_heading`
- `stage_directions`
- `reason`: Item-level reason such as `initial_recording`, `script_changed`, `director_request`, `bad_take`, or `actor_request`.
- `notes`
- `previous_recording`: Optional path to a previous take included in the zip.
- `cue_audio`: Optional path to cue/context audio included in the zip.
- `changed`
- `target_duration_ms`
- `target_hesitation_ms`
- `simultaneous`

Rules:

- Recording Requests may be complete full-role requests or constrained requests containing only selected segments.
- Every item must include enough text context for the actor to make a performance choice without opening Cuemaster or a full script.
- `cue_text` should be the most useful immediate cue when one can be identified.
- `previous_text` and `next_text` should provide local dramatic context when available, even if they are not the exact cue.
- `output_path` declares where LineRecorder should place the accepted WAV inside the exported `role_recordings` package.
- Cue audio and previous-take audio are optional context assets. They must not replace the required actor response recording.

## Role Recording Package

LineRecorder exports a role recording package that Stager can import.

Example archive:

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

Example manifest:

```json
{
  "schema_version": 1,
  "package_type": "role_recordings",
  "complete": false,
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
  ],
  "missing_segment_ids": ["0_14_1"]
}
```

Rules:

- `complete: true` means every required recording item from the imported Recording Request has an accepted recording.
- `complete: false` is allowed for LineRecorder export, but Stager must treat the package as partial.
- `recordings[].segment_id` is the authoritative identity for placing audio into Stager's segment tree.
- `audio_path` must point to a WAV file inside the zip.
- LineRecorder should export only the current accepted take for each segment by default.

## Relationship To Playbooks

LineRecorder packages may be incomplete because actors can export partial work. Playbooks are different: Playbook generation remains strict and must fail if required cue or response audio is missing.
