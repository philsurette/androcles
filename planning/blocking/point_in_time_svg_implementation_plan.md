# Point-In-Time Stage SVG Implementation Plan

This is a focused implementation plan for rendering a described stage and a single point-in-time scene state to SVG. It intentionally starts independently of Quince Playbook integration, Cuemaster integration, publication diffs, audio timing, and animation.

Status note: this plan documents the completed pre-stage/set/scene vertical slice. Future work should use [stage_set_scene_design.md](stage_set_scene_design.md), which moves set-specific records under named `setup` blocks and keeps `stage` limited to invariant geometry.

## Goal

Given a text file that describes:

- a stage layout
- named locations
- optional dimensions and levels
- a scene-start snapshot
- point-in-time actor/prop/set-piece placements

generate:

- normalized JSON for that point in time
- one static SVG stage diagram
- diagnostics for unresolved or incomplete references

## Non-Goals

- No Quince Playbook packaging.
- No Cuemaster UI.
- No animation timeline.
- No full-play blocking replay.
- No 3D rendering.
- No lighting-control or sound-control export.
- No requirement to parse all of `production.md` in the first slice.

## Producer Workflow

The first workflow should be:

1. Define a stage, using text only if dimensions are unknown.
2. Define named positions and important set/prop anchors.
3. Define the scene-start snapshot.
4. Render a point-in-time SVG.
5. Add precision only where the SVG needs it.

Example:

```text
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius
anchor door_l = UL
anchor door_r = UR
set table kind=furniture at=C size=(5,3)

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
OPH offstage via=door_l
sword @ table
```

Measured version:

```text
stage type=proscenium width=36 depth=24 units=ft
grid standard=9
actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius
anchor door_l at=(-16,20,0)
anchor door_r at=(16,20,0)
set table kind=furniture at=C size=(5,3)

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
sword @ table
```

## Design Decisions

- Dimensions are optional. If omitted, use a deterministic default stage or normalized coordinate space.
- Standard 9-zone grid works without measured dimensions.
- Multiple levels are represented as `(x,y,z)` metadata and rendered in 2D plan view.
- Scene snapshots are authoritative state; do not replay the whole play.
- Absolute placement corrects state.
- Missing state produces diagnostics and a useful partial SVG, not a hard failure.
- Static SVG output defaults to portrait orientation for mobile viewing; in portrait, downstage renders to the right.
- Landscape output remains available as an explicit render option.
- Actors render as circles with two-character labels and full names in SVG `<title>` elements.
- Set pieces, props, and anchors should avoid visible labels by default and expose names through SVG `<title>` elements to reduce clutter.
- Set pieces and props use embedded SVG symbols so generated diagrams are self-contained.

## Output Shape

Suggested standalone command during the spike:

```sh
./block render \
  path/to/stage.txt \
  --scene 1.2 \
  --out /tmp/stage.svg
```

Landscape output:

```sh
./block render \
  path/to/stage.txt \
  --scene 1.2 \
  --out /tmp/stage-landscape.svg \
  --orientation landscape
```

Potential later Quince command:

```sh
quince staging render --play <play_id> --scene 1.2 --beat start
```

Do not implement the Quince command in this slice unless the standalone renderer is already solid.

## Phase 1: Data Model

- [x] Add staging model classes for `StageLayout`, `StageShape`, `Area`, `Anchor`, `Level`, `Connector`, `SetPiece`, `Prop`, `SceneSnapshot`, and `Placement`.
- [x] Keep model classes independent from Playbook and Cuemaster code.
- [x] Represent locations as resolved `(x,y,z)` plus the source reference string.
- [x] Represent unresolved locations as diagnostics rather than `None` where possible.
- [x] Add unit tests for model serialization to normalized JSON.

## Phase 2: Layout Parser

- [x] Parse minimal text-only layout:
  - `stage type=proscenium`
  - `grid standard=9`
  - `anchor door_l = UL`
  - `anchor table = C`
- [x] Parse measured layout:
  - `width`
  - `depth`
  - `units`
  - `at=(x,y,z)`
  - `size=(w,d)`
- [x] Generate default 9-zone areas from measured or default dimensions.
- [x] Parse actor metadata with two-character diagram labels.
- [x] Support standard aliases such as `USL`, `DSR`, and `CSC`.
- [x] Add diagnostics for duplicate IDs and malformed statements.
- [x] Add parser tests for text-only and measured layouts.

## Phase 3: Snapshot Parser

- [x] Parse scene snapshot headers such as `scene 1.2 snapshot`.
- [x] Parse actor placements:
  - `HAM @ DL`
  - `HAM @ balcony_l face=house`
  - `OPH offstage via=door_l`
- [x] Parse prop and set-piece placements:
  - `table @ C`
  - `sword @ table`
- [x] Treat placements as absolute state.
- [x] Add diagnostics for malformed placements.
- [x] Add tests for scene-start snapshots.

## Phase 4: Resolver

- [x] Resolve grid zones to coordinates.
- [x] Resolve anchors and set pieces.
- [x] Resolve props placed on set pieces.
- [x] Resolve offstage actors with entrance/exit metadata.
- [x] Preserve unresolved entries with diagnostics.
- [x] Add tests for unknown references and partial rendering state.

## Phase 5: 2D Level Support

- [x] Parse `level` definitions with `z`.
- [x] Parse elevated anchors and set pieces.
- [x] Parse stairs/ramps/lifts as connectors between z levels.
- [x] Render z as metadata only; do not introduce 3D.
- [x] Add tests for elevated actor placement and connector diagnostics.

## Phase 6: Static SVG Renderer

- [x] Render stage boundary.
- [x] Render 9-zone grid and labels.
- [x] Render named anchors and set pieces.
- [x] Render actor circles with two-character labels and facing indicators.
- [x] Render props and set pieces as compact embedded SVG markers.
- [x] Add SVG `<title>` metadata for anchors, set pieces, props, and actors.
- [x] Support portrait and landscape output; default to portrait.
- [x] Render elevated connectors with 2D styling and elevation labels.
- [x] Render elevated surfaces/platforms with 2D styling and elevation labels.
- [x] Render unresolved/offstage actors in a side list or diagnostics block.
- [x] Use deterministic SVG output suitable for snapshot tests.
- [x] Add renderer tests for text-only and measured stages.

## Phase 7: Standalone CLI

- [x] Add a small standalone render entry point.
- [x] Accept input path and output SVG path.
- [x] Support selecting scene/snapshot by ID.
- [x] Support selecting portrait or landscape orientation.
- [x] Write normalized JSON next to the SVG when requested.
- [x] Print diagnostics in producer-readable text.
- [x] Add CLI smoke tests with temporary files.

## Phase 8: Documentation And Examples

- [x] Add text-only stage example.
- [x] Add measured stage example.
- [x] Add multi-level example using 2D elevation metadata.
- [x] Document that dimensions are optional.
- [x] Document that scene snapshots are preferred over full-play replay.

## Acceptance Criteria

- [x] A producer can describe a stage using only named zones and anchors.
- [x] A producer can define a scene-start snapshot.
- [x] The renderer produces a useful SVG without exact dimensions.
- [x] The renderer uses exact dimensions when provided.
- [x] Multi-level stage elements render in 2D with elevation labels.
- [x] Missing actor/prop state produces diagnostics and does not prevent SVG generation.
- [x] The implementation is independent of Quince Playbook/Cuemaster integration.
