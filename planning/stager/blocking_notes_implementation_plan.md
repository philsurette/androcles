# Blocking Notes Implementation Plan

## Purpose

Blocking is production-specific movement information that actors need to learn alongside their lines. It changes more often than spoken text, may apply to actors who are not speaking, and should have a central source of truth in `production.md`.

Blocking differs from spoken lines:

- it does not require audio recording,
- it should not trigger LineRecorder re-recording requests when only movement changes,
- it should appear in actor-facing artifacts as context,
- it may be relevant to actors who have no nearby dialogue,
- it may serve as an entrance or response cue for another actor.

The source-format contract belongs in [../specs/script_text_format.md](../specs/script_text_format.md).

## Design Summary

Use terse producer-authored blocking syntax in `production.md`:

```text
/LILLIAN: crosses to the window
/LILLIAN, CHRISTINE: cross downstage
/*: everyone freezes
```

This is syntactic sugar for the conceptual form:

```text
@blocking[LILLIAN]: crosses to the window
```

For inline blocking inside long speeches, use the existing `(_..._)` inline direction delimiters with a leading `/target-list:`:

```text
2.1-24 LILLIAN: I'm terribly sorry (_/CHRISTINE: takes LILLIAN's hand_) ... I just didn't know what to do!
```

Inline blocking is syntactic sugar for an inline blocking segment. It should be addressable as `2.1-24:b1`, but it should not affect the speech recording hash.

## Domain Model

Add a blocking production entry kind:

```python
ProductionEntryKind.BLOCKING = "blocking"
```

Standalone blocking entries need:

- associated `production_id` resolved by Stager
- `targets`
- `text`
- `placement` (`before` or `after`)
- `line_no`
- `content_hash`

Role lines with inline blocking need a richer parsed representation than the current plain text plus inline direction splitting. The parser should preserve:

- spoken segments,
- inline directions,
- inline blocking segments.

The existing `RoleBlock.split_block_segments()` should eventually classify `(_..._)` content that starts with `/target-list:` as blocking. Other `(_..._)` content remains an inline stage direction.

## Hashing Policy

Blocking requires separate content hashes, but does not require fine-grained direction-vs-blocking hash families:

- **Line hash**: includes full production entry content, including inline directions and inline blocking. Used for publication history and source integrity.
- **Speech hash**: spoken words only. Used for recording freshness and changed-line Recording Request generation.
- **Non-speech/context hash**: extracted inline directions, inline blocking, standalone directions, and standalone blocking. Used for context/artifact update reporting.

Changing standalone or inline blocking must not create a LineRecorder re-recording request unless spoken text changed too.

Changing inline stage directions should follow the same rule: update context/artifacts, but do not trigger speech re-recording by itself.

## Publication Workflow

The production publication workflow should classify non-speech context changes separately from speech changes. It should still render blocking changes in actor-friendly reports when the changed context segment is blocking:

- `blocking_added`
- `blocking_changed`
- `blocking_removed`

For role lines, publication diff should distinguish:

- speech changed,
- non-speech context changed.

Only speech changes and new speech segments should generate Recording Requests.

Blocking changes should be listed by target role in the publication report:

```text
Blocking changes since v0003:
  LILLIAN
    added 2.1-20: crosses to the window
    changed 2.1-24:b1: takes CHRISTINE's hand
```

## Artifact Policy

### Text Artifacts

Role markdown should include role-relevant blocking by default:

- blocking targeted to the role,
- blocking targeted to `*`,
- inline blocking inside the role's own spoken lines,
- optionally all blocking in the same scene when requested.

Full script markdown should support include/exclude controls:

```sh
./main text --blocking
./main text --no-blocking
```

### Recording Requests

LineRecorder Recording Requests should include nearby role-relevant blocking as context, not recording items.

Recommended manifest additions:

```json
{
  "blocking": [
    {
      "id": "2.1-24:b1",
      "targets": ["CHRISTINE"],
      "text": "takes LILLIAN's hand",
      "placement": "inline"
    }
  ]
}
```

Targeted re-recording requests should only be generated for changed or added speech segments.

### Playbooks

Playbooks should include structured stage directions and structured blocking as text context for Cuemaster.

Directions should be available independently from blocking:

- inline directions attached to the owning line,
- standalone directions in ordered script context,
- direction display metadata separate from any cue-audio behavior.

Blocking should be available as:

- role-scoped blocking timeline,
- inline blocking attached to the owning line,
- scene-level blocking entries with target roles.

Recommended line shape:

```json
{
  "id": "2.1-24",
  "directions": [
    {
      "id": "2.1-24:d1",
      "text": "crossing",
      "placement": "inline"
    }
  ],
  "blocking": [
    {
      "id": "2.1-24:b1",
      "targets": ["CHRISTINE"],
      "text": "takes LILLIAN's hand",
      "placement": "inline"
    }
  ]
}
```

Recommended standalone blocking shape:

```json
{
  "id": "2.1-20",
  "kind": "blocking",
  "targets": ["LILLIAN"],
  "text": "crosses to the window"
}
```

Directions and blocking should not require audio packaging and should not be treated as cue or response audio.

### Cuemaster

Cuemaster should surface directions and blocking as visual rehearsal context with independent display settings:

- display stage directions,
- display blocking,
- blocking scope: selected role / all.

Recommended defaults:

- display stage directions: on,
- display blocking: on,
- blocking scope: selected role.

The display settings should be separate from cue-audio behavior. For example, "display stage directions" should not necessarily mean "play stage direction cue audio."

- show "My Blocking" for the selected role,
- optionally show "All Blocking" for scene context,
- include blocking entries in the browse script view,
- include stage directions in the browse script view,
- allow stage directions and blocking to be toggled independently.

Blocking does not need playback controls.

## Current Status

Implemented:

- parser and domain model support for standalone and inline blocking,
- role-line speech/context hash separation,
- publication diff support for context-only changes,
- Recording Request blocking context,
- LineRecorder blocking display,
- Playbook blocking manifest entries,
- Cuemaster blocking display controls,
- markdown text artifact include/exclude controls.

## Implementation Phases

### Phase 1: Parser And Models

- Add `ProductionEntryKind.BLOCKING`.
- Extend `ProductionEntry` with `targets`.
- Parse standalone blocking shorthand:
  - `<id> /ROLE: text`
  - `<id> /ROLE, ROLE: text`
  - `<id> /*: text`
- Parse the conceptual long form if useful internally:
  - `<id> @blocking[ROLE]: text`
- Add parser tests for locked and draft production scripts.
- Preserve strictness:
  - empty target list fails,
  - malformed target role fails,
  - empty blocking text fails,
  - unclosed inline blocking fails.

### Phase 2: Inline Segmentation

- Add a `BlockingSegment` domain object.
- Extend role-line splitting to classify `(_..._)` content that begins with `/target-list:` as blocking.
- Parse inline target header inside existing inline markers:
  - `(_/ROLE: note_)`
  - `(_/ROLE, ROLE: note_)`
  - `(_/*: note_)`
- Ensure nested inline direction/blocking markers fail.
- Generate sub-ids:
  - `:sN` for speech,
  - `:dN` for inline directions,
  - `:bN` for inline blocking.

### Phase 3: Hash Separation

- Add speech-only normalization for role lines.
- Update recording freshness comparisons to use speech hashes.
- Preserve full line hashes for publication source integrity.
- Add non-speech/context hashes to parsed lines.
- Add tests proving that changing only ordinary `(_..._)` direction content or `(_/ROLE: ..._)` blocking content does not generate a changed-speech Recording Request.

### Phase 4: Publication Diff

- Extend `ProductionSnapshotBuilder` to include:
  - speech hashes,
  - non-speech/context hashes,
  - blocking targets.
- Extend `ProductionChangeAnalyzer` so context-only changes do not become changed-speech recording work.
- Update `publish-production --recording-requests` so only speech changes generate Recording Requests.
- Update publication report rendering to group blocking changes by target role.

### Phase 5: Text And Request Artifacts

- Add include/exclude blocking controls to text artifact generation.
- Add blocking context to Recording Request items.
- Ensure LineRecorder displays blocking context without treating it as something to record.
- Add tests for role-relevant blocking selection.

### Phase 6: Playbook And Cuemaster

- Extend Playbook manifest spec with structured `directions` and `blocking` context.
- Add Stager Playbook generation for inline and standalone direction entries.
- Add Stager Playbook generation for inline and standalone blocking entries.
- Add Cuemaster display settings for stage directions and blocking.
- Keep Cuemaster direction/blocking display settings separate from cue-audio settings.
- Add Cuemaster tests for direction visibility, selected-role blocking, and all-blocking toggles.

## Open Questions

- Whether all-role blocking should use `*` permanently, or whether `ALL` would be easier for non-technical producers.
- Whether other production-note classes need terse syntax later, such as props or acting notes.
- Whether blocking updates should produce a standalone "blocking update" package, or whether regenerating the Playbook is sufficient.
- Whether line-adjacent blocking for other actors should be shown automatically as cues, or only when the actor enables all scene blocking.
