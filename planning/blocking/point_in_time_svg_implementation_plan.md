# Point-In-Time Stage SVG Implementation Plan

This is a focused implementation plan for rendering a described stage and a single point-in-time scene state to SVG. It intentionally starts independently of Quince Playbook integration, Cuemaster integration, publication diffs, audio timing, and animation.

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
anchor door_l = UL
anchor door_r = UR
anchor table = C

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
OPH offstage via=door_l
table @ C
sword @ table
```

Measured version:

```text
stage type=proscenium width=36 depth=24 units=ft
grid standard=9
anchor door_l at=(-16,20,0)
anchor door_r at=(16,20,0)
set table kind=furniture at=C size=(5,3)

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
table @ C
sword @ table
```

## Design Decisions

- Dimensions are optional. If omitted, use a deterministic default stage or normalized coordinate space.
- Standard 9-zone grid works without measured dimensions.
- Multiple levels are represented as `(x,y,z)` metadata and rendered in 2D plan view.
- Scene snapshots are authoritative state; do not replay the whole play.
- Absolute placement corrects state.
- Missing state produces diagnostics and a useful partial SVG, not a hard failure.

## Output Shape

Suggested standalone command during the spike:

```sh
PYTHONPATH=src .venv/bin/python -m stager.staging.render_point \
  path/to/stage.txt \
  --scene 1.2 \
  --out /tmp/stage.svg
```

Potential later Quince command:

```sh
quince staging render --play <play_id> --scene 1.2 --beat start
```

Do not implement the Quince command in this slice unless the standalone renderer is already solid.

## Phase 1: Data Model

- [ ] Add staging model classes for `StageLayout`, `StageShape`, `Area`, `Anchor`, `Level`, `Connector`, `SetPiece`, `Prop`, `SceneSnapshot`, and `Placement`.
- [ ] Keep model classes independent from Playbook and Cuemaster code.
- [ ] Represent locations as resolved `(x,y,z)` plus the source reference string.
- [ ] Represent unresolved locations as diagnostics rather than `None` where possible.
- [ ] Add unit tests for model serialization to normalized JSON.

## Phase 2: Layout Parser

- [ ] Parse minimal text-only layout:
  - `stage type=proscenium`
  - `grid standard=9`
  - `anchor door_l = UL`
  - `anchor table = C`
- [ ] Parse measured layout:
  - `width`
  - `depth`
  - `units`
  - `at=(x,y,z)`
  - `size=(w,d)`
- [ ] Generate default 9-zone areas from measured or default dimensions.
- [ ] Support standard aliases such as `USL`, `DSR`, and `CSC`.
- [ ] Add diagnostics for duplicate IDs and malformed statements.
- [ ] Add parser tests for text-only and measured layouts.

## Phase 3: Snapshot Parser

- [ ] Parse scene snapshot headers such as `scene 1.2 snapshot`.
- [ ] Parse actor placements:
  - `HAM @ DL`
  - `HAM @ balcony_l face=house`
  - `OPH offstage via=door_l`
- [ ] Parse prop and set-piece placements:
  - `table @ C`
  - `sword @ table`
- [ ] Treat placements as absolute state.
- [ ] Add diagnostics for malformed placements.
- [ ] Add tests for scene-start snapshots.

## Phase 4: Resolver

- [ ] Resolve grid zones to coordinates.
- [ ] Resolve anchors and set pieces.
- [ ] Resolve props placed on set pieces.
- [ ] Resolve offstage actors with entrance/exit metadata.
- [ ] Preserve unresolved entries with diagnostics.
- [ ] Add tests for unknown references and partial rendering state.

## Phase 5: 2D Level Support

- [ ] Parse `level` definitions with `z`.
- [ ] Parse elevated anchors and set pieces.
- [ ] Parse stairs/ramps/lifts as connectors between z levels.
- [ ] Render z as metadata only; do not introduce 3D.
- [ ] Add tests for elevated actor placement and connector diagnostics.

## Phase 6: Static SVG Renderer

- [ ] Render stage boundary.
- [ ] Render 9-zone grid and labels.
- [ ] Render named anchors and set pieces.
- [ ] Render actor glyphs with labels and facing indicators.
- [ ] Render prop labels or compact prop markers.
- [ ] Render elevated surfaces with 2D styling and elevation labels.
- [ ] Render unresolved/offstage actors in a side list or diagnostics block.
- [ ] Use deterministic SVG output suitable for snapshot tests.
- [ ] Add renderer tests for text-only and measured stages.

## Phase 7: Standalone CLI

- [ ] Add a small standalone render entry point.
- [ ] Accept input path and output SVG path.
- [ ] Support selecting scene/snapshot by ID.
- [ ] Write normalized JSON next to the SVG when requested.
- [ ] Print diagnostics in producer-readable text.
- [ ] Add CLI smoke tests with temporary files.

## Phase 8: Documentation And Examples

- [ ] Add text-only stage example.
- [ ] Add measured stage example.
- [ ] Add multi-level example using 2D elevation metadata.
- [ ] Document that dimensions are optional.
- [ ] Document that scene snapshots are preferred over full-play replay.

## Acceptance Criteria

- [ ] A producer can describe a stage using only named zones and anchors.
- [ ] A producer can define a scene-start snapshot.
- [ ] The renderer produces a useful SVG without exact dimensions.
- [ ] The renderer uses exact dimensions when provided.
- [ ] Multi-level stage elements render in 2D with elevation labels.
- [ ] Missing actor/prop state produces diagnostics and does not prevent SVG generation.
- [ ] The implementation is independent of Quince Playbook/Cuemaster integration.
