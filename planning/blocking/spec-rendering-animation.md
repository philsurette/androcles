# SVG Rendering Spec Draft

## Purpose

Generate visual blocking assets from normalized staging data.

The active target is static SVG. Animation and timeline playback are future features tracked in `future-features.md`.

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

The renderer should not require full-play state replay. It should render from the nearest explicit snapshot/checkpoint plus the local events needed for the requested beat.

## SVG coordinate strategy

Use the SVG `viewBox` as the canonical render coordinate space.

The renderer should convert stage coordinates into SVG coordinates. Because SVG y normally increases downward but stage y is recommended to increase upstage, the renderer may either:

1. use a transform on the root drawing group, or
2. convert y values explicitly.

Choose the simpler and more testable approach.

The static renderer supports two output orientations:

- **portrait**: default, intended for mobile viewing; downstage renders to the right.
- **landscape**: optional, preserves the more traditional wide plan view with downstage near the bottom.

## SVG primitives

Recommended mapping:

| Concept | SVG |
|---|---|
| Stage boundary | `rect`, `polygon`, `path` |
| Area | `rect` or `polygon` plus label |
| Level/platform | labelled `polygon` or `rect` |
| Stair | repeated small `rect`/`line` shapes |
| Ramp | `polygon` plus slope label |
| Anchor | `circle` or symbol with SVG `<title>` |
| Actor | `g` containing circle + two-character label + full-name `<title>` |
| Movement path | `path` with arrow marker |
| Cue | small badge/text label |
| Note | optional callout text |

## Rendering levels

Render multiple levels in 2D plan view. Do not introduce a 3D camera for the first implementation.

Recommended conventions:

- deck-level surfaces use normal outlines
- raised platforms use thicker outlines or light fill
- balconies/bridges use dashed outlines, hatch, or distinct tint
- labels include the level name and elevation, such as `bridge +8'`
- actor glyphs on nonzero `z` include a small level/elevation badge
- stairs/ramps/lifts are drawn as connector symbols in plan view

For complicated multi-level designs, optionally generate separate SVG sheets per level. This should be treated as an output option, not a different authoring model.

## Actor Glyph

Actors should not use the generic object icon. Render actors as circles with a standardized two-character shorthand inside the circle. The full character name should be present as an SVG `<title>` so browser hover and accessibility tooling can reveal it without adding visible clutter.

Example:

```svg
<g class="actor-mark">
  <title>Hamlet</title>
  <circle class="actor-circle" cx="146.667" cy="395.556" r="13" />
  <text class="actor-label" x="146.667" y="396.556">HM</text>
</g>
```

Props, set pieces, and anchors should generally avoid visible labels in crowded diagrams. Use embedded symbols plus SVG `<title>` metadata by default. A later interactive mode may add click-to-show labels, but the plain SVG baseline should remain useful without JavaScript.

## Movement path

A movement path should use SVG path data:

```svg
<path class="move-path" d="M -12 4 Q -5 8 0 12" />
```

Vertical movement should render as 2D movement with connector labels, for example `via stair_l`, rather than true vertical motion. If the normalized model contains a z change without a valid connector, the renderer should include a warning/diagnostic badge.

## First implementation

Do not implement full animation first.

Implement:

1. static SVG stage diagram
2. actor placement
3. stateful point-in-time rendering from scene snapshots plus ordered blocking directions
4. optional movement path arrows
5. optional cue badges

Animation can follow after diagrams are reliable.
