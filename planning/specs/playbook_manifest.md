# Playbook Manifest Specification

This document defines the first app-facing export contract for Cuemaster, an actor rehearsal app. The goal is to give Cuemaster a stable, versioned Playbook to consume without parsing markdown, spreadsheets, or MP4 chapter metadata.

`planning/cuemaster/product_design.md` describes Cuemaster product behavior. This document is the source of truth for the Stager-generated manifest and Playbook structure consumed by Cuemaster.

## Intended Consumer

The primary consumer is Cuemaster, an offline-first actor rehearsal app.

Cuemaster should support:

- Selecting a Playbook.
- Selecting one or more roles to rehearse.
- Showing cue text before each expected response.
- Playing cue audio.
- Playing the actor's expected response audio.
- Showing stage directions and contextual text separately from spoken response text.
- Navigating by part, scene, block, or line.

Cuemaster should not need to understand the source play text format or Stager internals.

## Package Layout

The Playbook should be generated under:

```text
build/<play_id>/app/
```

Initial layout:

```text
build/<play_id>/app/
  manifest.json
  audio/
    segments/
      <ROLE>/
        <segment_id>.wav
    callouts/
      <ROLE>_callout.wav
```

All paths inside `manifest.json` are relative to the directory containing `manifest.json`.

The Playbook should be self-contained where practical. Cuemaster should be able to copy `build/<play_id>/app/` onto a device or into a mobile bundle without needing other files from `build/<play_id>/`.

## Schema Version

The root object includes a numeric schema version:

```json
{
  "schema_version": 1
}
```

Compatibility rules:

- Increment `schema_version` for breaking changes.
- Additive fields may keep the same schema version if existing fields retain their meaning.
- Cuemaster should reject unsupported schema versions explicitly.

## Root Manifest Shape

Proposed root shape:

```json
{
  "schema_version": 1,
  "play": {
    "id": "androcles",
    "title": "Androcles and the Lion",
    "authors": ["George Bernard Shaw"],
    "source": "Project Gutenberg"
  },
  "reading": {
    "type": "solo",
    "build_type": "custom"
  },
  "roles": [],
  "assets": []
}
```

Root fields:

- `schema_version`: Manifest schema version.
- `play`: Source text metadata needed for display.
- `reading`: Reading metadata that affects generated assets.
- `roles`: Rehearsable role payloads.
- `assets`: Optional Playbook-wide asset index.

## Role Payload

Each role entry represents one rehearsable role.

```json
{
  "id": "MEGAERA",
  "display_name": "Megæra",
  "reader": "Anonymous",
  "meta": false,
  "parts": [],
  "lines": []
}
```

Role fields:

- `id`: Stable role id from the play model, e.g. `MEGAERA`.
- `display_name`: Human-facing role name. Prefer reader metadata `role_name` when available, otherwise normalize the role id for display.
- `reader`: Reader name when known.
- `meta`: `true` for special/meta roles if exported.
- `parts`: Optional summary of parts where the role appears.
- `lines`: Ordered rehearsal line items for this role.

Initial Stager Playbook export should include normal actor roles by default. `_NARRATOR`, `_CALLER`, and `_ANNOUNCER` should be excluded from role selection unless a Stager CLI option or later design explicitly includes meta roles.

## Line Item

Each line item describes one expected response opportunity for one role.

```json
{
  "id": "0_5_MEGAERA",
  "part_id": 0,
  "block_id": "0.5",
  "role": "MEGAERA",
  "speaker": "MEGAERA",
  "cue": {
    "speaker": "_NARRATOR",
    "text": "Androcles and Megæra come along the path.",
    "audio": {
      "path": "audio/segments/_NARRATOR/0_4_1.wav",
      "duration_ms": 3600,
      "required": true
    }
  },
  "response": {
    "text": "I won’t go another step.",
    "segments": [
      {
        "id": "0_5_2",
        "text": "I won’t go another step.",
        "audio": {
          "path": "audio/segments/MEGAERA/0_5_2.wav",
          "duration_ms": 2430,
          "required": true
        }
      }
    ]
  },
  "directions": [],
  "previous_roles": [
    "_NARRATOR"
  ]
}
```

Line fields:

- `id`: Stable Cuemaster line id. It should include block identity and role id.
- `part_id`: Numeric play part id, or `null` for no-part preamble material.
- `block_id`: Human-readable block id using dot format, e.g. `0.2`.
- `role`: Role being rehearsed.
- `speaker`: Speaker label for this block. This may differ from `role` if callout/group behavior is involved.
- `cue`: Prompt shown or played before the response.
- `response`: Expected actor response for this role.
- `directions`: Stage directions associated with the response block.
- `previous_roles`: Useful display/context hint, matching the play model's preceding-role concept.

## Cue Payload

Cue payloads are required for every rehearsable non-meta role line. Cue text is used for display; cue audio is used for playback.

```json
{
  "speaker": "ANDROCLES",
  "text": "Well, dear, do you want to see one?",
  "audio": {
    "path": "audio/segments/ANDROCLES/0_8_1.wav",
    "duration_ms": 2100,
    "required": true
  }
}
```

Cue rules:

- The default cue is the preceding non-meta speech block.
- If the preceding block contains only directions, use direction text as context and attach narrator audio.
- If a role has the first rehearsable line in a part, use the part title as the cue; if the part has no title, use the play title.
- Rehearsable role lines must not have `cue: null` in a generated Playbook.
- Cue text may be shortened for rehearsal display, but the manifest should preserve enough metadata to support future full-text display.
- Narrator audio for direction-only cues is required when the direction is used as the cue for a rehearsable line.
- Caller/callout audio is a separate playback asset. Cuemaster may expose a UI preference to play or skip callouts, but callout audio is not a substitute for required cue audio.

Open decision for `planning/cuemaster/cue_generation.md`: whether the manifest should include both `full_text` and `display_text` for cues.

## Response Payload

Response payloads are required for rehearsable lines.

```json
{
  "text": "I won’t go another step.",
  "segments": []
}
```

Rules:

- `response.text` is the concatenated expected spoken text for the selected role in the block.
- `response.segments` preserves segment-level identity and audio assets.
- For inline directions, directions should not be merged into spoken response text.
- Missing response audio should fail Playbook generation.

## Audio Asset

Audio assets are represented consistently anywhere they appear:

```json
{
  "path": "audio/segments/MEGAERA/0_5_2.wav",
  "duration_ms": 2430,
  "required": true
}
```

Fields:

- `path`: Relative path from `manifest.json`.
- `duration_ms`: Audio length in milliseconds.
- `required`: Whether Playbook generation should fail if the asset is missing.

For schema version 1, audio format should remain WAV for segment assets unless a later Playbook packaging design chooses compressed assets.

## Stage Directions

Stage directions should be represented as structured text, not hidden inside response text.

```json
{
  "segment_id": "4_1_2",
  "text": "(_suddenly throwing down her stick_)",
  "placement": "inline"
}
```

Fields:

- `segment_id`: Segment id when available.
- `text`: Direction text exactly as produced by the parser.
- `placement`: `top_level`, `inline`, or `description`.

For actor rehearsal, directions are display/context by default. If a direction is used as the cue for a rehearsable line, its narrator audio is required.

## Simultaneous Lines

Simultaneous speech should preserve the shared segment id and all owners.

```json
{
  "id": "2_73_GLADIATOR-1",
  "block_id": "2.73",
  "role": "GLADIATOR-1",
  "speaker": "GLADIATORS",
  "simultaneous": true,
  "response": {
    "text": "Hail, Caesar!",
    "segments": [
      {
        "id": "2_73_1",
        "owners": ["GLADIATOR-1", "GLADIATOR-2"],
        "text": "Hail, Caesar!",
        "audio": {
          "path": "audio/segments/GLADIATOR-1/2_73_1.wav",
          "duration_ms": 1200,
          "required": true
        }
      }
    ]
  }
}
```

Rules:

- Each rehearsable owner gets its own role line item.
- The segment records all owners.
- The role-specific audio path uses the selected role's segment file.
- Cuemaster may later choose to play other simultaneous owners as context, but schema version 1 does not require that behavior.

## Special Roles

Default Playbook behavior:

- `_NARRATOR`: Excluded as a rehearsable role, but top-level and inline directions may appear as context.
- `_CALLER`: Excluded from role selection. Callout audio may be included as a separate playback asset and controlled by a Cuemaster UI preference.
- `_ANNOUNCER`: Excluded from actor rehearsal packages.

Future options may include:

- `--include-narrator-role`
- `--include-caller`
- `--include-announcer`

Those options should not be added until there is a Cuemaster use case for them.

## Missing Audio Compatibility

Default policy:

- Missing required response audio fails Playbook generation.
- Missing required cue audio fails Playbook generation.
- Narrator audio for direction-only cues is required when the direction is used as a cue.
- Missing callout audio fails only if the Playbook manifest references that callout asset.

The manifest should not silently include paths to missing required files.

Open decision for `planning/stager/missing_audio_policy.md`: exact exception class and Stager CLI flag name for diagnostic Playbook generation.

## Example Minimal Manifest

```json
{
  "schema_version": 1,
  "play": {
    "id": "androcles",
    "title": "Androcles and the Lion",
    "authors": ["George Bernard Shaw"],
    "source": "Project Gutenberg"
  },
  "reading": {
    "type": "solo",
    "build_type": "custom"
  },
  "roles": [
    {
      "id": "MEGAERA",
      "display_name": "Megæra",
      "reader": "Anonymous",
      "meta": false,
      "parts": [0],
      "lines": [
        {
          "id": "0_5_MEGAERA",
          "part_id": 0,
          "block_id": "0.5",
          "role": "MEGAERA",
          "speaker": "MEGAERA",
          "cue": {
            "speaker": "_NARRATOR",
            "text": "Androcles and Megæra come along the path.",
            "audio": {
              "path": "audio/segments/_NARRATOR/0_4_1.wav",
              "duration_ms": 3600,
              "required": true
            }
          },
          "response": {
            "text": "I won’t go another step.",
            "segments": [
              {
                "id": "0_5_2",
                "owners": ["MEGAERA"],
                "text": "I won’t go another step.",
                "audio": {
                  "path": "audio/segments/MEGAERA/0_5_2.wav",
                  "duration_ms": 4200,
                  "required": true
                }
              }
            ]
          },
          "directions": [],
          "previous_roles": ["_NARRATOR"]
        }
      ]
    }
  ],
  "assets": []
}
```

## Implementation Notes

- Build manifest records from the parsed `Play` model, not from markdown output.
- Use existing `BlockId` and `SegmentId` semantics for stable ids.
- Keep manifest-writing code out of `src/build.py`; the Stager CLI should delegate to a Playbook builder.
- Use dataclasses for manifest model classes.
- Prefer one primary class per new file.
- Add tests against in-memory `Play` fixtures before wiring the Stager CLI.
