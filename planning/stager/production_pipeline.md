# Production Pipeline Master Plan

## Goal

Move Quince from source-specific `play.txt` parsing to a production-script pipeline:

1. ScriptWright converts supported source formats into locked `production.md`.
2. Stager consumes locked `production.md` instead of `play.txt`.
3. Stager, Cuemaster, and LineRecorder use production ids as canonical script-unit ids.

This plan tracks the three implementation milestones. Each milestone has its own resumable checklist.

## Source Docs

- [../specs/script_text_format.md](../specs/script_text_format.md): Source formats, canonical `production.md`, comments, metadata, and draft/locked state.
- [../specs/production_script_ids.md](../specs/production_script_ids.md): Production id syntax, lifecycle, manifest identity, and content fingerprint rules.
- [../specs/playbook_manifest.md](../specs/playbook_manifest.md): Playbook manifest fields consumed by Cuemaster.
- [../specs/recording_package_manifest.md](../specs/recording_package_manifest.md): Recording Request and recording package fields consumed by LineRecorder and Stager.

## Milestones

- [ ] [scriptwright.md](scriptwright.md): Create ScriptWright to convert current `play.txt` and draft `production.md` into locked `production.md`.
- [x] [production_source_refactor.md](production_source_refactor.md): Refactor Stager build commands to consume locked `production.md` instead of `play.txt`.
- [ ] [production_id_adoption.md](production_id_adoption.md): Push production ids and content hashes through manifests, Cuemaster, and LineRecorder.

## Dependencies

- ScriptWright must land before Stager stops using `play.txt`.
- Stager must consume locked `production.md` before manifest ids can be made fully canonical.
- Cuemaster and LineRecorder should update after manifests contain production ids and content hashes.

## Cross-Cutting Decisions

- The tool name is **ScriptWright**.
- `production.md` is the canonical production script format.
- Draft `production.md` may omit ids or contain provisional ids.
- Locked `production.md` must contain stable production ids on every addressable script unit.
- Lock state is metadata-driven: `production_ids: draft` or `production_ids: locked`.
- Stager build commands consume locked `production.md`.
- Source-format parsing belongs behind ScriptWright.
- Manifests use one script-unit id field: `id` is the production id.
- Parser/build/audio ids may still exist under explicit names such as `block_id`, `segment_id`, or `audio_segment_id`.

## Acceptance Criteria

- [x] A show runner can convert current-format `play.txt` to locked `production.md`.
- [x] A show runner can convert idless or provisional draft `production.md` to locked `production.md`.
- [x] Stager normal build commands do not read `play.txt` directly.
- [x] Stager rejects missing, draft, or idless `production.md` for normal builds.
- [x] Playbook manifests use production ids as canonical script-unit `id` values.
- [ ] Recording Requests and recording packages use production ids as canonical recording item `id` values.
- [ ] Cuemaster and LineRecorder display production ids where they currently display ordinal line numbers.
- [ ] Content hashes detect changed text even if a production id is accidentally reused.
