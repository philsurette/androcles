# Production Id Implementation Plan

## Goal

Implement production-script identifiers in Stager so Quince can move cleanly from draft authoring in `play.txt` to stable rehearsal/recording artifacts built from `production.txt`.

The implementation must support two workflows:

- Draft authoring: show runners repeatedly edit `play.txt` and regenerate provisional `production.txt`.
- Production use: show runners lock `production.txt`, after which ids become stable handles used by Stager, LineRecorder, Cuemaster, Playbooks, Recording Requests, and recording packages.

## Source Docs

- [../specs/script_text_format.md](../specs/script_text_format.md): Planned shared spec for `play.txt`, `production.txt`, comments, and metadata headers.
- [../specs/production_script_ids.md](../specs/production_script_ids.md): Production id syntax, lifecycle, manifest identity, and content fingerprint rules.
- [../specs/playbook_manifest.md](../specs/playbook_manifest.md): Playbook manifest fields that consume production ids.
- [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md): Recording Request and recording package fields that consume production ids.

## Decisions To Encode

- `play.txt` is the draft/source script format.
- `production.txt` is the id-bearing production script format.
- `production.txt` uses the same paragraph syntax as `play.txt`, with a production id prefix on every addressable script paragraph.
- Line-leading `//` comments are ignored by the script parser.
- A leading `// key: value` metadata comment block records script metadata.
- `production_ids: draft` means Stager may regenerate `production.txt` from `play.txt`.
- `production_ids: locked` means Stager must not overwrite `production.txt` except through an explicit force or reconciliation command.
- Shared manifests use one script-unit id field: `id` is the production id. There is no parallel `production_id`.
- Parser/build ids may still exist, but only under explicit implementation names such as `block_id`, `segment_id`, or `audio_segment_id`.
- Recording freshness is decided by production id plus normalized content hash, not production id alone.

## Milestone 1: Shared Script Format Spec

- [ ] Create `planning/specs/script_text_format.md`.
- [ ] Move or restate the current `src/format.md` behavior as the formal `play.txt` contract.
- [ ] Define `production.txt` as the same base format plus required production id prefixes.
- [ ] Define line-leading `//` comments.
- [ ] Define a leading metadata comment block.
- [ ] Define required `production.txt` metadata:

```text
// script_format: quince-script-v1
// source_kind: production
// production_ids: draft
```

- [ ] Define allowed `production_ids` values: `draft`, `locked`.
- [ ] Define that comments are only comments when they start a line after optional whitespace; inline `//` inside dialogue is normal text.
- [ ] Define strict parse behavior for malformed metadata, unknown `production_ids` states, duplicate metadata keys, and ids in the wrong source kind.
- [ ] Cross-link `script_text_format.md` from `planning/README.md`.
- [ ] Cross-link `script_text_format.md` from `planning/specs/production_script_ids.md`.

## Milestone 2: Production Id Lifecycle

- [ ] Update `planning/specs/production_script_ids.md` to explicitly describe draft and locked phases.
- [ ] Specify that draft `production.txt` may be regenerated from `play.txt`.
- [ ] Specify that locked `production.txt` is the canonical source for downstream build commands.
- [ ] Specify that Playbook and Recording Request generation should require locked ids unless a deliberate diagnostic flag is provided.
- [ ] Specify CLI behavior for attempts to overwrite locked `production.txt`.
- [ ] Decide command names and options:

```text
./main production-script generate
./main production-script lock
./main production-script status
./main production-script reconcile
```

- [ ] Decide whether `./main text` should read `production.txt` automatically when locked, or require an explicit source selection.

## Milestone 3: Parser Support

- [ ] Add comment stripping for line-leading `//` comments.
- [ ] Add metadata header parsing before script paragraph parsing.
- [ ] Add strict metadata validation.
- [ ] Add production id prefix parsing for `production.txt`.
- [ ] Reject missing production ids in `production.txt`.
- [ ] Reject production ids in `play.txt`, unless the spec explicitly allows them later.
- [ ] Preserve source locations in diagnostics using `paths.display_location()`.
- [ ] Add parser tests for comments, metadata, draft/locked state, valid production ids, missing ids, duplicate ids, malformed ids, and inline `//` dialogue text.

## Milestone 4: Production Script Generation

- [ ] Add a service class that converts parsed `play.txt` into `production.txt`.
- [ ] Generate deterministic ids for headings, descriptions, top-level directions, role blocks, inline direction subunits, and spoken subunits.
- [ ] Generate a metadata header with `production_ids: draft`.
- [ ] Keep generated text editor-friendly and close to source formatting.
- [ ] Refuse to overwrite `production.txt` when it is locked unless the caller passes an explicit force option.
- [ ] Add tests for deterministic output from a fixed `play.txt` fixture.
- [ ] Add tests for repeated draft regeneration.
- [ ] Add tests for locked overwrite failure.

## Milestone 5: Content Fingerprints

- [ ] Define one normalized-content algorithm for production lines and sub-line units.
- [ ] Ignore line wrapping and insignificant whitespace.
- [ ] Preserve role, spoken text, direction text, punctuation, and meaningful ordering.
- [ ] Emit deterministic `sha256:<hex>` hashes.
- [ ] Add tests proving unchanged wrapping preserves hashes.
- [ ] Add tests proving text, role, direction, and punctuation changes alter hashes.
- [ ] Use hashes when deciding whether existing recordings are still valid.

## Milestone 6: Manifest Integration

- [ ] Update Playbook manifest generation so script-unit `id` fields are production ids.
- [ ] Add `content_hash` to Playbook line, response segment, and direction objects.
- [ ] Keep `block_id` and `segment_id` only as explicit parser/audio implementation ids.
- [ ] Update Recording Request generation so recording item `id` is the production segment id.
- [ ] Add `line_id`, `line_content_hash`, and `segment_content_hash` to Recording Request items.
- [ ] Update recording package import/export docs and implementation to preserve the production ids and hashes.
- [ ] Update tests so no manifest emits a parallel `production_id` field.

## Milestone 7: Downstream App Updates

- [ ] Update Cuemaster import validation to treat manifest `id` values as production ids.
- [ ] Update Cuemaster local database schema if it assumes old id shapes.
- [ ] Update Cuemaster UI display points where production ids are useful: script drawer, bookmarks, timing issues, diagnostics.
- [ ] Update LineRecorder import validation to treat recording item `id` as production segment id.
- [ ] Update LineRecorder export to preserve ids and content hashes.
- [ ] Update any tests or fixtures that assume parser-shaped ids are the public ids.

## Milestone 8: Documentation And Migration Cleanup

- [ ] Update `src/format.md` to point to `planning/specs/script_text_format.md` or replace it with a short implementation note.
- [ ] Update user-facing docs with the draft-to-locked workflow.
- [ ] Update AGENTS.md if command names or source-selection rules become sticky project workflow.
- [ ] Remove stale planning language that suggests dual ids or legacy compatibility.
- [ ] Add examples using `Androcles` source text only.

## Acceptance Criteria

- [ ] A show runner can edit `play.txt`, run a command, and get a draft `production.txt`.
- [ ] A show runner can regenerate draft `production.txt` repeatedly while `production_ids: draft`.
- [ ] Stager refuses to overwrite locked `production.txt` without an explicit force/reconcile command.
- [ ] Every addressable production-script paragraph has a production id.
- [ ] Every recordable or direction subunit has a derived production sub-id.
- [ ] Playbook manifests use production ids as canonical script-unit `id` values.
- [ ] Recording Requests and recording packages use production ids as canonical recording item `id` values.
- [ ] Content hashes detect changed text even if an id is accidentally reused.
- [ ] Tests cover parser behavior, generation behavior, lifecycle behavior, and manifest output.

