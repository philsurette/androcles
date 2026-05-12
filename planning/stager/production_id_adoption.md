# Production Id Adoption Plan

## Goal

Adopt production ids and content hashes across Stager manifests, Cuemaster, and LineRecorder after ScriptWright and the Stager production-source refactor are in place.

## Source Docs

- [../specs/production_script_ids.md](../specs/production_script_ids.md)
- [../specs/playbook_manifest.md](../specs/playbook_manifest.md)
- [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md)
- [production_source_refactor.md](production_source_refactor.md)
- [production_pipeline.md](production_pipeline.md)

## Design Decisions

- Manifest script-unit `id` fields are production ids.
- There is no parallel `production_id` field.
- Implementation ids may remain under explicit names such as `block_id`, `segment_id`, or `audio_segment_id`.
- Recording freshness is decided by production id plus normalized content hash.
- Actor-facing UIs should replace ordinal line numbers with bare production ids.

## Milestone 1: Content Hashes

- [x] Define normalized content hashing for production lines.
- [x] Define normalized content hashing for spoken sub-line segments.
- [x] Define normalized content hashing for inline directions.
- [x] Ignore line wrapping and insignificant whitespace.
- [x] Preserve role, text, direction, punctuation, and meaningful ordering.
- [x] Emit deterministic `sha256:<hex>` strings.
- [x] Add tests proving unchanged wrapping preserves hashes.
- [x] Add tests proving meaningful content changes alter hashes.

## Milestone 2: Playbook Manifest

- [x] Update Playbook line `id` values to production line ids.
- [x] Update response segment `id` values to production sub-line ids.
- [x] Update direction `id` values to production direction ids.
- [x] Add `content_hash` to line, response segment, and direction objects.
- [x] Keep parser/audio ids only under explicit fields such as `block_id` and `segment_id`.
- [x] Add tests ensuring no `production_id` field is emitted.
- [x] Add tests validating production ids and content hashes are present.

## Milestone 3: Recording Request And Recording Package

- [x] Update Recording Request item `id` to production segment id.
- [x] Add parent `line_id`.
- [x] Add `line_content_hash` and `segment_content_hash`.
- [x] Preserve ids and hashes in LineRecorder recording packages.
- [x] Make Stager import validate ids and hashes before accepting recordings as current.
- [x] Add tests for stale recording rejection when text changes behind a reused id.

## Milestone 4: Cuemaster

- [x] Update import validation for production ids and content hashes.
- [x] Update local database schema if it assumes parser-shaped ids.
- [x] Replace ordinal line-number display with bare production ids.
- [x] Update script drawer rows.
- [x] Update bookmark rows.
- [x] Update timing issue rows.
- [ ] Update diagnostics/import errors.
- [x] Add tests for import and display behavior.

## Milestone 5: LineRecorder

- [ ] Update Recording Request import validation for production ids and content hashes.
- [ ] Update recording item identity to use production segment ids.
- [ ] Replace ordinal line-number display with bare production ids.
- [ ] Preserve ids and hashes on export.
- [ ] Add tests for import, display, and export behavior.

## Milestone 6: Documentation And Fixtures

- [ ] Update manifest examples to production ids.
- [ ] Update user-facing docs to explain production ids.
- [ ] Update Androcles fixtures to include locked `production.md`.
- [ ] Remove planning language that suggests dual ids or legacy id migration.

## Acceptance Criteria

- [x] Playbook manifests use production ids as canonical ids.
- [x] Recording Requests use production segment ids as canonical recording item ids.
- [x] Recording packages preserve production ids and content hashes.
- [x] Stager detects stale recordings when text changes behind a reused id.
- [x] Cuemaster displays production ids instead of ordinal line labels.
- [ ] LineRecorder displays production ids instead of ordinal line labels.
- [ ] Tests cover Stager manifest generation, recording package import/export, Cuemaster import/display, and LineRecorder import/export.
