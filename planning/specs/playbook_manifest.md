# Playbook Manifest Specification

This document defines the first app-facing export contract for Cuemaster, an actor rehearsal app. The goal is to give Cuemaster a stable, versioned Playbook to consume without parsing markdown, spreadsheets, or MP4 chapter metadata.

`planning/cuemaster/product_design.md` describes Cuemaster product behavior. This document is the source of truth for the Stager-generated manifest and Playbook structure consumed by Cuemaster.

Permanent production-script identifiers and content fingerprints are defined in `planning/specs/production_script_ids.md`. Playbook manifests use production ids as canonical `id` values for script units; this document defines where they appear but does not redefine the id syntax or fingerprint rules.

Format compatibility and production-version rules are defined in [versioning.md](versioning.md). This document defines the current Playbook payload shape, not the cross-format versioning policy.

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
      <ROLE>/
        <ROLE>.wav
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

New writers should also emit `format_version` as described in [versioning.md](versioning.md). During migration, `schema_version: 1` maps to `format_version: 1.0.0` when the semantic format version is absent.

## Shared Cue Window Presets

Cuemaster cue-length choices and Stager cue-start-offset windows use the machine-readable preset list in `planning/specs/cue_window_presets.json`.

Initial presets:

- `none`: skip cue playback.
- `full`: full cue playback.
- `last_2s`: last 2 seconds.
- `last_5s`: last 5 seconds.
- `last_10s`: last 10 seconds.
- `last_15s`: last 15 seconds.
- `last_20s`: last 20 seconds.

Stager and Cuemaster should each have a small test that checks their local constants against this JSON file. This keeps user-facing cue-length options and Stager-generated `requested_window_ms` offsets from drifting.

## Root Manifest Shape

Proposed root shape:

```json
{
  "schema_version": 1,
  "build": {
    "buildId": "4f84...",
    "buildTimestamp": "2026-05-14T19:12:33Z"
  },
  "production": {
    "source": "published",
    "version": "12@k9f4p2x8m1qd",
    "sequence": 12,
    "publication_id": "k9f4p2x8m1qd",
    "published_at": "2026-05-14T19:10:00Z",
    "change_summary": "Updated Act I blocking.",
    "blocking_changes": ["I-32:b1"]
  },
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
  "sections": [],
  "roles": [],
  "assets": []
}
```

Root fields:

- `schema_version`: Manifest schema version.
- `build`: Build metadata for this generated playbook.
  - `buildId`: Unique immutable build identifier.
  - `buildTimestamp`: ISO 8601 UTC timestamp at which the playbook was generated.
- `production`: Production publication metadata for update decisions and actor-facing version display.
  - `source`: `published` when generated from the current published production, otherwise `working`.
  - `version`: Structured production version label, such as `12@k9f4p2x8m1qd`, when present.
  - `sequence`: Monotonically increasing production version sequence, when present.
  - `publication_id`: Unique publication id for the version sequence, used to detect forks.
  - `parent_version`: Parent production version label, when present.
  - `published_at`: ISO 8601 UTC publication timestamp for published Playbooks.
  - `change_summary`: Optional human-authored summary from publication history for display after updates.
  - `blocking_changes`: Optional list of changed blocking production ids included in this publication.
- `play`: Source text metadata needed for display.
- `reading`: Reading metadata that affects generated assets.
- `sections`: Ordered script navigation sections generated by Stager.
- `context`: Ordered narrator context blocks, including headings, descriptions, and top-level directions.
- `roles`: Rehearsable role payloads.
- `assets`: Optional Playbook-wide asset index.

## Section Payload

Sections are first-class navigation metadata. Cuemaster should use `sections`, not narrator heading context, for scene/section labels and start-location choices.

```json
{
  "id": "part-1",
  "part_id": 1,
  "block_id": "1.0",
  "title": "ACT I",
  "ordinal": 1
}
```

Section fields:

- `id`: Stable section id. Stager uses `part-<part_id>` for numbered parts and `play` for no-part material.
- `part_id`: Numeric play part id, or `null` for no-part material.
- `block_id`: Heading block id when the section has an explicit source heading, otherwise `null` for synthetic sections.
- `title`: Actor-facing section title.
- `ordinal`: Zero-based order in the Playbook.

Every role line's `part_id` should match one section's `part_id`. Synthetic fallback sections are valid when source text has no explicit heading.

## Context Payload

Context entries preserve script material that is not a rehearsable actor response but is still needed for browsing, cue display, cue-depth expansion, direction playback, and blocking display.

```json
{
  "id": "0_4_1",
  "part_id": 0,
  "block_id": "0.4",
  "kind": "description",
  "speaker": "_NARRATOR",
  "text": "Androcles and Megæra come along the path.",
  "content_hash": "sha256:...",
  "audio": {
    "path": "audio/segments/_NARRATOR/0_4_1.wav",
    "duration_ms": 3600,
    "required": true
  }
}
```

Blocking context entries use the same shape but set `kind` to `blocking`, include `targets` and `placement`, and omit `audio`. Blocking is an instruction to actors, not narrator-spoken script audio.

Context fields:

- `id`: Stable segment id for the context audio/text.
- `part_id`: Numeric play part id, or `null` for no-part preamble material.
- `block_id`: Human-readable block id using dot format.
- `kind`: `heading`, `description`, `direction`, or `blocking`.
- `speaker`: `_NARRATOR` for schema version 1 context entries.
- `text`: Display text. Headings should use the cleaned heading text, not raw source markers.
- `content_hash`: Normalized content fingerprint for detecting changed context text behind a reused production id.
- `audio`: Required narrator audio for heading, description, and direction context. Omitted for blocking context.
- `targets`: Role ids affected by a blocking context entry. Present for `blocking`; omitted otherwise.
- `placement`: `before` or `after` for standalone blocking context. Present for `blocking`; omitted otherwise.

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

Initial Stager Playbook export should include normal actor roles by default. `_NARRATOR`, `_CALLER`, and `_ANNOUNCER` should be excluded from actor role selection unless a Stager CLI option or later design explicitly includes meta roles. `_NARRATOR` headings, descriptions, and top-level directions still belong in the top-level `context` array.

## Line Item

Each line item describes one expected response opportunity for one role.

```json
{
  "id": "0-5",
  "content_hash": "sha256:...",
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
        "id": "0-5:s1",
        "segment_id": "0_5_2",
        "content_hash": "sha256:...",
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
  "blocking": [],
  "previous_roles": [
    "_NARRATOR"
  ]
}
```

Line fields:

- `id`: Permanent production-script id for this line, such as `3.2-15`.
- `content_hash`: Normalized content fingerprint for detecting changed text behind a reused production id.
- `part_id`: Numeric play part id, or `null` for no-part preamble material.
- `block_id`: Human-readable block id using dot format, e.g. `0.2`.
- `role`: Role being rehearsed.
- `speaker`: Character who cues this line. This may differ from `role` if callout/group behavior is involved.
  - If this differs from `role`, Cuemaster resolves optional callout audio from the playbook callout index by speaker (usually `audio/callouts/<speaker>/<speaker>.<ext>`).
- Callout playback is speaker-driven; Playbook line entries do not carry a `callout` field.
- `cue`: Prompt shown or played before the response.
- `response`: Expected actor response for this role.
- `directions`: Stage directions associated with the response block.
- `blocking`: Blocking notes associated with the response block.
- `previous_roles`: Useful display/context hint, matching the play model's preceding-role concept.

## Callout Assets

Callout playback assets are optional and are represented only in the top-level `assets` list.

- The playbook uses path-based lookup from line speaker IDs.
- `audio/callouts/<speaker>/<speaker>.<ext>` is the canonical layout for a callout owned by `<speaker>`.
- If there is no matching callout asset for the line `speaker`, Cuemaster should skip callout playback for that line.

Line-level `blocking` items are structured like directions with an additional `targets` list:

```json
{
  "id": "0-5:b1",
  "segment_id": "0_5_2",
  "content_hash": "sha256:...",
  "targets": ["MEGAERA"],
  "text": "crosses downstage",
  "placement": "inline"
}
```

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
- `response.segments[].id` is the production sub-line segment id, such as `3.2-15:s1`.
- `response.segments[].segment_id` may carry Stager's parser/audio segment id, such as `0_5_2`.
- `response.segments[].content_hash` should identify changed recordable text even if the production id was reused accidentally.
- For inline directions, directions should not be merged into spoken response text.
- Missing response audio should fail Playbook generation.

## Audio Asset

Audio assets are represented consistently anywhere they appear:

```json
{
  "path": "audio/segments/MEGAERA/0_5_2.wav",
  "duration_ms": 2430,
  "required": true,
  "cue_start_offsets": [
    {
      "requested_window_ms": 10000,
      "start_ms": 1260,
      "confidence": "boundary"
    }
  ]
}
```

Fields:

- `path`: Relative path from `manifest.json`.
- `duration_ms`: Intended audible content duration in milliseconds, excluding codec/container padding.
- `required`: Whether Playbook generation should fail if the asset is missing.
- `cue_start_offsets`: Optional cue-start offsets for cue playback windows. This field is most useful on cue audio assets; response audio may omit it.

Cue-start-offset fields:

- `requested_window_ms`: Cue window, in milliseconds, from `planning/specs/cue_window_presets.json`. The no-cue preset uses `0`; Cuemaster ignores offsets when cue playback is disabled.
- `start_ms`: Milliseconds from the start of the asset's audible content timeline where playback should begin.
- `confidence`: `exact`, `boundary`, or `fallback`.

Cue-start-offset rules:

- `cue_start_offsets` is optional for backward-compatible additive manifest changes.
- `requested_window_ms` values must come from non-null `window_ms` values in `planning/specs/cue_window_presets.json`.
- `start_ms` must satisfy `0 <= start_ms < duration_ms`.
- `start_ms` is a content-timeline offset, not a codec/container timestamp.
- Offsets must not alter `duration_ms`.
- Stager should emit at most one offset per requested window per asset.

For schema version 1, WAV remains the baseline segment asset format. Stager may add an explicit Playbook packaging option for MP3 assets as a storage/import optimization, but it must remain format-aware: manifest paths must use the encoded extension, `duration_ms` must preserve the source segment's audible content duration, and Cuemaster must consume assets through manifest paths rather than assuming `.wav`.

For compressed assets, encoder delay or padding must not change rehearsal timing. Stager should validate that the packaged audio has not been materially clipped, stretched, or padded with audible silence, but should not treat MP3 frame/container duration drift as the actor-facing timing duration.

MP3 Playbooks may emit `cue_start_offsets` computed from the source WAV asset. These offsets remain content-timeline values; Cuemaster should tolerate small encoder/player seek drift when applying them to compressed assets. The implementation plan is `planning/stager/cue_start_offsets.md`.

## Stage Directions

Stage directions should be represented as structured text, not hidden inside response text.

```json
{
  "id": "4-1:d1",
  "segment_id": "4_1_2",
  "content_hash": "sha256:...",
  "text": "(_suddenly throwing down her stick_)",
  "placement": "inline"
}
```

Fields:

- `id`: Production direction id.
- `segment_id`: Stager parser/audio segment id when available.
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
- `_ANNOUNCER`: Excluded from actor rehearsal packages. Announcer snippets are for audiobook/Librivox preambles and epilogues, not script headings, descriptions, or stage directions.

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
- Missing callout audio is non-fatal unless required by the Playbook generation flow.

The manifest should not silently include paths to missing required files.

Open decision for `planning/stager/missing_audio_policy.md`: exact exception class and Stager CLI flag name for diagnostic Playbook generation.

## Example Minimal Manifest

```json
{
  "schema_version": 1,
  "build": {
    "buildId": "4f84...",
    "buildTimestamp": "2026-05-14T19:12:33Z"
  },
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
          "id": "0-5",
          "content_hash": "sha256:...",
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
                "id": "0-5:s1",
                "segment_id": "0_5_2",
                "content_hash": "sha256:...",
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
