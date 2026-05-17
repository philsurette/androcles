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
- Prefer small commits by phase, with tests for each boundary before moving on.

## Phase 0: Audit Current State

- [ ] List all Stager manifest writers that emit `schema_version`.
  - Candidate areas: Playbook builder, Recording Request builder, role recordings exporter/importer tests.
- [ ] List all browser import validators that read `schema_version`.
  - Candidate areas: Cuemaster Playbook import validation, LineRecorder Recording Request validation.
- [ ] List all Stager import validators that read recording package manifests.
- [ ] List all production publication classes that create, store, or restore published versions.
  - Candidate areas: `production_version_store`, `production_publisher`, source rewriter, source resolver.
- [ ] List existing `plays/*/production.md` files and note whether they already have production-version metadata.
- [ ] Confirm current tests that snapshot manifest JSON examples so expected payloads can be updated deliberately.

## Phase 1: Shared Version Domain

Goal: one tested Stager module owns structured production versions and package format versions.

- [ ] Add a production-version value object.
  - Suggested module: `src/stager/production_publication/production_version.py`.
  - Parse `<sequence>@<publication-id>`.
  - Expose `sequence`, `publication_id`, and string rendering.
  - Reject missing sequence, non-positive sequence, malformed separators, empty ids, and legacy `v0007`-style values.
- [ ] Add publication-id generation.
  - Generate at least 60 random bits.
  - Encode as a short lowercase or Crockford Base32 token.
  - Avoid ambiguous characters if using Crockford Base32.
  - Add deterministic injection for tests.
- [ ] Add lineage helpers.
  - `is_successor_of(parent)`.
  - `same_sequence_different_publication_id(other)`.
  - `history_directory_name`, such as `0007-k9f4p2x8m1qd`.
- [ ] Add package format-version helpers.
  - Parse semantic versions.
  - Map existing `schema_version: 1` to `format_version: 1.0.0` only for package manifests.
  - Compare supported major/minor/patch.
  - Return warning/reject decisions without mixing UI text into the domain helper.
- [ ] Add focused tests for production-version parsing, rendering, generation, lineage, and legacy rejection.
- [ ] Add focused tests for format-version compatibility decisions.

## Phase 2: Production Markdown Metadata

Goal: `production.md` can carry structured version metadata without weakening script parsing.

- [ ] Update production metadata parsing to allow `production_version`.
- [ ] Update production metadata parsing to allow `parent_production_version`.
- [ ] Treat `parent_production_version: none` as first-publication lineage only, or decide to omit parent metadata for first publication.
- [ ] Validate `production_version` with the production-version value object when present.
- [ ] Validate `parent_production_version` with the production-version value object when present and not `none`.
- [ ] Reject legacy production-version strings with a clear diagnostic.
- [ ] Preserve version metadata when parsing and rendering locked output where appropriate.
- [ ] Update ScriptWright locking behavior.
  - Draft-to-locked output should not invent a production version.
  - Existing valid production-version metadata should be preserved only if the source remains a published working copy.
  - Force/regeneration behavior should not accidentally claim published lineage.
- [ ] Add parser tests for valid metadata.
- [ ] Add parser tests for missing metadata on unpublished locked files.
- [ ] Add parser tests for malformed and legacy metadata rejection.

## Phase 3: Publication History Storage

Goal: publication history stores structured identities and can detect forks.

- [ ] Update history directory naming from `v0007` style to `0007-<publication-id>`.
- [ ] Update `current.json` shape.
  - Include `production_version`.
  - Include `sequence`.
  - Include `publication_id`.
  - Include `parent_production_version`.
  - Include `published_at`.
  - Include source/content hash for the published manuscript snapshot if useful for drift detection.
- [ ] Update version listing to display structured production versions.
- [ ] Update restore behavior to restore the exact published metadata.
- [ ] Update diff behavior to report current published version and working manuscript version.
- [ ] Detect forked local history.
  - Same sequence, different publication id.
  - Report all colliding history entries.
- [ ] Detect out-of-date publish attempts.
  - Working `parent_production_version` does not match current published version.
  - Working `production_version` claims an older published version but the file has unpublished changes.
- [ ] Add tests for first publication.
- [ ] Add tests for normal successor publication.
- [ ] Add tests for fork detection.
- [ ] Add tests for out-of-date publish rejection.
- [ ] Add tests for restore and history listing.

## Phase 4: Publish Command Back-Writing

Goal: producer workflow stays simple: edit `production.md`, publish, let Stager write version metadata.

- [ ] Update `publish-production` to allocate the next sequence number from current history.
- [ ] Inject publication-id and timestamp generators for deterministic tests.
- [ ] Write `production_version` into the published snapshot.
- [ ] Write `parent_production_version` into the published snapshot.
- [ ] Back-write both fields to working `plays/<play_id>/production.md` after successful publication.
- [ ] Ensure failed publication does not mutate the working manuscript.
- [ ] Ensure normal build commands never write production-version metadata.
- [ ] Update `production-diff` output to include:
  - current published production version,
  - working production version,
  - whether the working source has unpublished changes,
  - fork or lineage warnings when detected.
- [ ] Update CLI tests for successful back-writing.
- [ ] Update CLI tests for no mutation on failure.
- [ ] Update CLI tests for diagnostics around legacy production-version strings.

## Phase 5: Package Format Versions

Goal: generated packages use semantic `format_version` and validate compatibility consistently.

- [ ] Add `format_version: "1.0.0"` to Playbook manifests.
- [ ] Add `package_type: "playbook"` to Playbook manifests if not already present.
- [ ] Add `format_version: "1.0.0"` to Recording Request manifests.
- [ ] Keep `package_type: "recording_request"` in Recording Request manifests.
- [ ] Add `format_version: "1.0.0"` to LineRecorder recording export package manifests.
- [ ] Keep `package_type: "role_recordings"` in LineRecorder recording export package manifests.
- [ ] Keep `schema_version: 1` during this package-format rollout.
- [ ] Add Stager tests for generated package version fields.
- [ ] Add Cuemaster tests for Playbook import:
  - exact supported version imports cleanly,
  - newer minor version imports with warning,
  - newer major version rejects,
  - missing version rejects unless `schema_version: 1` mapping is deliberately accepted for package manifests.
- [ ] Add LineRecorder tests for Recording Request import:
  - exact supported version imports cleanly,
  - newer minor version imports with warning,
  - newer major version rejects.
- [ ] Add Stager tests for LineRecorder recording export package import:
  - exact supported version imports cleanly,
  - newer minor version imports with warning,
  - newer major version rejects.

## Phase 6: Production Metadata In Playbooks

Goal: Playbooks identify the published manuscript they came from.

- [ ] Add root `production` metadata to Playbook manifest.
  - `version`.
  - `sequence`.
  - `publication_id`.
  - `parent_version`.
  - `source`.
  - `published_at` when source is published.
- [ ] Ensure Playbook builds from `--production-source published` include published metadata.
- [ ] Ensure Playbook builds from `--production-source working` are visibly marked as working-source builds.
- [ ] Decide whether working-source Playbooks omit `production.version` or use a synthetic working suffix.
- [ ] Update Cuemaster import model and storage schema for Playbook production metadata.
- [ ] Show production version in Cuemaster import/details UI where useful.
- [ ] Add Playbook builder tests for published metadata.
- [ ] Add Playbook builder tests for working-source metadata.
- [ ] Add Cuemaster import tests for production metadata persistence.

## Phase 7: Production Metadata In Recording Packages

Goal: recording workflows preserve the manuscript version that created the request.

- [ ] Add production-version metadata to Recording Request manifests.
  - `request.production_version`.
  - `play.version`.
  - Optional structured `production` object if useful for consistency with Playbooks.
- [ ] Include production version in Recording Request ids or filenames only if it improves traceability without making names unwieldy.
- [ ] Update LineRecorder import model and local storage to keep request production metadata.
- [ ] Preserve request production metadata when exporting `role_recordings`.
- [ ] Update Stager recording export package import to compare package production version to target published version.
- [ ] Decide import policy for production-version mismatch.
  - Recommended first behavior: warn/report mismatch, then rely on production ids plus content hashes for accept/reject decisions.
- [ ] Add Stager tests for Recording Request production metadata.
- [ ] Add LineRecorder tests for preserving metadata through import/export.
- [ ] Add Stager import tests for matching and mismatched production versions.

## Phase 8: Repository Manuscript Migration

Goal: local `production.md` files use the structured format; no legacy support remains.

- [ ] Inventory `plays/*/production.md`.
- [ ] For each manuscript with publication history, derive the current structured version from history.
- [ ] For each manuscript without publication history, decide whether to leave version metadata absent or create an initial publication.
- [ ] Rewrite old `production_version` values to `<sequence>@<publication-id>`.
- [ ] Add `parent_production_version` where known.
- [ ] Remove or reject any remaining `v0007`-style metadata.
- [ ] Run parser tests against migrated manuscripts.
- [ ] Run Stager publication tests.
- [ ] Run package generation tests for at least one migrated play.

## Phase 9: Documentation And User-Facing Diagnostics

- [ ] Update [../specs/versioning.md](../specs/versioning.md) with any implementation decisions made during rollout.
- [ ] Update [../specs/script_text_format.md](../specs/script_text_format.md) with final metadata examples.
- [ ] Update [production_publication_workflow.md](production_publication_workflow.md) with final CLI behavior.
- [ ] Update [../quince-workflow.md](../quince-workflow.md) to explain production versions in the producer workflow.
- [ ] Update [playbook_usage.md](playbook_usage.md) to mention production metadata in Playbooks.
- [ ] Add diagnostics for:
  - malformed production versions,
  - legacy production-version strings,
  - forked histories,
  - out-of-date publish attempts,
  - package format versions that are too new,
  - package format versions that are missing.
- [ ] Ensure diagnostics use `paths.display_path()` or `paths.display_location()` where they mention repository files.

## Phase 10: Final Verification

- [ ] Run targeted Stager versioning tests.
- [ ] Run targeted Stager publication tests.
- [ ] Run targeted Playbook generation tests.
- [ ] Run targeted Recording Request and recording package tests.
- [ ] Run Cuemaster import tests.
- [ ] Run LineRecorder import/export tests.
- [ ] Run full Python suite:

  ```sh
  .venv/bin/python run_tests.py
  ```

- [ ] Run Cuemaster quality:

  ```sh
  cd cuemaster
  npm run quality
  ```

- [ ] Run LineRecorder quality:

  ```sh
  cd linerecorder
  npm run quality
  ```

## Acceptance Criteria

- [ ] Stager rejects legacy production-version strings instead of attempting compatibility.
- [ ] Stager can publish a first structured production version.
- [ ] Stager can publish a normal successor version.
- [ ] Stager detects same-sequence/different-publication-id forks.
- [ ] Stager detects out-of-date publish attempts.
- [ ] Publication commands back-write structured version metadata only after success.
- [ ] Normal build commands do not mutate `production.md`.
- [ ] Playbook manifests include `format_version`, `package_type`, and production metadata.
- [ ] Recording Request manifests include `format_version`, `package_type`, and production metadata.
- [ ] LineRecorder recording export packages include `format_version`, `package_type`, and preserved production metadata.
- [ ] Cuemaster rejects newer major Playbook format versions and warns on newer minor versions.
- [ ] LineRecorder rejects newer major Recording Request format versions and warns on newer minor versions.
- [ ] Stager rejects newer major LineRecorder recording export package versions and warns on newer minor versions.
- [ ] Existing repository `production.md` files are migrated or intentionally left unpublished with no legacy version metadata.
