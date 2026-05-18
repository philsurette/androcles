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
anchor door_l kind=exit at=(-18,20,0)
set table kind=furniture at=C size=(5,3) fixed=true
prop letter preset=table
```

Acceptance tests:

- parses stage dimensions
- generates 9-zone grid
- resolves aliases
- parses anchors
- parses set pieces
- parses prop presets

## Milestone 3 — Blocking parser

Implement minimal statements:

```text
HAM @ DL
HAM move DL -> C dur=2.2
HAM face OPH
OPH enter vom_dr -> DR dur=1.6
OPH exit door_l dur=1.4
cue LX.24
```

Acceptance tests:

- parses placement
- parses move
- parses facing
- parses enter/exit
- parses cue reference
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
- unknown locations produce diagnostics

## Milestone 6 — Static SVG renderer

Render:

- stage rectangle
- grid labels
- actors
- movement paths
- cue badges

Acceptance tests:

- produces valid-looking SVG string
- includes `viewBox`
- includes actor IDs/classes
- includes path for movement
- deterministic output for snapshot testing

## Milestone 7 — Playbook integration

Add compiled outputs to Playbook assets.

Acceptance tests:

- sample `production.md` produces normalized JSON
- sample `production.md` produces SVG
- Cuemaster can load/display SVG as a static asset, if relevant code exists
- old text-only blocking entries are no longer required in the Playbook manifest

## Milestone 8 — Timeline skeleton

Generate timeline JSON without playback.

Acceptance tests:

- timed moves produce start/end or duration records
- cue events appear in timeline
- untimed events are omitted or marked static

## Later milestones

- editor diagnostics
- layout preview UI
- drag-to-adjust locations in Stager
- animation playback
- audio synchronization
- prop state validation
- z-axis path validation
- support for multiple layouts per production
