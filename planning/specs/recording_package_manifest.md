# LineRecorder Recording Package Manifest

This document is the source of truth for file contracts exchanged between Stager, LineRecorder, and future Cuemaster re-record requests.

LineRecorder uses actor-facing language such as "line" in the UI, but manifest identity is segment-based. A recording item maps to one Stager `segment_id` and one expected output audio file. If a displayed source line contains multiple speakable segments, Stager should export multiple recording items with shared context and distinct `segment_id` values.

## Package Types

Schema version 1 defines three local file contracts:

- `role_recording_pack`: Stager to LineRecorder. Contains the recording items an actor should record.
- `role_recordings`: LineRecorder to Stager. Contains accepted WAV recordings and import metadata.
- `rerecord_request`: Cuemaster or Stager to LineRecorder. Future contract for recording a subset of stale or bad segments.

All packages are zip archives with a `manifest.json` at the root. Paths inside manifests are relative to the zip root.

## Role Recording Pack

Stager exports a role-specific recording pack for each actor or role.

Example archive:

```text
CENTURION-recording-pack.zip
├── manifest.json
└── optional/
    └── context files if needed later
```

Example manifest:

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
  "items": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "sequence": 1,
      "display_text": "Halt! Orders from the Captain.",
      "segment_text": "Halt! Orders from the Captain.",
      "cue_text": "A bugle is heard far behind on the road.",
      "stage_directions": ["stopping"],
      "output_path": "audio/segments/CENTURION/0_12_1.wav"
    }
  ]
}
```

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
- `scene_heading`
- `stage_directions`
- `notes`
- `previous_recording`
- `changed`
- `target_duration_ms`
- `target_hesitation_ms`
- `simultaneous`

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

- `complete: true` means every required recording item from the imported pack has an accepted recording.
- `complete: false` is allowed for LineRecorder export, but Stager must treat the package as partial.
- `recordings[].segment_id` is the authoritative identity for placing audio into Stager's segment tree.
- `audio_path` must point to a WAV file inside the zip.
- LineRecorder should export only the current accepted take for each segment by default.

## Re-Record Request

Re-record requests are post-MVP. They should remain file-based and should not require Cuemaster to contain LineRecorder UI.

Example manifest:

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
  "items": [
    {
      "line_id": "0_12_CENTURION",
      "block_id": "0.12",
      "segment_id": "0_12_1",
      "display_text": "Halt! Orders from the Captain.",
      "reason": "outdated",
      "note": "Take should be faster and less angry."
    }
  ]
}
```

LineRecorder should eventually import these files and open directly to the requested recording items.

## Relationship To Playbooks

LineRecorder packages may be incomplete because actors can export partial work. Playbooks are different: Playbook generation remains strict and must fail if required cue or response audio is missing.
