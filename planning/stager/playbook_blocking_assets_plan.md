# Playbook Blocking Diagram Assets Implementation Plan

## Goal

Package blocking diagram JSON into Playbooks so Cuemaster can render stage/blocking snapshots without parsing `production.md`, `staging.txt`, or Stager resolver internals.

The Playbook should include these assets by default when staging data exists, with an explicit opt-out for smaller packages or clients that do not need blocking diagrams.

## Version Decision

- [x] Treat this as a Playbook minor version change: `1.0.0` -> `1.1.0`.
- [x] Rationale: the change adds optional root metadata and optional package files. Existing Cuemaster behavior can continue by ignoring `staging`.
- [x] Do not use a major version unless an existing required field changes meaning, package path resolution changes, or Cuemaster must understand blocking assets to rehearse.

## Target Package Shape

```text
app/
  manifest.json
  audio/
  staging/
    diagram_manifest.json
    icons.svg
    checkpoints/
      scene-1.3-start.json
      scene-1.3-b20.json
    deltas/
      scene-1.3.json
```

`manifest.json` points at the staging bundle:

```json
{
  "format_version": "1.1.0",
  "staging": {
    "included": true,
    "format": "quince.blocking.diagram_bundle",
    "format_version": "1.0.0",
    "manifest_path": "staging/diagram_manifest.json"
  }
}
```

## Design Rules

- [x] Store compact renderer input JSON, not pre-rendered SVGs.
- [x] Use `DiagramState` JSON for checkpoints.
- [x] Use semantic JSON delta operations for diffs; do not use textual JSON Patch or SVG diffs for the MVP.
- [x] Keep Cuemaster ignorant of staging authoring syntax and resolver logic.
- [x] Include enough ids in the bundle for Cuemaster to attach diagrams to script lines:
  - [x] scene id,
  - [x] beat id,
  - [x] production anchor id,
  - [ ] set id when applicable.
- [x] Keep SVG generation as a renderer concern, not a Playbook package concern.

## Phase 1: Spec And Fixtures

- [x] Update `planning/specs/playbook_manifest.md` with the root `staging` object and package layout.
- [x] Update `planning/specs/versioning.md` to record the minor-version decision.
- [ ] Add a machine-readable JSON fixture under `tests/fixtures/playbooks/` or a staging fixture directory showing:
  - [ ] `manifest.json` with `format_version: "1.1.0"`,
  - [ ] `staging/diagram_manifest.json`,
  - [ ] at least one checkpoint,
  - [ ] at least one delta target.
- [ ] Add a small schema or validation helper for `quince.blocking.diagram_bundle`.

## Phase 2: Stager Bundle Builder

- [x] Add a Playbook-facing staging bundle builder under `src/stager/playbook/` or `src/stager/staging/`.
- [x] Inputs:
  - [x] `paths.PathConfig`,
  - [x] parsed `StagingDocument`,
  - [ ] selected checkpoint policy,
  - [x] output directory.
- [x] Outputs:
  - [x] `staging/diagram_manifest.json`,
  - [x] `staging/icons.svg`,
  - [x] checkpoint `DiagramState` JSON files,
  - [x] delta JSON files,
  - [x] summary object for insertion into Playbook `manifest.json`.
- [x] Reuse `StagingExportService`, `StagingParser`, `StagingResolver`, `StagingStateResolver`, and `DiagramStateBuilder`.
- [x] Do not call the SVG renderer from the package builder.

## Phase 3: Checkpoint Policy

- [x] MVP checkpoints:
  - [x] scene start for every scene snapshot,
  - [ ] every set change,
  - [ ] every N beats if a scene has many beats.
- [ ] Default `N` to a conservative value such as `20`.
- [ ] Add an internal threshold that writes a full checkpoint instead of a delta when the delta is larger than the target full state.
- [ ] Make checkpoint spacing configurable in code first; defer CLI knobs unless real packages show a need.

## Phase 4: Delta Operations

- [x] Define the minimal operation set:
  - [x] `upsert_entity`,
  - [x] `remove_entity`,
  - [ ] `set_visible`,
  - [x] `upsert_offstage`,
  - [x] `remove_offstage`,
  - [x] `replace_diagnostics`,
  - [ ] `replace_stage` only for checkpoint/set-boundary transitions.
- [x] Store full replacement entity records for changed entities rather than fine-grained field patches.
- [x] Add deterministic sorting so generated deltas are stable in tests.
- [x] Add a round-trip test: checkpoint + deltas reconstructs the same `DiagramState` as direct resolver output.

## Phase 5: Playbook Builder Integration

- [x] Add `blocking_diagrams: bool = True` or similar to Stager Playbook build options.
- [x] Add CLI opt-out:
  - [x] `./main playbook --no-blocking-diagrams`,
  - [x] `quince build-playbook --no-blocking-diagrams`.
- [x] Decide interaction with the existing `--staging/--no-staging` option:
  - [x] `--no-staging` should skip staging export and imply no blocking diagrams,
  - [x] `--no-blocking-diagrams` should still allow staging export for local Block CLI use.
- [x] If no staging data exists, omit the root `staging` object and do not fail Playbook generation.
- [x] If staging data exists but bundle generation fails validation, fail Playbook generation unless the user opts out.
- [x] Include staging files in both unpacked app output and zipped Playbook output.
- [x] Set Playbook `format_version` to at least `1.1.0` when staging is included.
- [x] Keep `schema_version: 1`.

## Phase 6: Cuemaster Import And Rendering

- [x] Update Cuemaster Playbook import validation to accept `format_version: 1.1.0`.
- [x] Preserve existing newer-minor warning behavior for unsupported future minor versions.
- [x] Add TypeScript types for:
  - [x] root `staging`,
  - [x] diagram bundle manifest,
  - [x] checkpoint records,
  - [x] delta records,
  - [x] delta operations.
- [x] Add an IndexedDB/storage path for staging JSON files.
- [x] Port or implement a Cuemaster diagram-state renderer equivalent to the Python renderer.
- [x] Add a delta applicator and fixture tests proving Python-generated JSON renders expected actors/props.
- [x] Keep the rehearsal UI usable when staging is absent.
- [x] Normalize Playbook `manifest.staging` into the Cuemaster domain model without loading every checkpoint/delta during import.
- [x] Store staging JSON assets alongside other extracted Playbook assets and load them lazily when a diagram is opened.
- [x] Add a resolver that maps a line/blocking note to the best diagram target:
  - [x] exact `blocking.id` / production anchor match,
  - [x] line id match,
  - [x] nearest prior scene checkpoint when no beat target exists.

## Phase 7: UX Integration

- [x] Keep the existing blocking toggle semantics:
  - [x] off means no blocking text is shown in the rehearsal flow,
  - [x] on means concise human-readable blocking notes are displayed inline,
  - [x] role/all scope continues to filter which notes are shown.
- [x] Render visible blocking notes as clickable/tappable controls when a diagram target is available.
- [x] Keep the note text itself visible and readable; the diagram affordance should not replace text blocking.
- [x] Open an on-demand blocking diagram page/sheet from a blocking note:
  - [x] resolve the diagram target for the selected note,
  - [x] load the nearest checkpoint JSON,
  - [x] apply any needed deltas,
  - [x] render full-screen SVG/component from the resulting diagram state.
- [x] Start with on-demand viewing, not always-visible diagrams in the rehearsal line.
- [x] Allow tap/press inspection of actors and props using titles/labels from diagram state.
- [x] Include a clear close/back action that returns to the same rehearsal line and playback state.
- [ ] On mobile, default the diagram page to portrait full-screen with pan/zoom; downstage orientation follows the packaged diagram state/rendering options.
- [x] Preserve existing rehearsal flow if a diagram cannot be rendered.
- [x] If a note has no diagram target, display it as plain text with no broken affordance.
- [ ] Consider a setting to hide blocking diagrams for actors who do not want visual blocking.
- [x] Do not auto-open diagrams during audio playback or auto-advance.

## Phase 8: Tests

- [x] Stager unit tests:
  - [x] bundle manifest generation,
  - [x] checkpoint generation,
  - [x] delta generation,
  - [x] direct state equals checkpoint-plus-delta state,
  - [x] no-staging-data omits Playbook `staging`,
  - [x] opt-out omits Playbook `staging` and files.
- [ ] Stager integration tests:
  - [ ] `./main playbook` includes staging by default for Hamlet fixture,
  - [ ] `./main playbook --no-blocking-diagrams` excludes it,
  - [x] zipped Playbook contains referenced staging files.
- [ ] Cuemaster tests:
  - [x] imports `1.1.0` Playbook,
  - [x] older fixture without `staging` still imports,
  - [x] unsupported newer minor imports with warning,
  - [x] unsupported newer major rejects,
  - [x] blocking toggle still hides/shows text notes without staging assets,
  - [x] visible blocking note opens diagram view when a target exists,
  - [x] non-targeted blocking note remains plain text,
  - [x] diagram view returns to the same rehearsal line,
  - [x] checkpoint and delta fixture renders expected entity positions,
  - [x] packaged SVG icon library renders set-piece and prop icons.

## Acceptance Criteria

- [x] Playbooks with staging data include `manifest.staging` by default.
- [x] Playbooks without staging data remain valid and omit `manifest.staging`.
- [x] Existing rehearsal behavior does not depend on staging assets.
- [x] Existing Cuemaster clients can ignore the added field/files as a newer minor-format package.
- [x] Cuemaster can render a blocking diagram from packaged JSON without source markdown or `staging.txt`.
- [x] Full test suite passes in Stager and Cuemaster.
