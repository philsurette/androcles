# Layout Spec Draft

## Purpose

The layout spec defines the physical stage world that blocking references.

It should answer:

- What shape is the stage?
- Where is downstage/upstage/stage-left/stage-right?
- What are the standard areas?
- Where are entrances/exits?
- What platforms, stairs, ramps, bridges, traps, and fixed objects exist?
- Where are preset props?

## Block form

```markdown
[[layout id=main-stage units=ft]]
...
[[/layout]]
```

## Coordinate system

Recommended default:

```text
+x = stageRight
+y = upstage
+z = up
audience = south
origin = downstage-center
```

A stage 36 feet wide and 24 feet deep therefore spans:

```text
x = -18..18
y = 0..24
z = 0+
```

## Minimal statements

### Stage

```text
stage type=proscenium width=36 depth=24 audience=south
```

Supported `type` values for v0.1:

- `proscenium`
- `thrust`
- `arena`
- `blackbox`

The first renderer may only fully support `proscenium`.

### Standard grid

```text
grid standard=9
```

Generated areas:

```text
UL UC UR
CL C  CR
DL DC DR
```

Recommended aliases:

```text
USL -> UL
USC -> UC
USR -> UR
CSL -> CL
CSC -> C
CSR -> CR
DSL -> DL
DSC -> DC
DSR -> DR
```

### Custom area

```text
area balcony polygon=(-10,18, 10,18, 10,22, -10,22) z=8
area table_zone rect=(-3,10,6,4)
```

Rect form:

```text
rect=(x,y,width,depth)
```

Polygon form:

```text
polygon=(x1,y1, x2,y2, x3,y3, ...)
```

### Level

```text
level deck z=0
level bridge polygon=(-10,18, 10,18, 10,22, -10,22) z=8
```

### Stairs

```text
stair stair_l from=(-12,14,0) to=(-10,18,8) steps=10
```

### Ramp

```text
ramp ramp_r from=(12,10,0) to=(10,18,8) slope="1:12"
```

### Anchor

```text
anchor door_l kind=exit at=(-18,20,0)
anchor vom_dr kind=entrance at=(18,3,0)
anchor trap_c kind=trap at=(0,12,0) size=(4,4)
```

Supported `kind` values for v0.1:

- `entrance`
- `exit`
- `door`
- `vom`
- `trap`
- `mark`
- `focus`
- `other`

### Set piece

```text
set table kind=furniture at=C size=(5,3) fixed=true
set wagon1 kind=platform at=(0,18,0) size=(8,4) movable=true
```

### Prop

```text
prop letter preset=table
prop sword preset=throne
prop lantern preset=(2,14,0)
```

## Validation rules

- IDs must be unique within a layout.
- `stage` is required.
- `grid standard=9` requires rectangular stage dimensions.
- All `preset` references must resolve to an area, anchor, set piece, or coordinate.
- z-axis surfaces should be labelled in SVG even if not rendered in 3D.

## Renderer expectations

The static SVG renderer should show:

- stage boundary
- standard zones
- custom areas
- levels/platform outlines
- stairs/ramps
- anchors
- fixed set pieces
- preset props, optionally hidden by default if diagrams become cluttered
