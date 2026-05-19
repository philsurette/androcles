# Implementation Plan

## Milestone 0 — Discovery

- Locate existing Quince/Stager Markdown parsing code.
- Identify existing block syntax conventions.
- Identify Playbook output structure.
- Identify current test framework.
- Decide where staging modules belong.
- Identify existing blocking-note code paths and tests that should be removed or replaced.
- Remove or rewrite the test-only `fairies` blocking notes so the old syntax is not treated as a compatibility contract.
- Decide the authoring syntax for line-local actions. Explicitly compare fenced `[[blocking]]` blocks with inline syntax such as `(_/action: ..._)` and target-specific variants.

Acceptance tests:

- current production fixtures do not require the old blocking implementation
- old blocking-note parser behavior is either removed or explicitly isolated as temporary dead-end compatibility code
- accepted replacement syntax covers line-local action without forcing every movement into a standalone fenced block

## Milestone 1 — Block extraction

Implement extraction of selected staging authoring forms. The starter examples use:

- `[[layout ...]] ... [[/layout]]`
- `[[blocking ...]] ... [[/blocking]]`
- `[[cues ...]] ... [[/cues]]`

If inline action syntax is chosen for line-local blocking, include it in this milestone rather than treating it as a later compatibility feature.

Acceptance tests:

- extracts one block
- extracts multiple blocks
- preserves block attributes
- preserves source line/column if feasible
- reports unclosed blocks
- parses the accepted line-local action syntax, if selected
- ignores or rejects removed blocking-note syntax according to the chosen removal strategy

## Milestone 2 — Layout parser

Implement a minimal parser for:

```text
stage type=proscenium width=36 depth=24 audience=south
grid standard=9
setup act1
anchor door_l kind=exit at=(-18,20,0)
piece table kind=table at=C size=(5,3) fixed=true
prop letter preset=table
```

Acceptance tests:

- parses stage dimensions
- parses named setup/set blocks
- generates 9-zone grid
- resolves aliases
- parses anchors inside a setup
- parses set pieces inside a setup using `piece`
- parses prop presets inside a setup
- stores z/elevation metadata without requiring 3D rendering
- parses stairs/ramps/lifts as level connectors
- rejects or diagnoses setup-owned records outside a setup

## Milestone 3 — Blocking parser

Implement minimal statements:

```text
HM @ DL
HM move DL -> C dur=2.2
HM face OP
OP enter vom_dr -> DR dur=1.6
OP exit door_l dur=1.4
cue LX.24
snapshot
```

Acceptance tests:

- parses placement
- parses move
- parses facing
- parses enter/exit
- parses cue reference
- parses snapshots/checkpoints
- gives useful diagnostics for malformed lines

## Milestone 4 — Cue-lite parser

Implement:

```text
LX.12 type=lighting label="Special on Hamlet" focus=C fade=1.5
SND.04 type=sound label="Distant bell"
Q.17 type=group cues=[LX.12,SND.04] label="Combined cue"
```

Acceptance tests:

- parses cue ID
- parses type/label/focus/fade
- parses grouped cues
- warns on duplicate cue IDs

## Milestone 5 — Resolver and normalized model

Implement reference resolution:

- areas
- aliases
- anchors
- set pieces
- props
- cue references

Acceptance tests:

- `DL` resolves to center of downstage-left area
- `DSR` resolves as alias of `DR`
- `table` resolves to set-piece location
- scene snapshots resolve against their referenced setup/set
- two scenes can share one setup/set
- two scenes can use different setup/set records with different levels/connectors
- unknown locations produce diagnostics
- vertical moves warn when no stair/ramp/lift connector exists
- rendering state resolves from the nearest prior snapshot rather than from full-play replay

## Milestone 6 — Point-in-time state resolver

Renderers should be able to request a scene state at a specific beat. The resolver should:

- start with the scene-start snapshot
- load the scene's referenced setup/set before resolving placements
- apply ordered blocking beats for that scene up to the requested beat
- update actor, prop, and movable set-piece locations
- handle enters and exits as state changes
- preserve diagnostics for unknown or inconsistent state

Initial supported beat statements:

```text
HM @ C
HM move DL -> C
HM -> C
OP enter door_l -> DL
OP exit via=door_r
sword @ table
sword remove
```

Acceptance tests:

- [x] scene-start snapshot initializes state
- [x] absolute placement updates state
- [x] move/cross updates the entity to the destination
- [x] enter introduces an offstage actor/prop into the rendered state
- [x] exit/remove moves an entity to the offstage list
- [x] rendering an unknown beat produces a diagnostic
- [x] resolving a later beat applies all earlier beats for the same scene in source order

## Milestone 7 — Static SVG renderer

Render:

- stage rectangle
- grid labels
- selected setup/set scenery
- actors
- movement paths
- cue badges

Acceptance tests:

- produces valid-looking SVG string
- includes `viewBox`
- `block stage` renders only invariant stage geometry
- `block set` renders selected set scenery without scene actor placements
- scene rendering includes the selected setup/set
- includes actor IDs/classes
- deterministic output for snapshot testing
- labels elevated levels in 2D plan view
- renders actor level/elevation badges for non-deck positions
- includes diagnostics for unknown actor/prop state instead of failing the whole diagram

Movement path arrows and cue badges are future refinements after stateful point-in-time rendering is reliable.

## Milestone 8 — Playbook integration

Add compiled outputs to Playbook assets.

Acceptance tests:

- sample `production.md` produces normalized JSON
- sample `production.md` produces SVG
- Cuemaster can load/display SVG as a static asset, if relevant code exists
- old text-only blocking entries are no longer required in the Playbook manifest

## Later milestones

- editor diagnostics
- layout preview UI
- drag-to-adjust locations in Stager
- prop state validation
- z-axis path validation
- support for multiple layouts per production
