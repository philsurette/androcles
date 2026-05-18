# SVG Rendering and Animation Spec Draft

## Purpose

Generate visual blocking assets from normalized staging data.

The first target is static SVG. Animation is a later generated layer.

## Static SVG goals

Each blocking beat should be renderable as a static SVG showing:

- stage boundary
- standard grid/areas
- named anchors
- relevant set pieces
- actors
- facing indicators
- movement paths
- cue badges
- optional notes

## SVG coordinate strategy

Use the SVG `viewBox` as the canonical render coordinate space.

The renderer should convert stage coordinates into SVG coordinates. Because SVG y normally increases downward but stage y is recommended to increase upstage, the renderer may either:

1. use a transform on the root drawing group, or
2. convert y values explicitly.

Choose the simpler and more testable approach.

## SVG primitives

Recommended mapping:

| Concept | SVG |
|---|---|
| Stage boundary | `rect`, `polygon`, `path` |
| Area | `rect` or `polygon` plus label |
| Level/platform | labelled `polygon` or `rect` |
| Stair | repeated small `rect`/`line` shapes |
| Ramp | `polygon` plus slope label |
| Anchor | labelled `circle` or symbol |
| Actor | `g` containing circle + label + facing arrow |
| Movement path | `path` with arrow marker |
| Cue | small badge/text label |
| Note | optional callout text |

## Actor glyph

A minimal actor glyph:

```svg
<g class="actor" data-actor="HAM" transform="translate(0,12) rotate(180)">
  <circle r="0.25" />
  <line x1="0" y1="0" x2="0" y2="0.5" />
  <text x="0.35" y="0.1">HAM</text>
</g>
```

## Movement path

A movement path should use SVG path data:

```svg
<path class="move-path" d="M -12 4 Q -5 8 0 12" />
```

## Animation recommendation

Prefer **SVG + JavaScript-controlled timeline** for interactive playback.

Native SVG animation may be generated for demo/export, but JS control is better for:

- pause
- scrub
- jump to line
- sync with audio
- playback speed
- rehearsal controls
- Cuemaster integration

## Timeline JSON

Example:

```json
{
  "beat": "b12",
  "lineId": "HAM-042",
  "audioStart": 192.4,
  "audioEnd": 196.8,
  "events": [
    {
      "type": "move",
      "actor": "HAM",
      "path": "M -12 4 Q -5 8 0 12",
      "start": 192.8,
      "end": 195.0,
      "face": "OPH"
    },
    {
      "type": "cue",
      "id": "LX.24",
      "at": 195.0
    }
  ]
}
```

## Timing inference

Timing should be inferred only when explicit timing is missing.

Priority:

1. explicit start/end
2. explicit duration
3. beat-relative timing from line/audio metadata
4. static-only fallback

## First implementation

Do not implement full animation first.

Implement:

1. static SVG stage diagram
2. actor placement
3. movement path arrows
4. cue badges
5. optional JSON timeline skeleton

Animation can follow after diagrams are reliable.
