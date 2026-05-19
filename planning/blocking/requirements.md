# Quince Staging DSL Requirements

## Goal

Create a lightweight text-based staging language that can be embedded in `production.md` and compiled by Stager into normalized staging data, static SVG diagrams, and eventually optional animation timelines.

## Users

Primary users:

- directors
- stage managers
- assistant stage managers
- producers preparing a playbook
- actors using Cuemaster to rehearse

Secondary users:

- lighting/sound people who need cue coordination points
- future tooling that edits or validates production staging

## Core requirements

### R0. Progressive producer workflow

The producer workflow should not require a fully measured technical stage model before useful blocking diagrams can be created.

Recommended workflow:

1. Define the stage once.
2. Define reusable named positions, areas, anchors, and important set/prop positions.
3. Define a starting snapshot for each scene or major beat.
4. Add only the blocking changes that matter.
5. Add dimensions and exact geometry later only when diagrams need more precision.

The authoring model should support progressive specificity:

- **Tier 1: named zones only**

  ```text
  door_l = UL
  door_r = UR
  table = C
  ```

- **Tier 2: approximate geometry**

  ```text
  table at=C size=medium
  platform at=UC level=platform
  ```

- **Tier 3: measured geometry**

  ```text
  table at=(0,12,0) size=(5,3)
  platform rect=(-8,16,16,6) z=4
  ```

Dimensions should improve rendering quality, not unlock the feature. If no dimensions are provided, Stager should use a normalized or default stage model and still produce a useful SVG.

### R1. Markdown-embedded authoring

The staging DSL must be embeddable in `production.md`. The exact authoring syntax is not settled.

Block delimiters may be useful for larger declarations such as layout and cue definitions:

```markdown
[[layout]]
...
[[/layout]]

[[cues]]
...
[[/cues]]
```

Line-local action syntax may be better for blocking tied directly to dialogue or business, for example:

```markdown
HAMLET: Now might I do it pat— (_/action: crosses DL -> C_)
```

or a target-specific variant:

```markdown
HAMLET: Now might I do it pat— (_/HM: crosses DL -> C_)
```

The final syntax should optimize for producer readability and editability, not for the starter-pack examples.

### R2. Separate layout, blocking, and cue-lite concerns

The system must define separate conceptual specs:

- Stage: invariant physical performance-space geometry.
- Set: reusable scenic setup for one or more scenes.
- Blocking: actor/prop/set-piece events against a scene snapshot and its selected set.
- Cue-lite: coordination cues linked to beats, actions, areas, actors, props, or set pieces.

### R3. Standard 9-zone support

The layout spec must support the standard stage grid:

```text
UL UC UR
CL C  CR
DL DC DR
```

Aliases such as `USL`, `USC`, `USR`, `CSL`, `CSC`, `CSR`, `DSL`, `DSC`, `DSR` may also be supported.

The compiler should be able to generate these areas automatically from stage dimensions.

### R4. Continuous coordinate support

The system must support numeric stage coordinates, at minimum:

```text
(x,y)
(x,y,z)
```

The layout should define the coordinate convention. Recommended default:

```text
+x = stage right
+y = upstage
+z = up
```

### R5. Limited z-axis support

The layout spec must support practical z-axis staging features:

- deck level
- raised platforms
- bridges
- balconies
- stairs
- ramps
- traps/lifts as named anchors or areas

The first implementation may render z as labels and layering in plan-view SVG rather than true 3D.

The system should explicitly avoid true 3D in the first implementation. Store z/elevation in the normalized model, render it as 2D plan-view metadata, and validate vertical movement through named connectors such as stairs, ramps, and lifts.

### R6. Named anchors and areas

The layout spec must support named locations:

- doors
- entrances
- exits
- voms
- traps
- stairs
- set-piece anchors
- prop preset positions

Blocking events should reference these by ID.

### R7. Fixed and movable set pieces

The layout must distinguish:

- fixed set pieces
- movable set pieces
- furniture
- practical objects
- preset props

The first version may render these as simple SVG primitives.

### R8. Actor placement and movement

Blocking must support:

- initial placement
- movement/cross
- entrances
- exits
- facing
- holds
- notes
- cue references

Blocking must also support snapshots/checkpoints so diagrams do not depend on fragile full-play state replay. A producer should be able to restate actor/prop/set-piece positions at scene or beat boundaries and have rendering start from the nearest checkpoint.

### R9. Prop interactions

Blocking should support:

- pickup
- put
- give
- carry
- preset

The first implementation may parse prop interactions later, but the data model should leave room for them.

### R10. Cue-lite integration

Blocking must be able to reference cue IDs, especially:

- lighting cues: `LX.12`, `LQ.12`
- sound cues: `SND.04`, `SQ.04`
- set/shift cues: `SHIFT.02`
- grouped cues: `Q.17`

Cue-lite should support focus references such as areas, actors, props, and set pieces, but must not become a full lighting-control format.

### R11. Static SVG output

Stager must be able to generate static SVG blocking charts.

The first rendering target should be plan view.

### R12. Optional animation path

The data model should support later animation using:

- generated SVG paths
- actor glyph groups
- timing events
- a small JS-controlled timeline

Native SVG animation may be used for export/demo, but the preferred interactive model is SVG plus JavaScript.

### R13. Offline/local-first

The compiler and generated assets must work without server infrastructure.

## Non-goals

- Full DMX, lighting-console, or fixture patch modeling.
- Full choreography notation.
- Full 3D rendering.
- Safety-critical automation control.
- Automatic replacement of stage-manager judgment.
- Mermaid compatibility.
- Runtime parsing of authoring DSL inside Cuemaster.

## Acceptance criteria for first vertical slice

Given a `production.md` containing one layout block and one blocking block, Stager can:

1. parse the blocks
2. resolve the standard 9-zone grid
3. normalize blocking events into JSON
4. render a static SVG showing:
   - stage boundary
   - grid labels
   - actor positions
   - movement path arrows
   - cue badges
5. pass parser and renderer tests
