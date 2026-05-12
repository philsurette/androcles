# Production Script Identifiers

## Purpose

Production scripts change during rehearsal. Directors may add, delete, move, or revise lines after actors have started recording and rehearsing. Quince needs permanent, concise, human-readable identifiers for every addressable script unit so Stager, LineRecorder, and Cuemaster can agree on what changed and what must be recorded again.

These identifiers are additive to the current play text format. They should become visible wherever an id helps actors, directors, or maintainers discuss a specific script unit.

The shared script-format source of truth is `planning/specs/script_text_format.md`. That spec defines the exact `production.md` syntax, including line-leading `//` comments, one physical line per script unit, and the `production_ids: draft` or `production_ids: locked` metadata header. The Stager implementation plan is `planning/stager/production_ids.md`.

## Source Artifacts

`play.txt` remains the raw import/source artifact.

Stager should add an initial script-hardening step that reads `play.txt` and creates an editable production script artifact:

```text
plays/<play_id>/production.md
```

`production.md` should keep a text-editor-friendly line-oriented format, but every addressable script unit must have an explicit production id. While `production.md` is marked `production_ids: draft`, Stager may regenerate it from `play.txt`. Once it is marked `production_ids: locked`, it becomes the default source for subsequent Stager builds. `play.txt` remains useful for import, comparison, or re-hardening, but it should not silently overwrite locked production ids.

The artifact name is **Production script**. The filename is `production.md`. The name matches theatre vocabulary and signals that this is the director-maintained script used after initial import.

The draft/locked state belongs in a leading metadata comment block:

```text
// script_format: quince-production-v1
// source_kind: production
// production_ids: draft
```

The lock-state line is metadata expressed as a comment, not a new script paragraph type.

## Production Script Format

`production.md` should remain easy to edit with ordinary text editors. Each addressable script unit occupies one physical line, and the id is visible at the start of that line.

Examples:

```text
# I-0 ACT I
## I.2-0 SCENE II
I.2-15 CAPTAIN: I will go (_draws sword_) if I must.
I.2-16 @direction: The soldiers move aside.
I.2-17 @description: A dusty Roman road at noon.
### I.2-18 Scene transition
```

Stager should parse the leading production id, then parse the remainder of the line using the canonical production entry grammar in `planning/specs/script_text_format.md`. This keeps the format human-readable while avoiding a separate sidecar id map that can drift from the text.

Headings are addressable lines too. Use `-0` for the heading that establishes a structure when that is natural, then number performed script units from `-1`.

Inline stage directions normally do not need explicit ids in the text because Stager can derive `:dN` and `:sN` ids from the containing line during parsing. If a future workflow needs manually pinned inline ids, that should be added as a small extension to inline direction syntax rather than by introducing a separate manifest-only identity.

## ID Syntax

Production ids have three layers:

```text
<structure>-<line><revision>:<segment>
```

Only the structure and line id are required.

Examples:

```text
3.2-15       line 15 in scene 2 of act 3
P-14         line 14 in the prologue
P.1-3        line 3 in scene 1 of the prologue
II.3-12      line 12 in scene 3 of act II
3.2-15.1     inserted line after 3.2-15
3.2-15a      revised version of 3.2-15
3.2-15.1a    revised version of inserted line 3.2-15.1
3.2-15:s1    first spoken segment inside line 3.2-15
3.2-15:d1    first stage direction inside line 3.2-15
3.2-15:s2    second spoken segment inside line 3.2-15
```

Rules:

- `.` inside the structure identifies hierarchy, such as act/scene.
- Each structural component may be numeric, such as `3`, or uppercase alphabetic/alphanumeric, such as `P`, `E`, `II`, or `INT1`.
- `-` separates structural location from the line id.
- `.` after the line id identifies inserted lines.
- A trailing lowercase letter identifies a text revision of the line.
- `:` identifies a sub-line unit.
- `sN` identifies spoken segment `N` inside the line.
- `dN` identifies stage direction `N` inside the line.
- Use uppercase alphabetic structural components. Do not use lowercase structural components, because lowercase is reserved for revision and sub-line suffixes.
- Roman numerals are allowed as structural labels, but they are labels, not numbers.
- Script order comes from `production.md` file order and manifest sequence/order fields, not from sorting production ids as strings.

## Structural IDs

The structure portion should be explicit enough for a director's working script.

Examples:

```text
P-1      prologue line 1
P.1-3    prologue, scene 1, line 3
1-0      act 1 heading
1-1      act 1 line 1, if no scenes are defined
1.2-0    act 1, scene 2 heading
1.2-15   act 1, scene 2, line 15
I.2-15   act I, scene 2, line 15, if roman numerals are preferred
E-1      epilogue line 1, if epilogue is retained as a named structure
INT-2    interlude line 2
```

Stager should support a play with only top-level parts and a play with director-added scenes. Structural ids are director-facing labels, not ordering instructions. If scenes are added later, existing production ids should not be renumbered automatically without an explicit reconciliation operation.

## Line Identity

The line id identifies an addressable production-script unit. A line may be:

- a heading,
- a description,
- a standalone stage direction,
- a spoken role block,
- a block containing spoken text and inline directions.

The line id is the permanent identity used for discussion, change tracking, and production manifests. It should not change just because the line moves.

## Sub-Line Identity

Sub-line ids are used when a single line contains multiple recordable or addressable units.

Example source line:

```text
3.2-15 CAPTAIN. I will go (_draws sword_) if I must.
```

Addressable units:

```text
3.2-15      whole line
3.2-15:s1   CAPTAIN: I will go
3.2-15:d1   (_draws sword_)
3.2-15:s2   CAPTAIN: if I must
```

Sub-line ids should be stable within a line revision. If the line is revised from `3.2-15` to `3.2-15a`, sub-line ids may be regenerated under the revised line:

```text
3.2-15a:s1
3.2-15a:d1
3.2-15a:s2
```

This keeps the permanent identity at the line level while still allowing LineRecorder and Stager to address individual recordable segments.

## Edits And Revisions

### Modified Lines

If text changes in a way that may affect recording or rehearsal, create a revised id:

```text
3.2-15   original
3.2-15a  first revised text
3.2-15b  second revised text
```

The original id remains in history. Active manifests should reference the active revised id.

### Inserted Lines

If a line is added after `3.2-15`, use:

```text
3.2-15.1
```

Additional insertions after the same line use:

```text
3.2-15.2
3.2-15.3
```

If an inserted line is revised:

```text
3.2-15.1a
```

### Deleted Lines

`production.md` should contain the active production script, not required tombstones. Deleted lines may be removed from `production.md`.

If a new line is later inserted at the same location, authors should prefer an inserted or revised id such as `3.2-15.1` or `3.2-15a`, but Quince correctness must not depend on authors remembering that convention. Stager should treat production id plus normalized text fingerprint as the practical identity for recording freshness. If `3.2-15` disappears and later reappears with different text, Stager should detect the changed fingerprint and require fresh recording even though the production id was reused.

There is no plan to implement a separate change ledger unless a clear need emerges. Historical deletion records should not be required in the editable Production script.

### Moved Lines

Moved lines keep their production id. Ordering metadata should describe the current order separately from identity. Moving a line should not require re-recording unless text or recordable directions changed.

## Manifest Requirements

All shared manifests that reference script units should use production ids as the canonical `id` for those script units. Do not add parallel `production_id` fields. Parser, build, or audio identities may still appear when useful, but they must use explicit names such as `block_id`, `segment_id`, or `audio_segment_id`.

Manifests should also include normalized content fingerprints for script units that drive recording or rehearsal freshness. Production ids are the human-facing stable handles; content fingerprints are the safety net for accidental id reuse or unmarked text changes.

Fingerprint rules:

- Compute fingerprints from normalized script content, not from audio.
- Ignore insignificant formatting that does not affect performance, such as line wrapping.
- Preserve meaningful text, role, direction, and punctuation changes.
- Use deterministic strings, such as `sha256:<hex>`.
- Compare production id plus content fingerprint before reusing existing recordings or marking a line unchanged.

### Playbook Manifest

Playbook line entries should include:

```json
{
  "id": "3.2-15",
  "content_hash": "sha256:...",
  "block_id": "parser-block-id",
  "response": {
    "segments": [
      {
        "id": "3.2-15:s1",
        "segment_id": "parser-segment-id",
        "content_hash": "sha256:..."
      }
    ]
  },
  "directions": [
    {
      "id": "3.2-15:d1",
      "segment_id": "parser-segment-id",
      "content_hash": "sha256:..."
    }
  ]
}
```

In this shape, `id` is the production id. There is intentionally no separate `production_id`.

### Recording Request Manifest

Recording items should use the production segment id as `id` and may include the parent line id:

```json
{
  "id": "3.2-15a:s1",
  "line_id": "3.2-15a",
  "line_content_hash": "sha256:...",
  "segment_id": "parser-segment-id",
  "segment_content_hash": "sha256:..."
}
```

LineRecorder should display production ids anywhere it would otherwise display ordinal line numbers.

### Recording Package Manifest

LineRecorder exports should carry the same production ids back to Stager so Stager can import recordings without relying only on filenames or current ordering.

## Display Requirements

Stager should display production ids in generated scripts and diagnostics.

LineRecorder should show production ids for recording items anywhere it would otherwise display ordinal line numbers, such as `Line 1` or `Line 2`.

Cuemaster should show production ids anywhere it would otherwise display ordinal line numbers. Do not prefix the value with `line`, `id`, or similar label; the id format is recognizable on its own. Reasonable display points:

- script drawer rows,
- bookmark and timing issue rows,
- the current line/position indicator,
- diagnostics and import errors.

## Filename Safety

Production ids are JSON-safe as strings. For filenames, replace `:` with `_` or another safe separator:

```text
3.2-15:s1 -> 3.2-15_s1.wav
```

Do not rely on filename transformation as identity. Manifests should carry the canonical id string.

## Stager Implementation Notes

The first implementation should be strict:

- If `production.md` exists, Stager should use it by default.
- If `production.md` is missing, Stager may parse `play.txt` only for commands that explicitly allow raw input.
- A hardening command should generate `production.md` and fail if it cannot assign deterministic ids.
- A future reconciliation command should compare raw/new script text against `production.md`, preserve existing ids when possible, and suggest inserted/revised/deleted ids.
- Stager should not decide that existing audio is reusable from production id alone. It should also compare the relevant content fingerprint.

## Closed Decisions

- Prologues, epilogues, interludes, and roman-numeral acts may use uppercase structural labels such as `P`, `E`, `INT`, `I`, and `II`.
- There is no plan to implement a separate change ledger unless the need becomes clear.
- Actor-facing UIs should replace ordinal line numbers with production ids wherever line numbers are currently displayed.
