# Script Text Format

## Purpose

Quince needs a text format that remains easy to edit by hand but is strict enough for Stager, LineRecorder, and Cuemaster to share stable script identity.

This spec defines:

- source script formats used while drafting,
- the canonical Markdown-friendly `production.md` format used after script hardening,
- line-leading comments,
- metadata comment headers,
- the `production_ids` draft/locked lifecycle.

## Format Roles

### Source Scripts

`plays/<play_id>/play.txt` is a draft/source script. ScriptWright may support multiple source formats over time.

The current paragraph-oriented Stager format, documented historically in `src/format.md`, should be treated as an import/source format optimized for lightly edited Gutenberg text. It is not the canonical long-term Quince script format.

Supported source formats:

- Current paragraph-oriented `play.txt`.
- Draft `production.md`, using the production Markdown-friendly grammar but with ids optional or provisional.

Future source formats may be added if ScriptWright can compile them into canonical locked `production.md`.

### Production Scripts

`plays/<play_id>/production.md` is the canonical normalized script format. Draft `production.md` files may be edited directly during development. Locked `production.md` files are the source of stable production ids consumed by Stager.

The production format is strict Markdown-friendly text:

- each addressable script unit occupies exactly one physical line,
- every non-comment, non-blank locked script line starts with a production id,
- draft script lines may omit ids or contain provisional ids that ScriptWright may replace,
- structural headings use Markdown heading markers,
- script order is file order, not id sort order,
- long speeches remain one physical line.

Example:

```text
// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
## I.1-0 SCENE I
I.1-1 @description: A dusty Roman road at noon.
I.1-2 CAPTAIN: I will never submit to the depredations of the barbarous invaders. They will be examined, expelled, exterminated, or exfoliated!
I.1-3 @direction: The soldiers move aside.
I.1-4 CAPTAIN: I will go (_draws sword_) if I must.
```

## Comments

Line-leading `//` starts a comment.

Rules:

- A comment begins only when `//` appears after optional leading whitespace at the start of a physical line.
- Comments are ignored by script parsing, except for recognized metadata comments in the leading metadata block.
- Inline `//` inside dialogue, descriptions, or directions is normal text.
- Comments may appear anywhere, but metadata comments are only recognized in the initial metadata block.

Example:

```text
// This is a comment.
I.1-2 CAPTAIN: The URL is https://example.invalid/script-notes and should remain dialogue text.
```

## Metadata Header

The initial metadata block is a contiguous block of line-leading comments before the first script line.

Metadata comments use:

```text
// key: value
```

Required `production.md` metadata:

```text
// script_format: quince-production-v1
// source_kind: production
// production_ids: draft
```

Allowed `production_ids` values:

- `draft`: ScriptWright may add, replace, or remove production ids while generating locked output.
- `locked`: Stager may consume the file for builds, and ScriptWright must not overwrite ids except through an explicit force or reconciliation command.

The lock state is metadata-driven, not inferred from the presence of ids. Draft files may contain provisional ids, and ScriptWright may replace them.

Parser rules:

- Unknown metadata keys should fail until a use case is defined.
- Duplicate metadata keys should fail.
- Missing required production metadata should fail.
- Unknown `production_ids` values should fail.
- Metadata after the first script line is an ordinary comment and should not change parser behavior.

## Production Line Grammar

Locked production entries have these shapes:

```text
# <production-id> <heading text>
## <production-id> <heading text>
### <production-id> <heading text>
<production-id> @description: <description text>
<production-id> @direction: <stage direction text>
<production-id> <ROLE>: <spoken text>
<production-id> <ROLE>, <ROLE>: <simultaneous spoken text>
```

`<production-id>` is defined by [production_script_ids.md](production_script_ids.md).

Draft `production.md` entries may omit `<production-id>`:

```text
# ACT I
## SCENE I
@description: A dusty Roman road at noon.
CAPTAIN: I will never submit.
CAPTAIN, MEGAERA: We speak together.
```

ScriptWright assigns ids when locking the file.

Heading levels are structural hints for Markdown preview and human scanning. Production id structure remains authoritative for identity; file order remains authoritative for script order.

Reserved lowercase entry labels:

- `@description`
- `@direction`

Role tags:

- Role tags do not start with `@`.
- Role tags should use canonical role ids, such as `CAPTAIN` or `GLADIATOR_1`.
- Multiple comma-separated role tags represent simultaneous speech by multiple roles.
- Whitespace around commas is allowed.

Examples:

```text
# P-0 PROLOGUE
P-14 NARRATOR: In the beginning, the road was empty.
I.1-1 @description: A grove near a Roman road.
I.1-2 MEGAERA: I won't go another step.
I.1-3 ANDROCLES: Oh, not again, dear.
I.1-4 @direction: The lion roars offstage.
I.1-5 GLADIATOR_1, GLADIATOR_2: Hail, Caesar!
```

## Inline Stage Directions

Inline stage directions use the existing `(_` and `_)` delimiters.

Example:

```text
I.1-4 CAPTAIN: I will go (_draws sword_) if I must.
```

Rationale:

- `(_` and `_)` are already used by the current Stager source format.
- The delimiters are visually distinct from normal parenthetical punctuation.
- Markdown previews generally render the text between `_` markers as italic, which is useful for stage directions.

Rules:

- Inline directions may appear inside spoken text.
- Inline directions are addressable sub-line units derived from the containing production id, such as `I.1-4:d1`.
- Spoken text around inline directions is addressable as `:sN` sub-line units.
- Unclosed inline direction delimiters should fail parsing.
- Nested inline directions are not allowed.

## One Physical Line Per Script Unit

Production script lines must not wrap across multiple physical lines.

Allowed:

```text
I.1-2 CAPTAIN: I will never submit to the depredations of the barbarous invaders. They will be examined, expelled, exterminated, or exfoliated!
```

Not allowed:

```text
# Not allowed:
I.1-2 CAPTAIN:
I will never submit to the depredations of the barbarous invaders.
They will be examined, expelled, exterminated, or exfoliated!
```

This is less typographically pretty for long speeches, but it keeps parsing, diagnostics, line identity, and reconciliation substantially simpler.

## Strictness

Production parsing should fail for:

- a locked non-comment, non-blank line without a production id,
- malformed production id syntax,
- duplicate production ids,
- lowercase structural id components,
- unknown reserved entry labels,
- empty role tags,
- empty required text after `:`,
- multiline script entries,
- unclosed or nested inline direction delimiters,
- missing or malformed metadata.

Draft parsing should still be strict about entry grammar, comments, metadata, multiline entries, and inline direction delimiters, but it should permit missing or provisional production ids.

## Relationship To Manifests

Production ids become canonical manifest `id` values for script units.

Parser/build ids may still exist in manifests under explicit implementation names such as `block_id`, `segment_id`, or `audio_segment_id`, but there should be no parallel `production_id` field.

Content hashes are defined in [production_script_ids.md](production_script_ids.md) and should be computed from the normalized production line or sub-line content.

## Open Questions

- Whether source `play.txt` should grow a first-class `quince-source-v1` line-oriented format without production ids.
- Whether heading tags need optional structured levels, such as act, scene, prologue, epilogue, or interlude.
- Whether simultaneous speech needs a display label separate from the participating role ids.
- Whether role metadata should live in script metadata comments or remain in YAML metadata files.
