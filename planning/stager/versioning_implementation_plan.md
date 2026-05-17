# Versioning Implementation Plan

This is a resumable rollout plan for the versioning design in [../specs/versioning.md](../specs/versioning.md).

The rollout covers three related concerns:

- Package format versions for Playbooks and recording packages.
- Structured production manuscript versions for published `production.md` snapshots.
- Production-version propagation into Playbooks, Recording Requests, and LineRecorder recording export packages.

There is no compatibility requirement for old production-version strings. The only existing production manuscripts are local to this repository and should be migrated to the new structured form.

## Working Rules

- Keep format versioning separate from production manuscript versioning.
- Do not add compatibility shims for old `production_version` forms such as `v0007`.
- Keep `schema_version: 1` only where already emitted for package compatibility during the semantic `format_version` rollout.
- Use structured production versions shaped as `<sequence>@<publication-id>`, such as `7@k9f4p2x8m1qd`.
- Generate `publication_id` values with at least 60 bits of randomness, encoded as a short human-readable token.
- Treat timestamps as metadata only. Do not use timestamps as unique identity.
- Normal build commands must not mutate `production.md`.
- Only publication commands may write `production_version` and `parent_production_version` back to the working manuscript.
- Playbook, Recording Request, audioplay, and other artifact builds must consume production metadata; they must not create new production versions.
- Durable change history belongs in `production-history`, not as a growing comment block in `production.md`.
- Prefer small commits by phase, with tests for each boundary before moving on.

## Phase 0: Audit Current State

- [x] List all Stager manifest writers that emit `schema_version`.
  - Candidate areas: Playbook builder, Recording Request builder, role recordings exporter/importer tests.
  - Audit: Playbook manifests use `src/stager/playbook/app_manifest.py`; Recording Requests use `src/stager/linerecorder/recording_request_manifest.py`; LineRecorder recording export packages are assembled in `linerecorder/src/package/exportRoleRecordings.ts`; Stager import validation checks `schema_version` in `src/stager/linerecorder/role_recordings_importer.py`.
- [x] List all browser import validators that read `schema_version`.
  - Candidate areas: Cuemaster Playbook import validation, LineRecorder Recording Request validation.
  - Audit: Cuemaster validates Playbooks in `cuemaster/src/specs/validatePlaybookManifest.ts`; LineRecorder validates Recording Requests in `linerecorder/src/specs/validateRecordingRequestManifest.ts`; LineRecorder validates local role recording package shape in `linerecorder/src/specs/validateRoleRecordingsManifest.ts`.
- [x] List all Stager import validators that read recording package manifests.
- [x] List all production publication classes that create, store, or restore published versions.
  - Candidate areas: `production_version_store`, `production_publisher`, source rewriter, source resolver.
  - Audit: `ProductionPublisher` creates versions; `ProductionVersionStore` stores/lists/restores versions; `ProductionSourceRewriter` writes locked sources; `ProductionSourceResolver` chooses published versus working sources.
- [x] List existing `plays/*/production.md` files and note whether they already have production-version metadata.
  - Audit: `plays/androcles/production.md`, `plays/solo-androcles/production.md`, and `plays/fairies/production.md` exist; none currently contain `production_version`, `parent_production_version`, or `production_note`.
- [x] Confirm current tests that snapshot manifest JSON examples so expected payloads can be updated deliberately.
  - Audit: key snapshot/assertion tests include `tests/stager/playbook/test_app_manifest.py`, `tests/stager/playbook/test_playbook_builder.py`, `tests/stager/linerecorder/test_recording_request_builder.py`, `tests/stager/linerecorder/test_role_recordings_importer.py`, Cuemaster Playbook normalization/import tests, and LineRecorder Recording Request/export validation tests.

## Phase 1: Shared Version Domain

Goal: one tested Stager module owns structured production versions and package format versions.

- [x] Add a production-version value object.
  - Suggested module: `src/stager/production_publication/production_version.py`.
  - Parse `<sequence>@<publication-id>`.
  - Expose `sequence`, `publication_id`, and string rendering.
  - Reject missing sequence, non-positive sequence, malformed separators, empty ids, and legacy `v0007`-style values.
- [x] Add publication-id generation.
  - Generate at least 60 random bits.
  - Encode as a short lowercase or Crockford Base32 token.
  - Avoid ambiguous characters if using Crockford Base32.
  - Add deterministic injection for tests.
- [x] Add lineage helpers.
  - `is_successor_of(parent)`.
  - `same_sequence_different_publication_id(other)`.
  - `history_directory_name`, such as `0007-k9f4p2x8m1qd`.
- [x] Add package format-version helpers.
  - Parse semantic versions.
  - Map existing `schema_version: 1` to `format_version: 1.0.0` only for package manifests.
  - Compare supported major/minor/patch.
  - Return warning/reject decisions without mixing UI text into the domain helper.
- [x] Add focused tests for production-version parsing, rendering, generation, lineage, and legacy rejection.
- [x] Add focused tests for format-version compatibility decisions.

## Phase 2: Production Markdown Metadata

Goal: `production.md` can carry structured version metadata without weakening script parsing.

- [x] Update production metadata parsing to allow `production_version`.
- [x] Update production metadata parsing to allow `parent_production_version`.
- [x] Update production metadata parsing to allow `production_note`.
- [x] Treat `parent_production_version: none` as first-publication lineage only, or decide to omit parent metadata for first publication.
  - Decision for now: parser accepts `none`; publisher behavior will decide whether first publication writes `none` or omits the field.
- [x] Validate `production_version` with the production-version value object when present.
- [x] Validate `parent_production_version` with the production-version value object when present and not `none`.
- [x] Treat `production_note` as freeform current-version orientation text, not durable history.
- [x] Reject legacy production-version strings with a clear diagnostic.
- [x] Preserve version metadata when parsing and rendering locked output where appropriate.
  - Progress: parser preserves metadata in `ProductionScript.metadata`; publication/source rendering behavior remains in the later publish-command slice.
- [x] Update ScriptWright locking behavior.
  - Draft-to-locked output should not invent a production version.
  - Existing valid production-version metadata should be preserved only if the source remains a published working copy.
  - Force/regeneration behavior should not accidentally claim published lineage.
- [x] Add parser tests for valid metadata.
- [x] Add parser tests for missing metadata on unpublished locked files.
- [x] Add parser tests for malformed and legacy metadata rejection.

## Phase 3: Publication History Storage

Goal: publication history stores structured identities and can detect forks.

- [x] Update history directory naming from `v0007` style to `0007-<publication-id>`.
- [x] Update `current.json` shape.
  - [x] Include `production_version`.
  - [x] Include `sequence`.
  - [x] Include `publication_id`.
  - [x] Include `parent_production_version`.
  - [x] Include `published_at`.
  - [x] Include `change_summary`.
  - Include source/content hash for the published manuscript snapshot if useful for drift detection.
- [x] Update version listing to display structured production versions.
- [x] Update restore behavior to restore the exact published metadata.
- [x] Update diff behavior to report current published version and working manuscript version.
- [x] Detect forked local history.
  - Same sequence, different publication id.
  - Report all colliding history entries.
- [x] Detect out-of-date publish attempts.
  - Publishing now requires the working `production_version` to match the current published version when history exists.
  - Working `production_version` claims an older published version but the file has unpublished changes.
- [x] Add tests for first publication.
- [x] Add tests for normal successor publication.
- [x] Add tests for fork detection.
- [x] Add tests for out-of-date publish rejection.
- [x] Add tests for restore and history listing.

## Phase 4: Publish Command Back-Writing

Goal: producer workflow stays simple: edit `production.md`, publish, let Stager write version metadata.

- [x] Update `publish-production` to allocate the next sequence number from current history.
- [x] Inject publication-id and timestamp generators for deterministic tests.
- [x] Add producer change-summary input.
  - [x] Prompt interactively when the command is attached to a terminal.
  - [x] Accept `--change-summary` for non-interactive use.
  - [x] Require `--allow-empty-summary` if an empty summary is allowed.
- [x] Write `production_version` into the published snapshot.
- [x] Write `parent_production_version` into the published snapshot.
- [x] Write `production_note` into the published snapshot as the concise current-version note.
- [x] Write the full `change_summary` into the version's managed publication `manifest.json`.
- [x] Back-write `production_version`, `parent_production_version`, and `production_note` to working `plays/<play_id>/production.md` after successful publication.
- [x] Ensure failed publication does not mutate the working manuscript.
  - Progress: missing CLI change summary exits before publication and test coverage verifies the failure path; broader failure-after-diff coverage remains useful with later lineage checks.
- [x] Ensure normal build commands never write production-version metadata.
- [x] Ensure Playbook and Recording Request builds never create or back-write production-version metadata.
- [x] Update `production-diff` output to include:
  - [x] current published production version,
  - [x] working production version,
  - [x] whether the working source has unpublished changes,
  - [x] fork warnings when detected.
  - [x] lineage warnings when detected.
- [x] Update CLI tests for successful back-writing.
- [x] Update CLI tests for no mutation on failure.
- [x] Update CLI tests for required or explicitly-empty change summaries.
- [x] Update CLI tests for diagnostics around legacy production-version strings.

## Phase 5: Package Format Versions

Goal: generated packages use semantic `format_version` and validate compatibility consistently.

- [x] Add `format_version: "1.0.0"` to Playbook manifests.
- [x] Add `package_type: "playbook"` to Playbook manifests if not already present.
- [x] Add `format_version: "1.0.0"` to Recording Request manifests.
- [x] Keep `package_type: "recording_request"` in Recording Request manifests.
- [x] Add `format_version: "1.0.0"` to LineRecorder recording export package manifests.
- [x] Keep `package_type: "role_recordings"` in LineRecorder recording export package manifests.
- [x] Keep `schema_version: 1` during this package-format rollout.
- [x] Add Stager tests for generated package version fields.
- [x] Add Cuemaster tests for Playbook import:
  - [x] exact supported version imports cleanly,
  - [x] newer minor version imports with warning,
  - [x] newer major version rejects,
  - [x] missing version rejects unless `schema_version: 1` mapping is deliberately accepted for package manifests.
- [x] Add LineRecorder tests for Recording Request import:
  - [x] exact supported version imports cleanly,
  - [x] newer minor version imports with warning,
  - [x] newer major version rejects.
- [x] Add Stager tests for LineRecorder recording export package import:
  - [x] exact supported version imports cleanly,
  - [x] newer minor version imports with warning,
  - [x] newer major version rejects.

## Phase 6: Production Metadata In Playbooks

Goal: Playbooks identify the published manuscript they came from.

- [x] Add root `production` metadata to Playbook manifest.
  - [x] `version`.
  - [x] `sequence`.
  - [x] `publication_id`.
  - [x] `parent_version`.
  - [x] `source`.
  - [x] `published_at` when source is published.
- [x] Ensure Playbook builds from `--production-source published` include published metadata.
- [x] Ensure Playbook builds from `--production-source working` are visibly marked as working-source builds.
- [x] Ensure Playbook builds do not mutate `production.md`.
- [x] Decide whether working-source Playbooks omit `production.version` or use a synthetic working suffix.
  - Decision: use `source: "working"` and preserve the source `production.version` when present; do not invent a synthetic version.
- [x] Update Cuemaster import model and storage schema for Playbook production metadata.
- [x] Show production version in Cuemaster import/details UI where useful.
- [x] Add Playbook builder tests for published metadata.
- [x] Add Playbook builder tests for working-source metadata.
- [x] Add Cuemaster import tests for production metadata persistence.

## Phase 7: Production Metadata In Recording Packages

Goal: recording workflows preserve the manuscript version that created the request.

- [x] Add production-version metadata to Recording Request manifests.
  - [x] `request.production_version`.
  - [x] `play.version`.
  - [x] Optional structured `production` object if useful for consistency with Playbooks.
- [x] Include production version in Recording Request ids or filenames only if it improves traceability without making names unwieldy.
  - Decision: do not add production versions to ids or filenames yet; keep traceability in manifest metadata.
- [x] Ensure Recording Request builds do not mutate `production.md`.
- [x] Update LineRecorder import model and local storage to keep request production metadata.
- [x] Preserve request production metadata when exporting `role_recordings`.
- [x] Update Stager recording export package import to compare package production version to target published version.
- [x] Decide import policy for production-version mismatch.
  - Decision: warn/report mismatch, then rely on production ids plus content hashes for accept/reject decisions.
- [x] Add Stager tests for Recording Request production metadata.
- [x] Add LineRecorder tests for preserving metadata through import/export.
- [x] Add Stager import tests for matching and mismatched production versions.

## Phase 8: Repository Manuscript Migration

Goal: local `production.md` files use the structured format; no legacy support remains.

- [x] Inventory `plays/*/production.md`.
  - Tracked repository manuscripts: `plays/androcles/production.md`, `plays/solo-androcles/production.md`.
  - Local untracked manuscript observed: `plays/fairies/production.md`.
- [x] For each manuscript with publication history, derive the current structured version from history.
  - No tracked manuscript has tracked publication history.
- [x] For each manuscript without publication history, decide whether to leave version metadata absent or create an initial publication.
  - Decision: leave tracked manuscripts intentionally unpublished until they are explicitly published.
- [x] Rewrite old `production_version` values to `<sequence>@<publication-id>`.
  - No tracked manuscript contains old `production_version` metadata.
- [x] Add `parent_production_version` where known.
  - No tracked manuscript has known parent publication metadata.
- [x] Remove or reject any remaining `v0007`-style metadata.
  - Verified tracked manuscripts have no legacy metadata; parser and CLI tests retain legacy strings only as rejection fixtures.
- [x] Run parser tests against migrated manuscripts.
  - Parsed `plays/androcles/production.md` and `plays/solo-androcles/production.md` successfully.
- [x] Run Stager publication tests.
- [x] Run package generation tests for at least one migrated play.

## Phase 9: Documentation And User-Facing Diagnostics

- [x] Update [../specs/versioning.md](../specs/versioning.md) with any implementation decisions made during rollout.
- [x] Update [../specs/script_text_format.md](../specs/script_text_format.md) with final metadata examples.
- [x] Update [production_publication_workflow.md](production_publication_workflow.md) with final CLI behavior.
- [x] Update [../quince-workflow.md](../quince-workflow.md) to explain production versions in the producer workflow.
- [x] Update [playbook_usage.md](playbook_usage.md) to mention production metadata in Playbooks.
- [x] Add diagnostics for:
  - malformed production versions,
  - legacy production-version strings,
  - forked histories,
  - out-of-date publish attempts,
  - missing change summaries when publishing,
  - package format versions that are too new,
  - package format versions that are missing.
- [x] Ensure diagnostics use `paths.display_path()` or `paths.display_location()` where they mention repository files.

## Phase 10: Final Verification

- [x] Run targeted Stager versioning tests.
- [x] Run targeted Stager publication tests.
- [x] Run targeted Playbook generation tests.
- [x] Run targeted Recording Request and recording package tests.
- [x] Run Cuemaster import tests.
- [x] Run LineRecorder import/export tests.
- [x] Run full Python suite:

  ```sh
  .venv/bin/python run_tests.py
  ```

- [x] Run Cuemaster quality:

  ```sh
  cd cuemaster
  npm run quality
  ```

- [x] Run LineRecorder quality:

  ```sh
  cd linerecorder
  npm run quality
  ```

## Acceptance Criteria

- [x] Stager rejects legacy production-version strings instead of attempting compatibility.
- [x] Stager can publish a first structured production version.
- [x] Stager can publish a normal successor version.
- [x] Stager detects same-sequence/different-publication-id forks.
- [x] Stager detects out-of-date publish attempts.
- [x] Publication commands back-write structured version metadata only after success.
- [x] Normal build commands do not mutate `production.md`.
- [x] Playbook and Recording Request builds do not create new production versions.
- [x] Published version manifests store producer-authored change summaries.
- [x] Working `production.md` contains only current-version metadata and optional concise `production_note`, not a growing change-history log.
- [x] Playbook manifests include `format_version`, `package_type`, and production metadata.
- [x] Recording Request manifests include `format_version`, `package_type`, and production metadata.
- [x] LineRecorder recording export packages include `format_version`, `package_type`, and preserved production metadata.
- [x] Cuemaster rejects newer major Playbook format versions and warns on newer minor versions.
- [x] LineRecorder rejects newer major Recording Request format versions and warns on newer minor versions.
- [x] Stager rejects newer major LineRecorder recording export package versions and warns on newer minor versions.
- [x] Existing repository `production.md` files are migrated or intentionally left unpublished with no legacy version metadata.
