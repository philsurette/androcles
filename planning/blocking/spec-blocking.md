# Blocking Spec Draft

## Purpose

The blocking spec defines actions by actors, props, and set pieces against a scene snapshot. A scene snapshot references one named set, which supplies the scenic layout for that scene.

It should be readable enough for rehearsal notes but structured enough for SVG rendering.

## Authoring form

The authoring form is open. A fenced `[[blocking]]` block is useful for multi-event beats and examples in this starter pack, but it should not be treated as the only or preferred syntax for every action.

Possible beat block:

```markdown
[[blocking beat=b12 scene=1.2 line=HM-042]]
HM move DL -> C dur=2.2
cue LX.24 at=HM.arrive(C)
[[/blocking]]
```

Possible inline or line-local action:

```markdown
HAMLET: Now might I do it pat— (_/action: move DL -> C dur=2.2_)
HAMLET: Now might I do it pat— (_/HM: move DL -> C dur=2.2_)
```

The final design may support both: block form for standalone staging beats, inline form for movement/business that belongs inside a spoken line.

Recommended block attributes:

- `beat`
- `scene`
- `line`
- `time`
- `set`
- `variant`

## Minimal syntax

### Actor placement

```text
HM @ DL
HM @ (2,8,0) face=house
```

Equivalent explicit form:

```text
HM place DL
```

Placement is absolute. It may be used as an author correction or checkpoint even if prior movement state is incomplete.

### Movement

```text
HM move DL -> C dur=2.2
HM cross DL -> C dur=2.2 curve=arc
HM -> C
```

Supported movement options:

- `dur=seconds`
- `curve=line|arc|bezier`
- `speed=slow|normal|fast`
- `face=house|target|path|ACTOR_ID|angle`
- `via=LOCATION`

### Facing

```text
HM face OP
HM face house
HM face 180
```

### Entrance

```text
OP enter vom_dr -> DR dur=1.6
```

### Exit

```text
OP exit door_l dur=1.4
```

### Hold

```text
hold dur=0.5
HM hold dur=1.0
```

### Prop interaction

```text
HM pickup sword from=table
HM put sword at=table
HM give letter to=OP
```

Prop interactions may be v0.2 if v0.1 needs to stay smaller.

### Gesture / business

```text
HM gesture point target=trap_c hand=R
HM business "checks the letter, then hides it"
```

Business is intentionally semi-structured.

### Cue reference

```text
cue LX.24
cue LX.24 at=HM.arrive(C)
cue Q.17 at=end
```

### Notes

```text
note "Director wants this cross to feel reluctant."
```

## State and snapshots

Rendering a beat requires knowing where actors, props, and movable set pieces are at that moment. Replaying every prior event from the start of the play is brittle, so the staging model should support explicit snapshots/checkpoints.

A `snapshot` is authoritative state at a beat, scene, or production boundary. Producers should normally define a starting snapshot at the beginning of each scene, then write only meaningful changes after that.

```text
snapshot
HM @ DL face=CD
CD @ UC
table @ C
letter @ table
```

Scene-start example:

```text
scene 1.2 set=act1 snapshot
HM @ DL face=CD
CD @ UC
OP offstage via=door_l
table @ C
sword @ table
```

Rendering should start from the nearest prior snapshot and apply events up to the requested beat. This keeps diagrams useful even when earlier blocking is incomplete or has changed.

Rules:

- `snapshot` resets known truth for listed actors/props/set pieces.
- Absolute placement such as `HM @ C` updates state regardless of prior state.
- Movement with explicit `from` should warn if it disagrees with known state.
- Movement without explicit `from` may infer from current state.
- If no current state exists, warn and still render the destination when possible.
- Unknown actor/prop locations should not fail the entire diagram; render them in an "unknown/offstage" list or diagnostics section.

Example:

```text
[[blocking scene=1.2 beat=b12]]
snapshot
HM @ DL face=CD
CD @ UC
sword @ table
[[/blocking]]

[[blocking scene=1.2 beat=b13]]
HM move DL -> C dur=2.5
HM pickup sword from=table
cue LX.12 at=HM.arrive(C)
[[/blocking]]
```

To render `b13`, Stager uses snapshot `b12`, applies `b13`, then renders `HM` at `C`, `CD` at `UC`, and `sword` carried by `HM`.

The first standalone renderer implements the same idea with ordered beat blocks:

```text
scene 1.3 set=act1 snapshot
HM @ balcony_l face=CD
CD @ DC
OP @ deck_l face=HM
sword @ table

beat b1 scene=1.3
HM move balcony_l -> UC face=OP
OP move deck_l -> C face=HM

beat b2 scene=1.3
CD move DC -> DR
sword remove
```

Rendering `--scene 1.3 --beat b2` starts from the `scene 1.3 set=act1 snapshot`, resolves locations against set `act1`, applies `b1`, then applies `b2`.

## Timing model

Timing should be layered:

1. Explicit event timing wins.
2. Beat/line/audio timing provides defaults.
3. Untimed events render statically.

Examples:

```text
HM move DL -> C start=0.4 dur=2.2
HM move DL -> C start=lineStart+0.5 end=lineEnd
HM move DL -> C
```

The first implementation may only support `dur`.

## Location references

Locations may be:

- standard areas: `DL`, `C`, `UR`
- aliases: `DSR`, `USL`
- selected-set custom areas: `balcony`
- selected-set anchors: `door_l`
- selected-set set pieces: `table`
- selected-set props: `letter`
- numeric coordinates: `(x,y)` or `(x,y,z)`

## Normalization

All blocking statements should normalize to explicit event records.

Example:

```text
HM move DL -> C dur=2.2
```

Normalizes to:

```json
{
  "type": "move",
  "actor": "HM",
  "from": {"source": "DL", "x": -12, "y": 4, "z": 0},
  "to": {"source": "C", "x": 0, "y": 12, "z": 0},
  "duration": 2.2
}
```

## Validation rules

- Actor IDs must be declared or inferable from the production cast.
- Locations must resolve through the scene's selected set plus the invariant stage grid.
- Cue IDs should resolve through cue-lite definitions, but missing cue definitions may be warnings.
- Events with z changes should warn if no stairs/ramp/lift path is available.
- Prop interactions should warn if prop state is impossible or unknown.
