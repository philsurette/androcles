# Codex start prompt: Quince Staging DSL

You are working in the Quince codebase.

## Objective

Implement the first version of a lightweight Markdown-embedded staging DSL for Quince. The DSL should support:

1. A **layout spec** for stage geometry, standard 9-zone areas, custom areas, levels, entrances/exits, stairs/ramps, fixed set pieces, and preset prop locations.
2. A **blocking spec** for actor placement, movement, facing, entrances/exits, prop interactions, gestures/business, holds, notes, and cue references.
3. A **cue-lite spec** for lighting/sound/set-shift coordination cues without modeling full lighting-console or DMX data.
4. A compiler pipeline from `production.md` blocks to normalized JSON and static SVG diagrams.
5. A clean path toward optional animation using generated SVG paths plus a JS-controlled timeline.

## Context

Quince is a local/offline theatre tool suite. Core workflows must not require a server. The staging feature should work inside Stager and compile into Playbook assets consumed by Cuemaster.

The authoring surface is `production.md`. The likely block forms are:

```markdown
[[layout id=main-stage units=ft]]
...
[[/layout]]

[[cues]]
...
[[/cues]]

[[blocking beat=b12 line=HM-042]]
...
[[/blocking]]
```

The implementation should be incremental. Start with parsing and static SVG generation. Do not attempt full animation or rich lighting design in the first pass.

## Read these files first

- `requirements.md`
- `architecture.md`
- `spec-layout.md`
- `spec-blocking.md`
- `spec-cue-lite.md`
- `spec-rendering-animation.md`
- `implementation-plan.md`
- `examples/production-staging-example.md`

## First implementation milestone

Build a minimal vertical slice:

1. Locate `[[layout]]`, `[[cues]]`, and `[[blocking]]` blocks in a Markdown file.
2. Parse a small subset:
   - layout:
     - `stage`
     - `grid standard=9`
     - `anchor`
     - `set`
     - `prop`
   - blocking:
     - `ACTOR @ LOCATION`
     - `ACTOR move FROM -> TO dur=N`
     - `ACTOR face TARGET`
     - `ACTOR enter VIA -> LOCATION dur=N`
     - `ACTOR exit VIA dur=N`
     - `cue CUE_ID`
   - cue-lite:
     - `LX.12 type=lighting label="..." focus=C fade=1.5`
3. Resolve standard stage locations such as `DL`, `DC`, `DR`, `CL`, `C`, `CR`, `UL`, `UC`, `UR`.
4. Produce normalized JSON.
5. Produce one static SVG diagram per blocking block.
6. Add tests for parsing, normalization, and SVG output.

## Constraints

- Keep everything local/offline.
- Keep the syntax forgiving but the normalized model strict.
- Prefer small, dependency-light code.
- Avoid coupling the compiler to a browser.
- Do not make Cuemaster parse authoring DSL directly; Stager should compile it.
- Do not model full lighting fixture data.
- Treat animation as a later generated layer.

## Deliverables

Create or modify code so that a sample `production.md` can produce:

- `staging.normalized.json`
- `blocking-b12.svg`
- parser/normalizer tests
- documentation comments where needed, but avoid noisy method-level comments unless the code is genuinely non-obvious

When making design choices, prefer clear data models and deterministic rendering over clever syntax.
