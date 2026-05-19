# Blocking Spec Draft

## Purpose

The blocking spec defines actions by actors, props, and set pieces against a declared layout.

It should be readable enough for rehearsal notes but structured enough for SVG rendering.

## Authoring form

The authoring form is open. A fenced `[[blocking]]` block is useful for multi-event beats and examples in this starter pack, but it should not be treated as the only or preferred syntax for every action.

Possible beat block:

```markdown
[[blocking beat=b12 scene=1.2 line=HAM-042]]
HAM move DL -> C dur=2.2
cue LX.24 at=HAM.arrive(C)
[[/blocking]]
```

Possible inline or line-local action:

```markdown
HAMLET: Now might I do it pat— (_/action: move DL -> C dur=2.2_)
HAMLET: Now might I do it pat— (_/HAM: move DL -> C dur=2.2_)
```

The final design may support both: block form for standalone staging beats, inline form for movement/business that belongs inside a spoken line.

Recommended block attributes:

- `beat`
- `scene`
- `line`
- `time`
- `layout`
- `variant`

## Minimal syntax

### Actor placement

```text
HAM @ DL
HAM @ (2,8,0) face=house
```

Equivalent explicit form:

```text
HAM place DL
```

Placement is absolute. It may be used as an author correction or checkpoint even if prior movement state is incomplete.

### Movement

```text
HAM move DL -> C dur=2.2
HAM cross DL -> C dur=2.2 curve=arc
HAM -> C
```

Supported movement options:

- `dur=seconds`
- `curve=line|arc|bezier`
- `speed=slow|normal|fast`
- `face=house|target|path|ACTOR_ID|angle`
- `via=LOCATION`

### Facing

```text
HAM face OPH
HAM face house
HAM face 180
```

### Entrance

```text
OPH enter vom_dr -> DR dur=1.6
```

### Exit

```text
OPH exit door_l dur=1.4
```

### Hold

```text
hold dur=0.5
HAM hold dur=1.0
```

### Prop interaction

```text
HAM pickup sword from=table
HAM put sword at=table
HAM give letter to=OPH
```

Prop interactions may be v0.2 if v0.1 needs to stay smaller.

### Gesture / business

```text
HAM gesture point target=trap_c hand=R
HAM business "checks the letter, then hides it"
```

Business is intentionally semi-structured.

### Cue reference

```text
cue LX.24
cue LX.24 at=HAM.arrive(C)
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
HAM @ DL face=CLA
CLA @ UC
table @ C
letter @ table
```

Scene-start example:

```text
scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
OPH offstage via=door_l
table @ C
sword @ table
```

Rendering should start from the nearest prior snapshot and apply events up to the requested beat. This keeps diagrams useful even when earlier blocking is incomplete or has changed.

Rules:

- `snapshot` resets known truth for listed actors/props/set pieces.
- Absolute placement such as `HAM @ C` updates state regardless of prior state.
- Movement with explicit `from` should warn if it disagrees with known state.
- Movement without explicit `from` may infer from current state.
- If no current state exists, warn and still render the destination when possible.
- Unknown actor/prop locations should not fail the entire diagram; render them in an "unknown/offstage" list or diagnostics section.

Example:

```text
[[blocking scene=1.2 beat=b12]]
snapshot
HAM @ DL face=CLA
CLA @ UC
sword @ table
[[/blocking]]

[[blocking scene=1.2 beat=b13]]
HAM move DL -> C dur=2.5
HAM pickup sword from=table
cue LX.12 at=HAM.arrive(C)
[[/blocking]]
```

To render `b13`, Stager uses snapshot `b12`, applies `b13`, then renders `HAM` at `C`, `CLA` at `UC`, and `sword` carried by `HAM`.

## Timing model

Timing should be layered:

1. Explicit event timing wins.
2. Beat/line/audio timing provides defaults.
3. Untimed events render statically.

Examples:

```text
HAM move DL -> C start=0.4 dur=2.2
HAM move DL -> C start=lineStart+0.5 end=lineEnd
HAM move DL -> C
```

The first implementation may only support `dur`.

## Location references

Locations may be:

- standard areas: `DL`, `C`, `UR`
- aliases: `DSR`, `USL`
- custom areas: `balcony`
- anchors: `door_l`
- set pieces: `table`
- props: `letter`
- numeric coordinates: `(x,y)` or `(x,y,z)`

## Normalization

All blocking statements should normalize to explicit event records.

Example:

```text
HAM move DL -> C dur=2.2
```

Normalizes to:

```json
{
  "type": "move",
  "actor": "HAM",
  "from": {"source": "DL", "x": -12, "y": 4, "z": 0},
  "to": {"source": "C", "x": 0, "y": 12, "z": 0},
  "duration": 2.2
}
```

## Validation rules

- Actor IDs must be declared or inferable from the production cast.
- Locations must resolve through the layout.
- Cue IDs should resolve through cue-lite definitions, but missing cue definitions may be warnings.
- Events with z changes should warn if no stairs/ramp/lift path is available.
- Prop interactions should warn if prop state is impossible or unknown.
