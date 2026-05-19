# Quince Staging And Blocking

This folder contains the active design material for Quince's lightweight text-based staging/blocking system.

The goal is to let producers/directors/stage managers embed stage layout, blocking, and simple coordination cues in `production.md`, then have Stager compile that text into:

- normalized staging data
- static SVG blocking diagrams
- optional animation timelines
- Playbook-ready assets for Cuemaster

## Current Status

The static blocking MVP is complete. Producers can place staging notes in `production.md`; Stager exports `build/<play_id>/staging/staging.txt`; the Block CLI renders stage, set, scene, and beat diagrams; Playbooks package DiagramState checkpoints, deltas, and SVG icons; and Cuemaster renders those packaged diagrams on demand from blocking notes.

The next work should build on this pipeline rather than reintroducing direct SVG packaging or runtime parsing of authoring syntax in Cuemaster:

```text
production.md inline staging
  -> exported staging.txt
  -> parsed staging model
  -> resolved stage/set/scene/beat state
  -> DiagramState JSON
  -> Python SVG renderer / Cuemaster renderer / future renderers
```

## Planning Stance

These documents are a starting point, not a settled specification. They capture one possible direction for replacing the earlier blocking-note implementation, but individual syntax choices should be evaluated against real producer ergonomics before implementation.

There is no requirement to maintain backward compatibility with the current blocking-note implementation because no real productions depend on it. The handful of existing `fairies` blocking notes were test data and may be rewritten or removed during rollout.

Implementation should remove or replace the current blocking-note parser, publication-diff handling, Recording Request context, Playbook entries, and Cuemaster display behavior as needed. However, the old inline shape `(_/action: ..._)` or a close variant may still be the right authoring surface for line-local actions. Do not assume `[[blocking ...]]` blocks are better for every use case.

## Active Files

- `requirements.md` — product requirements and non-goals.
- `architecture.md` — current staging architecture and data-flow direction.
- `spec-layout.md` — layout DSL draft.
- `spec-blocking.md` — blocking DSL draft.
- `spec-cue-lite.md` — cue/lighting-lite DSL draft.
- `spec-rendering-animation.md` — SVG rendering and animation design.
- `stage_set_scene_design.md` — stage/set/scene terminology, syntax direction, CLI shape, and rollout plan.
- `implementation-plan.md` — original staged implementation plan; treat this as historical context where it conflicts with the current stage/set/scene and DiagramState implementation.
- `future-features.md` — animation, timeline playback, and richer staging features deferred from the active implementation path.
- `examples/README.md` — standalone point-in-time stage examples and render commands.
- `examples/production-staging-example.md` — sample embedded usage in `production.md`.

Completed and superseded plans are archived under `planning/completed/`.

## Current Terminology

- **Block CLI**: standalone command surface for staging/blocking workflows, available as `./block`.
- **Staging file**: exported staging overlay artifact containing stage geometry, reusable sets, scene snapshots, and optional blocking beats. It is normally generated from `production.md` at `build/<play_id>/staging/staging.txt`.
- **Stage**: invariant physical playing space: type, dimensions, units, orientation, coordinate system, and generated grid.
- **Set**: reusable scenic setup for one or more scenes. A set owns levels, anchors, connectors, set pieces, and prop presets.
- **Scene snapshot**: authoritative initialization for a scene, written in the exported overlay as `scene <scene_id> set=<set_id>`.
- **Blocking beat**: ordered group of blocking directions, written in the exported overlay as `<beat_id> @ <production-id>`.
- **Blocking direction**: a single state change such as placement, move, enter, exit, or remove.
- **Point-in-time state**: computed state after applying a scene snapshot plus beats up to the requested beat.
- **DiagramState**: resolved, renderer-neutral JSON describing the stage, set, entities, icons, labels, diagnostics, and movement hints for a point in time.
- **Blocking diagram**: generated visual rendering of a DiagramState, currently SVG in Python and Cuemaster.

Example stage-only command:

```sh
./block export plays/hamlet/production.md
./block stage build/hamlet/staging/staging.txt
```

Normal Stager and Quince build commands export the staging overlay automatically before building:

```sh
./main text
./main playbook
quince build-playbook
quince build-audioplay
```

Use `--no-staging` on those build commands when you intentionally want to skip this generated artifact. The standalone `./block export` command remains useful when you only want to refresh diagrams without running a larger build.

Example set-only command:

```sh
./block set act1 build/hamlet/staging/staging.txt
```

Example scene snapshot command:

```sh
./block scene 1.2 build/hamlet/staging/staging.txt
```

Example beat command:

```sh
./block beat 1.3 b2 build/hamlet/staging/staging.txt
```

Transitional point-in-time render alias:

```sh
./block render \
  build/hamlet/staging/staging.txt \
  --scene 1.3 \
  --beat b2
```

When run from a play folder, render commands default to `build/<play_id>/staging/staging.txt`; run `./block export` first if no build command has refreshed that artifact yet.

From a play folder, the same commands can be shortened to `./block set act1`, `./block scene 1.2`, and `./block beat 1.3 b2`.

When the input is under `plays/<play_id>/` or `build/<play_id>/staging/`, `--out` defaults to `build/<play_id>/staging/`.

## Design stance

This is deliberately not a full theatre production-control standard. It is a small, local-first, Markdown-friendly staging layer that can be edited by humans and rendered by Stager.

The system should keep three concerns separate:

1. **Stage** defines invariant performance-space geometry.
2. **Set** defines reusable scenic setup for one or more scenes.
3. **Blocking** defines actor, prop, and movable set-piece events against a scene snapshot.
4. **Cue-lite** defines coordination cues, especially lighting/sound/set-shift references.

Syntax remains open. A likely final design may use larger fenced blocks for layout and cue definitions, while allowing terse inline or nearby action notation for line-local movement and business.

The compiler may render static SVG first. Animation should be added as a generated visualization layer, not as a requirement of the authoring syntax.
