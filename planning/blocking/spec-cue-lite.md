# Cue-Lite Spec Draft

## Purpose

Cue-lite defines coordination cues, especially lighting, sound, set shifts, and grouped cues.

It is not a full lighting-design, DMX, or console-file format.

## Block form

```markdown
[[cues]]
...
[[/cues]]
```

## Cue IDs

Recommended prefixes:

```text
LX.12      lighting cue
LQ.12      alternate lighting cue prefix
SND.04     sound cue
SQ.04      alternate sound cue prefix
SHIFT.02   set/scene-shift cue
Q.17       grouped/called cue
```

## Lighting cue

```text
LX.12 type=lighting label="Special on Hamlet" focus=C fade=1.5
LX.13 type=lighting label="Widen to throne" focus=[C,UC] fade=2.0
LX.24 type=lighting label="Moonlight catches Ophelia" focus=OPH fade=3.0 color="cool blue"
```

Supported fields:

- `type`
- `label`
- `focus`
- `fade`
- `color`
- `intensity`
- `follow`
- `note`

The meaning of `color`, `intensity`, and `follow` is advisory only in v0.1.

## Sound cue

```text
SND.04 type=sound label="Distant bell"
```

Supported fields:

- `type`
- `label`
- `source`
- `fade`
- `note`

## Set/shift cue

```text
SHIFT.02 type=shift label="Bridge reveal"
```

Supported fields:

- `type`
- `label`
- `target`
- `note`

## Group cue

```text
Q.17 type=group cues=[LX.13,SND.04,SHIFT.02] label="Revelation cue"
```

Group cues are for coordination/calling. They should not erase the underlying cues.

## Cue references from blocking

```text
cue LX.24
cue LX.24 at=HAM.arrive(C)
cue Q.17 at=end
```

## Non-goals

Cue-lite must not model:

- fixture patch
- DMX universes
- fixture personalities
- console syntax
- safety-critical automation
- lighting paperwork replacement

## Validation

- Cue IDs should be unique.
- `type` should be one of `lighting`, `sound`, `shift`, `group`, or `other`.
- Focus references should resolve to layout locations, actors, props, or set pieces where possible.
- Unknown focus references should warn, not fail.
