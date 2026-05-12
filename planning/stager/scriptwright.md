# ScriptWright Implementation Plan

## Goal

Create ScriptWright, the Stager-side tool that converts supported draft script inputs into canonical locked `production.md`.

Initial inputs:

- Current paragraph-oriented `play.txt`.
- Draft Markdown-friendly `production.md`, with ids omitted or provisional.

Output:

- Locked `plays/<play_id>/production.md` with stable production ids and `production_ids: locked`.

## Source Docs

- [../specs/script_text_format.md](../specs/script_text_format.md)
- [../specs/production_script_ids.md](../specs/production_script_ids.md)
- [production_pipeline.md](production_pipeline.md)

## Design Decisions

- ScriptWright owns source-format parsing.
- Stager owns build artifact generation from locked `production.md`.
- Draft `production.md` ids are optional and replaceable.
- The presence of ids does not imply lock state.
- ScriptWright must refuse to overwrite locked `production.md` unless an explicit force or reconcile operation is requested.
- ScriptWright should emit deterministic output for deterministic input.
- Reconcile is intentionally out of MVP. Before locking, users may freely regenerate draft output. After locking, users should edit `production.md` directly while preserving existing ids, or explicitly regenerate with `--force` when replacing ids is acceptable.

## Milestone 1: Package And CLI Boundary

- [x] Create `src/stager/scriptwright/`.
- [x] Add a ScriptWright service class.
- [x] Add CLI entrypoints under `./main scriptwright ...`.
- [x] Add `generate`, `lock`, `status`, and `reconcile` command stubs or decide narrower MVP command names before implementation.
- [x] Use `paths.PathConfig` dependency injection.
- [x] Use `paths.display_path()` and `paths.display_location()` in diagnostics.

## Milestone 2: Production Markdown Parser

- [x] Parse metadata comments from draft and locked `production.md`.
- [x] Parse line-leading `//` comments.
- [x] Parse Markdown headings with optional/provisional ids.
- [x] Parse `@description:` and `@direction:` entries.
- [x] Parse role entries such as `CAPTAIN: text`.
- [x] Parse simultaneous role entries such as `CAPTAIN, MEGAERA: text`.
- [x] Parse inline directions using `(_` and `_)`.
- [x] Reject multiline script entries.
- [x] Reject malformed metadata.
- [x] Reject unclosed or nested inline directions.
- [x] Add focused parser tests.

## Milestone 3: Current play.txt Import

- [x] Wrap the existing paragraph-oriented `play.txt` parser as a ScriptWright source format.
- [x] Convert current `Part`, block, role, description, direction, and simultaneous-line semantics into the production model.
- [x] Preserve existing role ids and metadata where possible.
- [x] Add tests using small current-format fixtures.
- [x] Add one integration fixture based on Androcles source text.

## Milestone 4: Id Assignment

- [x] Generate deterministic structural ids for headings.
- [x] Generate deterministic line ids for headings, descriptions, directions, and role lines.
- [x] Generate sub-line ids for spoken segments and inline directions.
- [x] Support uppercase structural labels such as `P`, `E`, `I`, `II`, and `INT`.
- [x] Reject lowercase structural components in locked output.
- [x] Preserve director-chosen structural labels when source headings make them clear.
- [x] Add tests for id generation, duplicate detection, inserted-line shapes, and roman/prologue/epilogue labels.

## Milestone 5: Locked Output

- [x] Emit `production.md` using the canonical Markdown-friendly grammar.
- [x] Emit required metadata with `production_ids: locked`.
- [x] Emit one physical line per addressable script unit.
- [x] Preserve comments from draft `production.md` where practical.
- [x] Refuse to overwrite locked `production.md` without explicit force.
- [x] Add tests for deterministic output and overwrite behavior.

## Milestone 6: Reconcile Placeholder

- [x] Define minimal reconcile behavior for MVP.
- [x] If full reconciliation is out of scope, make the command fail with a clear "not implemented" diagnostic.
- [x] Document that users can regenerate draft output freely before locking.

## Acceptance Criteria

- [x] `./main scriptwright ...` can convert current-format `play.txt` to locked `production.md`.
- [x] `./main scriptwright ...` can convert idless draft `production.md` to locked `production.md`.
- [x] Locked output contains stable production ids on every addressable line.
- [x] Locked output uses `production_ids: locked`.
- [x] Existing locked output is not overwritten accidentally.
- [x] Tests cover parsing, id assignment, output formatting, and overwrite protection.
