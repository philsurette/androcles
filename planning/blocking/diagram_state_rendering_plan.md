# Diagram State Rendering Design And Implementation Plan

## Recommendation

Do this before continuing with new blocking features.

The current Python renderer goes directly from `ResolvedSnapshot` to SVG. That is fine for the prototype, but it will become the wrong foundation if Playbooks need many blocking diagrams and Cuemaster needs to render them efficiently.

The next architecture should be:

```text
staging file / production.md blocking
  -> parsed staging model
  -> resolved stage/set/scene/beat state
  -> diagram state JSON
  -> renderer adapter
       -> SVG in Python block CLI
       -> SVG or native view in Cuemaster
       -> PNG/print/other output later
```

Stager/block should own all semantic compilation: parsing, set selection, location resolution, beat application, collision offsets, icon choice, elevation classification, and diagnostics. Renderers should consume a stable, already-resolved diagram JSON contract and draw it.

## Why This Is Better

### Smaller Playbooks

Full SVG repeats a lot of markup:

- XML document structure
- CSS
- icon symbol definitions
- grid line elements
- repeated class and attribute names
- repeated side-panel labels

Current Hamlet SVGs are around 10-12 KB each. If production diagrams become 20-25 KB and a Playbook carries 1000+ diagrams, that becomes expensive quickly.

Diagram state JSON can be smaller because it stores only semantic drawing state:

- stage size once per checkpoint
- entity ids
- resolved coordinates
- icon ids
- visibility/offstage state
- title/label metadata

It also enables checkpoint/delta packaging later, where Stager stores full diagram states only at checkpoints and compact semantic deltas for intermediate directions.

### More Efficient Runtime Updates

Cuemaster can keep one rendered diagram mounted and update changed entities:

- move actor `HAM`
- hide prop `sword`
- update facing label
- show offstage entry

That avoids loading and replacing a complete SVG document for every blocking direction.

### More Flexible Rendering

If Playbooks store final SVGs, the visual design is baked into the package. If Playbooks store diagram state, Cuemaster can improve rendering later without regenerating every Playbook:

- portrait vs landscape
- mobile-specific label density
- larger tap targets
- dark mode
- zoom/pan
- actor-only mode
- prop visibility toggles
- accessibility titles
- future canvas/WebGL/VR renderers

### Less Brittle Than SVG Diffs

Textual or DOM-level SVG diffs are coupled to renderer implementation details. They can break when the Python renderer changes element ordering, grouping, formatting, CSS class names, or icon layout.

Diagram state deltas are semantic:

```json
{"entity_id": "sword", "visible": false}
```

That survives renderer refactors.

### Keeps Cuemaster Simple

Cuemaster should not parse authoring syntax such as:

```text
HAM move DL -> C face=OPH
```

It should receive already-resolved state:

```json
{
  "id": "actor:HAM",
  "kind": "actor",
  "point": {"x": 0, "y": 12, "z": 0},
  "label": "HM",
  "title": "Hamlet",
  "face": "OPH"
}
```

That keeps staging semantics centralized in Stager while allowing Cuemaster to own presentation.

## Diagram State Contract

The diagram state should be a renderer-facing contract, not a copy of the authoring model and not raw SVG.

It should use stage coordinates, not SVG pixels. Each renderer projects stage coordinates into its own viewport.

### Top-Level Shape

```json
{
  "format": "quince.blocking.diagram_state",
  "format_version": "1.0",
  "diagram_id": "scene:1.3@b2",
  "diagram_kind": "beat",
  "scene_id": "1.3",
  "beat_id": "b2",
  "set_id": "act1",
  "stage": {
    "type": "proscenium",
    "width": 36,
    "depth": 24,
    "units": "ft",
    "audience": "south"
  },
  "areas": [],
  "levels": [],
  "connectors": [],
  "anchors": [],
  "set_pieces": [],
  "entities": [],
  "offstage": [],
  "diagnostics": []
}
```

### Diagram Kinds

- `stage`: stage geometry only.
- `set`: stage plus selected set scenery, no scene placements.
- `scene`: selected set plus scene snapshot placements.
- `beat`: selected set plus point-in-time state after applying beats.

### Coordinates

Coordinates should stay in stage units:

```json
{"x": -12, "y": 4, "z": 0}
```

Renderer-specific projection should not leak into the JSON. A renderer may output portrait, landscape, zoomed, split-level, or mobile-optimized views from the same state.

### Render Entities

Actors, props, set pieces, and possibly anchors should become render entities with stable ids.

```json
{
  "id": "actor:HAM",
  "source_id": "HAM",
  "kind": "actor",
  "layer": "actors",
  "point": {"x": -12, "y": 4, "z": 0},
  "source": "DL",
  "label": "HM",
  "title": "Hamlet",
  "face": "CLA",
  "style": {"elevation": "deck"},
  "visible": true
}
```

Props:

```json
{
  "id": "prop:sword",
  "source_id": "sword",
  "kind": "prop",
  "layer": "props",
  "point": {"x": 0, "y": 12, "z": 0},
  "source": "table",
  "icon": "sword",
  "title": "sword",
  "visible": true
}
```

Set pieces:

```json
{
  "id": "set_piece:table",
  "source_id": "table",
  "kind": "set_piece",
  "layer": "scenery",
  "point": {"x": 0, "y": 12, "z": 0},
  "source": "C",
  "icon": "table",
  "title": "table",
  "size": {"width": 5, "depth": 3},
  "fixed": true,
  "visible": true
}
```

### Layout Decisions

Some layout behavior should be compiled into diagram state so Python and Cuemaster renderers match:

- icon ids
- actor labels
- full titles
- entity layers
- elevation style bucket
- visibility/offstage state
- collision offsets for actors and props at the same point
- prop slot positions for props placed on a set piece

The renderer should still own projection from stage units to pixels.

## Checkpoints And Deltas

The diagram-state refactor enables, but does not need to immediately implement, Playbook checkpoint/delta packaging.

Recommended later package shape:

```text
staging/
  diagram_manifest.json
  checkpoints/
    scene-1.3-start.json
    scene-1.3-b20.json
  deltas/
    scene-1.3.json
```

Checkpoint:

```json
{
  "checkpoint_id": "scene:1.3:start",
  "diagram_state": {...}
}
```

Delta:

```json
{
  "from_checkpoint": "scene:1.3:start",
  "target": "scene:1.3@b2",
  "ops": [
    {"op": "upsert_entity", "entity": {"id": "actor:CLA", "point": {"x": 12, "y": 4, "z": 0}, "source": "DR"}},
    {"op": "set_visible", "id": "prop:sword", "visible": false}
  ]
}
```

Checkpoint spacing should be configurable later:

- always at scene start
- always at set change
- every N blocking beats
- whenever delta size exceeds a threshold
- whenever the renderer decides a full state is clearer than a complex diff

## Python Refactor Target

Current:

```text
ResolvedSnapshot -> StageSvgRenderer -> SVG
```

Target:

```text
ResolvedSnapshot -> DiagramStateBuilder -> DiagramState -> StageSvgRenderer -> SVG
```

`StageSvgRenderer` should eventually accept `DiagramState`, not `ResolvedSnapshot`.

The Block CLI should write diagram-state JSON from `--json-out`. If we still need raw resolver JSON for debugging, add a separate `--resolved-json-out` option later.

## TypeScript/Cuemaster Target

Cuemaster should eventually have a TypeScript equivalent of the rendering adapter:

```text
DiagramState JSON -> Cuemaster staging SVG/component
```

It should not include:

- stage-file parser
- blocking syntax parser
- set resolver
- beat resolver
- location resolver

It may include:

- JSON schema validation
- diagram projection
- SVG/component rendering
- checkpoint/delta application
- UI affordances such as zoom, filtering, tap-to-label

## Implementation Plan

### Phase 1 — Python Diagram State Model

- [x] Add `src/stager/staging/diagram_state.py`.
- [x] Define dataclasses for `DiagramState`, `DiagramStage`, `DiagramArea`, `DiagramLevel`, `DiagramConnector`, `DiagramAnchor`, `DiagramEntity`, `DiagramOffstageEntity`, and `DiagramDiagnostic`.
- [x] Add `format` and `format_version` fields.
- [x] Add `diagram_kind` values: `stage`, `set`, `scene`, `beat`.
- [x] Add `to_dict()` methods with deterministic key ordering where useful.
- [x] Keep this model renderer-facing and independent from authoring parser classes.

### Phase 2 — Diagram State Builder

- [x] Add `src/stager/staging/diagram_state_builder.py`.
- [x] Convert `ResolvedSnapshot` into `DiagramState`.
- [x] Preserve stage, scene, beat, and set identity.
- [x] Convert areas, levels, anchors, connectors, set pieces, props, and actors into renderer-facing records.
- [x] Assign stable entity ids such as `actor:HAM`, `prop:sword`, and `set_piece:table`.
- [x] Assign icon ids using `StageSvgIconLibrary.icon_id()`.
- [x] Assign actor labels and titles.
- [x] Assign elevation style buckets such as `deck`, `elevated`, and `below`.
- [x] Move actor collision offsets from `StageSvgRenderer` into the builder.
- [x] Move prop collision offsets and prop-on-set-piece slot indexes into the builder.
- [x] Preserve offstage/unknown state.
- [x] Preserve diagnostics.

### Phase 3 — SVG Renderer Refactor

- [x] Change `StageSvgRenderer.render()` to accept `DiagramState`.
- [x] Move projection, viewport, portrait/landscape, and SVG markup concerns into the renderer.
- [x] Remove direct dependency on `ResolvedSnapshot` from `StageSvgRenderer`.
- [x] Keep SVG output visually equivalent to current output.
- [x] Keep embedded icon symbols for standalone SVG export.
- [x] Add tests that compare key SVG features after the refactor.

### Phase 4 — CLI JSON Contract

- [x] Update `block stage --json-out` to write diagram-state JSON.
- [x] Update `block set --json-out` to write diagram-state JSON.
- [x] Update `block scene --json-out` to write diagram-state JSON.
- [x] Update `block beat --json-out` to write diagram-state JSON.
- [x] Consider adding `--resolved-json-out` only if lower-level resolver debugging is still needed.
- [x] Update help text and docs so `--json-out` means diagram state.

### Phase 5 — Tests And Fixtures

- [x] Add unit tests for `DiagramStateBuilder`.
- [x] Add golden JSON coverage for `plays/hamlet/staging.txt --scene 1.3 --beat b2` through regenerated CLI output.
- [x] Assert generated JSON includes `format`, `format_version`, `diagram_kind`, `set_id`, stage dimensions, and stable entity ids.
- [x] Assert stage-only diagram state excludes set-specific scenery.
- [x] Assert set-only diagram state excludes actor placements.
- [x] Assert actor collisions and prop slots are represented in JSON, not recomputed in SVG renderer.
- [x] Run `PYTHONPATH=src .venv/bin/python -m pytest tests/stager/staging/test_point_in_time_svg.py`.
- [x] Run `.venv/bin/python run_tests.py`.

### Phase 6 — Documentation

- [x] Update `planning/blocking/README.md` to describe diagram state as the renderer contract.
- [x] Update `planning/terminology.md` with **diagram state**.
- [x] Update `planning/blocking/spec-rendering-animation.md` to say renderers consume diagram state.
- [x] Document that full SVG export is a renderer output, not the Playbook storage format.

### Phase 7 — Playbook/Cuemaster Follow-On Plan

- [ ] Design `staging/diagram_manifest.json` for Playbooks.
- [ ] Decide checkpoint spacing defaults.
- [ ] Define semantic delta operations.
- [ ] Add a JSON schema for diagram state under `planning/specs/` when Cuemaster consumes it.
- [ ] Port diagram-state rendering to Cuemaster TypeScript.
- [ ] Add cross-language fixture tests: Python-generated JSON should render expected entities in Cuemaster.

## Acceptance Criteria For This Refactor

- `StageSvgRenderer` renders from diagram state, not directly from `ResolvedSnapshot`.
- `--json-out` produces a stable diagram-state JSON contract.
- Current Hamlet SVG outputs remain visually equivalent.
- The full test suite passes.
- The next blocking features can build against diagram state rather than special-casing SVG output.

## Open Decisions

- Whether diagram state should include precomputed projected coordinates in addition to stage coordinates. Default answer: no, keep projection renderer-owned.
- Whether collision offsets belong in stage units or renderer-relative units. Default answer: store semantic slot/offset hints and let renderers scale them.
- Whether Playbooks should store checkpoint states only or checkpoint states plus deltas. Default answer: start with checkpoint states; add deltas after Cuemaster renders states reliably.
- Whether SVG symbols should be embedded in each exported SVG or referenced externally. Default answer: keep embedded symbols for standalone SVG export; Playbook/Cuemaster can share icon definitions.
