# Quince Staging Architecture

## Overview

The staging system compiles human-authored staging notes in `production.md` into deterministic assets.

This architecture replaces the current blocking-note implementation rather than wrapping it. The current implementation does not need compatibility support, but its inline authoring shape may still inform the replacement syntax. New downstream behavior should consume a compiled staging model rather than raw authoring text, regardless of whether that text came from fenced blocks, inline actions, or both.

```text
production.md
  ↓
staging export
  ↓
build/<play_id>/staging/staging.txt
  ↓
staging parser
  ↓
normalized staging model
  ↓
validation and stage/set/scene/beat resolution
  ↓
DiagramState JSON
  ├─ Python SVG renderer for Block CLI and build artifacts
  ├─ Playbook staging bundle: icons, checkpoints, deltas
  └─ Cuemaster renderer for on-demand diagrams
```

## Authoring versus normalized model

The authoring DSL should be permissive and readable.

The normalized model should be explicit and strict.

Example authoring:

```text
HM move DL -> C dur=2.2
cue LX.24 at=HM.arrive(C)
```

Example normalized event:

```json
{
  "id": "evt-b12-001",
  "type": "move",
  "actor": "HM",
  "from": {"source": "DL", "x": -12, "y": 4, "z": 0},
  "to": {"source": "C", "x": 0, "y": 12, "z": 0},
  "duration": 2.2,
  "path": {"kind": "line"}
}
```

## Modules

### Staging Exporter

Finds inline and nearby staging notes inside `production.md` and writes the generated staging overlay to `build/<play_id>/staging/staging.txt`.

The exported overlay is the handoff between producer-facing script authoring and staging-specific parsing. It should preserve production ids and source positions for diagnostics.

### Layout parser

Parses stage geometry and object definitions.

Outputs:

- stage dimensions
- coordinate system
- generated and custom areas
- anchors
- levels
- set pieces
- props

### Cue-lite parser

Parses cue definitions.

Outputs cue records keyed by cue ID.

### Blocking parser

Parses actor, set-piece, prop, and cue events.

Outputs unresolved references first, then passes them to the resolver.

### Resolver

Resolves:

- area aliases to coordinates
- anchors to coordinates
- prop preset locations
- set-piece locations
- actor references
- cue references
- line/beat references
- nearest snapshots/checkpoints for rendering state

### Validator

Reports:

- unknown actor/location/prop/cue IDs
- impossible movement references
- missing layout
- unsupported z-axis transitions
- z-axis transitions without an available stair/ramp/lift connector
- state mismatches between known actor/prop position and explicit movement `from`
- malformed timing expressions

Validation should warn rather than fail where possible.

### State resolver

The renderer should not depend on replaying the whole play from the beginning. The compiler should build state from explicit snapshots/checkpoints and then apply local events.

Recommended behavior:

- find the nearest prior snapshot for the requested beat
- apply events from that snapshot through the requested beat
- treat absolute placement as a state correction
- warn, but still render useful output, when state is incomplete
- keep unknown actors/props in diagnostics or an offstage/unknown list

### DiagramState Builder

Builds renderer-neutral JSON from resolved state. This layer owns final icon ids, labels, titles, level colors, movement hints, offstage lists, and diagnostics.

Renderers must not parse authoring syntax or resolve location references.

### SVG Renderer

Generates static SVG charts.

The renderer should not depend on browser APIs.

### Timeline generator

Later milestone.

Generates event timing records for optional animation playback.

## Data model outline

```ts
type StageLayout = {
  id: string;
  units: "ft" | "m" | "unit";
  stage: StageShape;
  coordinateSystem: CoordinateSystem;
  areas: Record<string, Area>;
  levels: Record<string, Level>;
  anchors: Record<string, Anchor>;
  setPieces: Record<string, SetPiece>;
  props: Record<string, Prop>;
};

type BlockingBeat = {
  id: string;
  sceneId?: string;
  lineId?: string;
  sourceRange?: SourceRange;
  snapshot?: BlockingSnapshot;
  events: BlockingEvent[];
};

type BlockingSnapshot = {
  placements: Record<string, PlacementState>;
  props: Record<string, PropState>;
  setPieces: Record<string, SetPieceState>;
};

type BlockingEvent =
  | PlaceEvent
  | MoveEvent
  | FaceEvent
  | EnterEvent
  | ExitEvent
  | CueEvent
  | HoldEvent
  | NoteEvent;

type Cue = {
  id: string;
  type: "lighting" | "sound" | "shift" | "group" | "other";
  label?: string;
  focus?: Reference[];
  fade?: number;
  note?: string;
};
```

## Playbook Output

The compiled Playbook should contain authoring-independent assets:

```text
playbook/
  staging/
    diagram_manifest.json
    icons.svg
    checkpoints/
      scene-1.3-start.json
      scene-1.3-b20.json
    deltas/
      scene-1.3.json
```

Cuemaster consumes these compiled assets, not raw DSL. It loads the nearest checkpoint DiagramState, applies semantic deltas, and renders the result locally.

Text blocking entries remain useful human-readable rehearsal context. Diagram assets are an optional Playbook minor-version addition and should be omitted when no staging data exists or when the producer passes `--no-blocking-diagrams`.
