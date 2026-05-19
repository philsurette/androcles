# Stage / Set / Scene Design And Rollout Plan

## Purpose

Blocking needs a reusable layer between the physical stage and a scene snapshot.

Real productions often change major scenic structures between acts or scene groups: balconies are installed, stairs move, platforms are added, doors disappear, and prop presets change. Those changes should not be modeled as scene-specific actor blocking, and they should not be treated as immutable stage geometry.

The staging model should therefore separate:

1. **Stage**: invariant performance-space geometry.
2. **Set**: reusable scenic setup placed on that stage.
3. **Scene snapshot**: actor, prop, and movable-object state for one scene using one set.

## Terminology

- **Staging file**: the standalone authoring file consumed by the Block CLI. The default filename is `staging.txt` because the file contains stage, set, scene, and beat records.
- **Stage**: invariant venue/play-space geometry. In v0.1 this means type, dimensions, units, coordinate system, audience orientation, and generated standard grid.
- **Set**: a named scenic setup used by one or more scenes. A set owns levels, anchors, connectors, structural scenic elements, set pieces, and prop presets.
- **Scene snapshot**: the authoritative initial state for a scene. It references exactly one set and places actors, props, and movable set pieces for that scene.
- **Blocking beat**: ordered state changes within one scene. It starts from the scene snapshot and applies local changes up to the requested beat.
- **Point-in-time state**: the resolved scene snapshot plus zero or more applied beats.
- **Blocking diagram**: SVG rendering of a stage, set, scene snapshot, or point-in-time state.

## Layer Responsibilities

### Stage

The stage should be stable across the production.

Stage records include:

- stage type, such as `proscenium`, `thrust`, `arena`, or `blackbox`
- width, depth, units, and coordinate-system metadata
- audience orientation
- generated default areas, such as the standard 9-zone grid

Stage records should not include balconies, stairs, doors, furniture, prop presets, or other scenery unless those features are genuinely permanent venue geometry. For the MVP, put nearly all named anchors and vertical structure in sets.

### Set

A set is the reusable scenic configuration for an act, scene group, or other major setup.

Set records include:

- levels and platforms
- stairs, ramps, lifts, and other connectors
- entrances, exits, doors, windows, traps, marks, and focus anchors
- custom areas that are meaningful only in that setup
- fixed and movable set pieces
- prop preset locations

A scene should reference one set. Multiple scene snapshots can reference the same set.

For the MVP, sets should not inherit from other sets. If two sets are similar, duplicate the few records or wait for a later `extends=` feature after real usage shows it is worth the complexity.

### Scene Snapshot

A scene snapshot is the starting truth for a scene.

Scene snapshot records include:

- actor placements
- actor facing
- prop locations or carried/offstage state
- movable set-piece positions if they differ from the set preset

Scene snapshots should not define levels, stairs, structural anchors, or fixed set layout. If those change, create a new set and point the scene at that set.

### Blocking Beat

A blocking beat is a local delta from the scene snapshot and earlier beats in the same scene.

Beats can:

- move actors
- enter or exit actors
- move props
- mark props removed/offstage
- move movable set pieces
- update facing

Beats should not install/remove major structural set elements. Model those as a different scene snapshot using a different set.

## Authoring Syntax

Use **Set** as the producer-facing term, but use `setup <id>` as the file keyword to avoid confusion with the existing set-piece shorthand.

Recommended MVP syntax:

```text
stage type=proscenium width=36 depth=24 units=ft
grid standard=9

actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius
actor OPH label=OP name=Ophelia

setup act1
level balcony at=UC size=(18,4) z=8
anchor door_l = UL
anchor door_r = UR
anchor deck_l at=CL
anchor balcony_l at=(-8,20,8)
stair stair_l from=deck_l to=balcony_l
piece table kind=table at=C size=(5,3)
prop sword preset=table

setup act2
anchor door_l = CL
anchor door_r = CR
piece throne kind=chair at=UC size=(4,4)
piece bench kind=bench at=DR size=(5,2)

scene 1.2 set=act1 snapshot
HAM @ DL face=CLA
CLA @ balcony_l
OPH offstage via=door_l
sword @ table

scene 1.3 set=act1 snapshot
HAM @ balcony_l face=CLA
CLA @ DC
OPH @ deck_l face=HAM
sword @ table

scene 2.1 set=act2 snapshot
CLA @ throne
HAM @ DL face=CLA
```

### Keyword Changes

The current syntax uses `piece table kind=table at=C` for set pieces. The earlier prototype accepted `set table kind=furniture at=C`; that remains only as a temporary parser alias during migration.

Rationale:

- `set` should mean the reusable scenic setup in user-facing CLI and documentation.
- `set piece` is a theatre term, but `set <id>` and `set <piece_id>` create an avoidable parser and documentation ambiguity.
- `piece` is terse, readable, and still maps to the existing `SetPieceDefinition` concept in code.

Because no real productions depend on the prototype blocking syntax, the parser alias should be removed after the remaining prototype-only docs and fixtures have migrated.

## Resolution Rules

When resolving a scene:

1. Resolve the scene id.
2. Resolve the scene's `set=` reference.
3. Resolve the stage geometry.
4. Resolve the selected set against the stage's grid, coordinate system, and units.
5. Resolve scene placements against the selected set.
6. Apply beats for that scene, if requested.

Location references should resolve in this order:

1. explicit coordinate
2. standard grid area or alias
3. selected-set anchor
4. selected-set set piece
5. selected-set prop preset

IDs in a resolved set should be unique across addressable locations. For example, a set should not define an anchor named `C` because `C` is a standard grid area.

## Data Model Direction

Recommended production classes:

```text
StagingDocument
  stage: StageDefinition
  actors: dict[str, ActorDefinition]
  sets: dict[str, ScenicSetDefinition]
  snapshots: dict[str, SceneSnapshot]
  beats: list[BlockingBeat]

ScenicSetDefinition
  id: str
  areas: dict[str, AreaDefinition]
  anchors: dict[str, AnchorDefinition]
  levels: dict[str, LevelDefinition]
  connectors: dict[str, ConnectorDefinition]
  set_pieces: dict[str, SetPieceDefinition]
  props: dict[str, PropDefinition]

SceneSnapshot
  id: str
  set_id: str
  placements: tuple[Placement, ...]
```

`ScenicSetDefinition` is preferable to `SetDefinition` in code because `set` is a Python built-in and because the class should be easy to distinguish from `SetPieceDefinition`.

## CLI Design

The Block CLI should expose the three layers directly:

```sh
./block stage plays/hamlet/staging.txt

./block set plays/hamlet/staging.txt \
  --set act1

./block scene plays/hamlet/staging.txt \
  --scene 1.2

./block beat plays/hamlet/staging.txt \
  --scene 1.3 \
  --beat b2
```

When run from a play folder, the input defaults to `staging.txt`.

For inputs under `plays/<play_id>/`, output defaults to `build/<play_id>/staging/`.

`block render` can remain as a temporary developer alias during the transition, but the clearer producer-facing command names should be `stage`, `set`, `scene`, and `beat`.

Expected render contents:

- `block stage`: stage boundary, grid, coordinate orientation, and no set-specific scenery.
- `block set`: stage plus selected set levels, anchors, connectors, pieces, and prop presets.
- `block scene`: selected set plus scene snapshot placements.
- `block beat`: selected set plus point-in-time state after applying beats.

## Migration Strategy

The current Hamlet and planning examples have been migrated by:

1. Keeping the existing `stage` and `grid` records at top level.
2. Adding `setup default` or a named setup such as `setup act1`.
3. Moving `level`, `anchor`, `stair`, `ramp`, `lift`, `piece`, and `prop` records into that setup.
4. Renaming `set <piece_id> ...` records to `piece <piece_id> ...`.
5. Adding `set=<setup_id>` to every `scene <id> snapshot` header and embedded blocking block where applicable.
6. Updating generated example SVG paths to include `set-<id>` where useful.

## Implementation Plan

### Phase 1 — Documentation And Examples

- [x] Record the stage/set/scene design in a dedicated planning doc.
- [x] Update shared terminology so `Stage` no longer includes set-specific scenery.
- [x] Update blocking README examples to show `stage`, `set`, `scene`, and `beat` commands.
- [x] Update layout and blocking specs to describe set selection.
- [x] Update Hamlet example syntax to include one or more `setup` blocks.

### Phase 2 — Model Refactor

- [x] Add `ScenicSetDefinition`.
- [x] Move anchors, levels, connectors, set pieces, and prop presets from `StagingDocument` into `ScenicSetDefinition`.
- [x] Add `set_id` to `SceneSnapshot`.
- [x] Use `ResolvedSnapshot.set_id` for renderer and JSON context.
- [x] Keep actor definitions document-global.
- [x] Update `to_dict()` output to include `set_id` and selected set data.

### Phase 3 — Parser Refactor

- [x] Parse `setup <id>` headers.
- [x] Parse `piece <id> ...` set-piece records.
- [x] Parse `scene <id> set=<set_id> snapshot`.
- [ ] Require set-owned records to appear inside a setup block.
- [x] Produce useful diagnostics for unknown setup references.
- [ ] Remove the old `set <piece_id> ...` authoring form rather than adding long-term compatibility.

### Phase 4 — Resolver Refactor

- [x] Resolve stage-only state without any set records.
- [x] Resolve set-only state for `block set`.
- [x] Resolve scene snapshots against their selected set.
- [x] Resolve beat state against the scene's selected set.
- [ ] Validate duplicate addressable ids in a resolved set.
- [ ] Validate that vertical movements reference available connectors when required.

### Phase 5 — CLI Refactor

- [x] Keep `./block` as the standalone launcher.
- [x] Keep `block stage`.
- [x] Add `block set --set <id>`.
- [x] Add `block scene --scene <id>`.
- [x] Add `block beat --scene <id> --beat <id>`.
- [x] Keep `block render` as a temporary alias for beat/scene rendering.
- [x] Update help text to use stage/set/scene/beat terminology consistently.

### Phase 6 — Tests And Fixtures

- [x] Add parser tests for setup blocks.
- [x] Add resolver tests for two scenes sharing one set.
- [x] Add resolver tests for two scenes using different sets with different levels/connectors.
- [x] Add CLI tests for `block set`, `block scene`, and `block beat`.
- [x] Add a Hamlet fixture with at least two sets.
- [x] Confirm stage-only rendering excludes set-specific scenery.
- [x] Confirm set rendering excludes scene actor placements.

### Phase 7 — Cleanup

- [ ] Remove stale docs that imply the stage owns all scenic structure.
- [ ] Rename examples and generated outputs where current filenames imply scene-only behavior.
- [ ] Check for dead parser/resolver branches after dropping the old `set <piece_id>` syntax.
- [x] Run `PYTHONPATH=src .venv/bin/python -m pytest tests/stager/staging/test_point_in_time_svg.py`.
- [x] Run `.venv/bin/python run_tests.py`.

## Follow-On Features

- Set inheritance with `setup act2 extends=act1`.
- Split render sheets by level for complex multi-level sets.
- Set-change cues that reference transitions between named sets.
- Editor tooling for choosing a scene's set from known setup ids.
