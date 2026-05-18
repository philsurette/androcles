# Quince Staging Architecture

## Overview

The staging system should compile human-authored Markdown blocks into deterministic assets.

This architecture replaces the current blocking-note implementation rather than wrapping it. The current implementation does not need compatibility support, but its inline authoring shape may still inform the replacement syntax. New downstream behavior should consume a compiled staging model rather than raw authoring text, regardless of whether that text came from fenced blocks, inline actions, or both.

```text
production.md
  ↓
block extraction
  ↓
layout parser     cue-lite parser     blocking parser
  ↓               ↓                   ↓
normalized staging model
  ↓
validation and resolution
  ↓
static SVG renderer
  ↓
optional timeline generator
  ↓
Playbook assets
```

## Authoring versus normalized model

The authoring DSL should be permissive and readable.

The normalized model should be explicit and strict.

Example authoring:

```text
HAM move DL -> C dur=2.2
cue LX.24 at=HAM.arrive(C)
```

Example normalized event:

```json
{
  "id": "evt-b12-001",
  "type": "move",
  "actor": "HAM",
  "from": {"source": "DL", "x": -12, "y": 4, "z": 0},
  "to": {"source": "C", "x": 0, "y": 12, "z": 0},
  "duration": 2.2,
  "path": {"kind": "line"}
}
```

## Modules

### Block extractor

Finds staging blocks inside Markdown.

Recommended block types:

- `layout`
- `blocking`
- `cues`

The extractor should preserve source positions for diagnostics.

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

### Validator

Reports:

- unknown actor/location/prop/cue IDs
- impossible movement references
- missing layout
- unsupported z-axis transitions
- malformed timing expressions

Validation should warn rather than fail where possible.

### SVG renderer

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
  events: BlockingEvent[];
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

## Playbook output

The compiled Playbook should contain authoring-independent assets:

```text
playbook/
  staging/
    staging.normalized.json
    svg/
      scene-1-beat-b12.svg
    timeline/
      scene-1-beat-b12.timeline.json
```

Cuemaster should consume these compiled assets, not raw DSL.

The old Playbook blocking entries can be removed or mapped into this staging asset set during implementation. Cuemaster should eventually render staging assets from the compiled model rather than from raw blocking-note text.
