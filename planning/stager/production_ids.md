# Production Id Implementation Plan

## Goal

Implement production-script identifiers so Quince can move cleanly from flexible draft authoring formats to stable rehearsal/recording artifacts built from canonical locked `production.md`.

The implementation must support two workflows:

- Draft authoring: show runners repeatedly edit `play.txt` or draft `production.md` and regenerate/lock `production.md` through PlayIngester.
- Production use: Stager consumes locked `production.md`, where ids are stable handles used by Stager, LineRecorder, Cuemaster, Playbooks, Recording Requests, and recording packages.

## Source Docs

- [../specs/script_text_format.md](../specs/script_text_format.md): Shared spec for source script formats, canonical `production.md`, comments, and metadata headers.
- [../specs/production_script_ids.md](../specs/production_script_ids.md): Production id syntax, lifecycle, manifest identity, and content fingerprint rules.
- [../specs/playbook_manifest.md](../specs/playbook_manifest.md): Playbook manifest fields that consume production ids.
- [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md): Recording Request and recording package fields that consume production ids.

## Decisions To Encode

- `play.txt` is a draft/source script input. PlayIngester may support multiple source formats.
- The current paragraph-oriented `play.txt` format is an import/source format, not the canonical Quince production format.
- PlayIngester is the tool boundary that converts source formats into locked `production.md`.
- Stager build commands should consume locked `production.md`, not `play.txt`.
- Draft `production.md` is also a PlayIngester source format; it may be idless or contain provisional ids.
- Locked `production.md` is the id-bearing canonical production script format.
- `production.md` is line-oriented: one addressable script unit per physical line.
- `production.md` uses Markdown-friendly entries such as `# I-0 ACT I`, `I.1-2 CAPTAIN: ...`, `I.1-3 @direction: ...`, and `I.1-4 @description: ...`.
- Line-leading `//` comments are ignored by the script parser.
- A leading `// key: value` metadata comment block records script metadata.
- `production_ids: draft` means PlayIngester may add, remove, or replace ids.
- `production_ids: locked` means Stager may consume `production.md`, and PlayIngester must not overwrite ids except through an explicit force or reconciliation command.
- Shared manifests use one script-unit id field: `id` is the production id. There is no parallel `production_id`.
- Parser/build ids may still exist, but only under explicit implementation names such as `block_id`, `segment_id`, or `audio_segment_id`.
- Recording freshness is decided by production id plus normalized content hash, not production id alone.

## Milestone 1: Shared Script Format Spec

- [x] Create `planning/specs/script_text_format.md`.
- [x] Define the current `src/format.md` behavior as an import/source format rather than the canonical production format.
- [x] Define `production.md` as a canonical line-oriented format with required production id prefixes when locked.
- [x] Define draft `production.md` as a PlayIngester source format where ids are optional or provisional.
- [x] Define Markdown-friendly production entries for headings, descriptions, directions, role lines, and simultaneous role lines.
- [x] Define line-leading `//` comments.
- [x] Define a leading metadata comment block.
- [x] Define required `production.md` metadata:

```text
// script_format: quince-production-v1
// source_kind: production
// production_ids: draft
```

- [x] Define allowed `production_ids` values: `draft`, `locked`.
- [x] Define that comments are only comments when they start a line after optional whitespace; inline `//` inside dialogue is normal text.
- [x] Define strict parse behavior for malformed metadata, unknown `production_ids` states, duplicate metadata keys, and ids in the wrong source kind.
- [x] Define valid production id syntax, including uppercase alphabetic structural components such as `P`, `E`, `II`, and `INT`.
- [x] Define that script order comes from file order, not production id string sorting.
- [x] Cross-link `script_text_format.md` from `planning/README.md`.
- [x] Cross-link `script_text_format.md` from `planning/specs/production_script_ids.md`.

## Milestone 2: Production Id Lifecycle

- [ ] Update `planning/specs/production_script_ids.md` to explicitly describe draft and locked phases.
- [ ] Specify that draft `production.md` may be regenerated from `play.txt` or edited directly.
- [ ] Specify that locked `production.md` is the canonical source for downstream build commands.
- [ ] Specify that Stager build commands consume locked `production.md` rather than `play.txt`.
- [ ] Specify that PlayIngester is responsible for converting current `play.txt` and draft `production.md` to locked `production.md`.
- [ ] Specify that Playbook and Recording Request generation should require locked ids unless a deliberate diagnostic flag is provided.
- [ ] Specify CLI behavior for attempts to overwrite locked `production.md`.
- [ ] Decide command names and options:

```text
./main ingest play
./main ingest lock
./main ingest status
./main ingest reconcile
```

- [ ] Decide whether PlayIngester should live under `./main ingest ...` or a dedicated command name.

## Milestone 3: Parser Support

- [ ] Add comment stripping for line-leading `//` comments.
- [ ] Add metadata header parsing before script paragraph parsing.
- [ ] Add strict metadata validation.
- [ ] Add production id prefix parsing for `production.md`.
- [ ] Add parsing for line-oriented production entries: Markdown headings, `@description:`, `@direction:`, `ROLE:`, and `ROLE, ROLE:`.
- [ ] Parse draft `production.md` entries with optional/provisional ids for PlayIngester.
- [ ] Parse locked `production.md` entries with required ids for Stager.
- [ ] Accept uppercase alphabetic/alphanumeric structural components in production ids.
- [ ] Reject lowercase structural components.
- [ ] Reject missing production ids in locked `production.md`.
- [ ] Reject production ids in `play.txt`, unless the spec explicitly allows them later.
- [ ] Reject multiline production entries.
- [ ] Preserve source locations in diagnostics using `paths.display_location()`.
- [ ] Add parser tests for comments, metadata, draft/locked state, valid production ids, missing ids, duplicate ids, malformed ids, and inline `//` dialogue text.

## Milestone 4: PlayIngester

- [ ] Add a PlayIngester service class that converts supported source formats into locked `production.md`.
- [ ] Support the current paragraph-oriented `play.txt` format as the first input format.
- [ ] Support draft Markdown-friendly `production.md` as the second input format.
- [ ] Treat ids in draft `production.md` as optional/provisional unless `production_ids: locked`.
- [ ] Generate deterministic ids for headings, descriptions, top-level directions, role blocks, inline direction subunits, and spoken subunits.
- [ ] Preserve director-chosen structural labels such as `P`, `E`, `I`, `II`, and `INT` when generating from source headings where possible.
- [ ] Generate a metadata header with `production_ids: locked` when locking output.
- [ ] Generate one physical production line per addressable script unit.
- [ ] Keep generated text editor-friendly even when source formatting is paragraph-oriented.
- [ ] Refuse to overwrite `production.md` when it is locked unless the caller passes an explicit force option.
- [ ] Add tests for deterministic output from a fixed `play.txt` fixture.
- [ ] Add tests for repeated draft regeneration.
- [ ] Add tests for locked overwrite failure.

## Milestone 4A: Stager Source Refactor

- [ ] Refactor Stager build services to load parsed plays from locked `production.md`.
- [ ] Stop using `play.txt` as the normal source for text, audio, Playbook, Recording Request, and verification builds.
- [ ] Keep source-format parsing behind PlayIngester.
- [ ] Add tests proving Stager rejects draft/idless `production.md` for normal builds.
- [ ] Add tests proving Stager does not silently fall back to `play.txt` when locked `production.md` is required.

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
- [ ] Update Cuemaster UI display points so ordinal line numbers are replaced by production ids without a `line` or `id` prefix.
- [ ] Update LineRecorder import validation to treat recording item `id` as production segment id.
- [ ] Update LineRecorder export to preserve ids and content hashes.
- [ ] Update LineRecorder UI so ordinal line numbers are replaced by production ids without a `line` or `id` prefix.
- [ ] Update any tests or fixtures that assume parser-shaped ids are the public ids.

## Milestone 8: Documentation And Migration Cleanup

- [ ] Update `src/format.md` to point to `planning/specs/script_text_format.md` or replace it with a short implementation note.
- [ ] Update user-facing docs with the draft-to-locked workflow.
- [ ] Update AGENTS.md if command names or source-selection rules become sticky project workflow.
- [ ] Remove stale planning language that suggests dual ids or legacy compatibility.
- [ ] Add examples using `Androcles` source text only.

## Acceptance Criteria

- [ ] A show runner can edit current-format `play.txt`, run PlayIngester, and get locked `production.md`.
- [ ] A show runner can edit idless/provisional draft `production.md`, run PlayIngester, and get locked `production.md`.
- [ ] Stager refuses to overwrite locked `production.md` without an explicit force/reconcile command.
- [ ] Stager build commands consume locked `production.md` rather than `play.txt`.
- [ ] Every addressable production-script line has a production id.
- [ ] Every recordable or direction subunit has a derived production sub-id.
- [ ] Playbook manifests use production ids as canonical script-unit `id` values.
- [ ] Recording Requests and recording packages use production ids as canonical recording item `id` values.
- [ ] Content hashes detect changed text even if an id is accidentally reused.
- [ ] Tests cover parser behavior, generation behavior, lifecycle behavior, and manifest output.
