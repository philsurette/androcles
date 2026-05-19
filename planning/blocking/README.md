# Quince Staging DSL Starter Pack

This folder contains starter material for implementing a lightweight text-based staging/blocking system for Quince.

The goal is to let producers/directors/stage managers embed stage layout, blocking, and simple coordination cues in `production.md`, then have Stager compile that text into:

- normalized staging data
- static SVG blocking diagrams
- optional animation timelines
- Playbook-ready assets for Cuemaster

## Planning stance

These documents are a starting point, not a settled specification. They capture one possible direction for replacing the earlier blocking-note implementation, but individual syntax choices should be evaluated against real producer ergonomics before implementation.

There is no requirement to maintain backward compatibility with the current blocking-note implementation because no real productions depend on it. The handful of existing `fairies` blocking notes were test data and may be rewritten or removed during rollout.

Implementation should remove or replace the current blocking-note parser, publication-diff handling, Recording Request context, Playbook entries, and Cuemaster display behavior as needed. However, the old inline shape `(_/action: ..._)` or a close variant may still be the right authoring surface for line-local actions. Do not assume `[[blocking ...]]` blocks are better for every use case.

## Files

- `codex-start-prompt.md` — prompt to paste into Codex.
- `requirements.md` — product requirements and non-goals.
- `architecture.md` — proposed system architecture.
- `spec-layout.md` — layout DSL draft.
- `spec-blocking.md` — blocking DSL draft.
- `spec-cue-lite.md` — cue/lighting-lite DSL draft.
- `spec-rendering-animation.md` — SVG rendering and animation design.
- `stage_set_scene_design.md` — stage/set/scene terminology, syntax direction, CLI shape, and rollout plan.
- `diagram_state_rendering_plan.md` — design and implementation plan for refactoring rendering around a stable diagram-state JSON contract before further blocking feature work.
- `implementation-plan.md` — staged implementation plan and acceptance tests.
- `point_in_time_svg_implementation_plan.md` — focused plan for a standalone stage-description-to-SVG vertical slice before Quince/Playbook integration.
- `future-features.md` — animation, timeline playback, and richer staging features deferred from the active implementation path.
- `examples/README.md` — standalone point-in-time stage examples and render commands.
- `examples/production-staging-example.md` — sample embedded usage in `production.md`.

## Current Terminology

- **Block CLI**: standalone command surface for staging/blocking workflows, available as `./block`.
- **Staging file**: standalone input file containing stage geometry, reusable sets, scene snapshots, and optional blocking beats. The default filename is `staging.txt`.
- **Stage**: invariant physical playing space: type, dimensions, units, orientation, coordinate system, and generated grid.
- **Set**: reusable scenic setup for one or more scenes. A set owns levels, anchors, connectors, set pieces, and prop presets.
- **Scene snapshot**: authoritative initialization for a scene, written as `scene <scene_id> set=<set_id> snapshot`.
- **Blocking beat**: ordered group of blocking directions, written as `beat <beat_id> scene=<scene_id>`.
- **Blocking direction**: a single state change such as placement, move, enter, exit, or remove.
- **Point-in-time state**: computed state after applying a scene snapshot plus beats up to the requested beat.
- **Blocking diagram**: generated SVG for a point-in-time state.

Example stage-only command:

```sh
./block stage plays/hamlet/staging.txt
```

Example set-only command:

```sh
./block set \
  plays/hamlet/staging.txt \
  --set act1
```

Example scene snapshot command:

```sh
./block scene \
  plays/hamlet/staging.txt \
  --scene 1.2
```

Example beat command:

```sh
./block beat \
  plays/hamlet/staging.txt \
  --scene 1.3 \
  --beat b2
```

Transitional point-in-time render alias:

```sh
./block render \
  plays/hamlet/staging.txt \
  --scene 1.3 \
  --beat b2
```

When run from a play folder, the input defaults to `staging.txt`.

When the input is under `plays/<play_id>/`, `--out` defaults to `build/<play_id>/staging/`.

## Design stance

This is deliberately not a full theatre production-control standard. It is a small, local-first, Markdown-friendly staging layer that can be edited by humans and rendered by Stager.

The system should keep three concerns separate:

1. **Stage** defines invariant performance-space geometry.
2. **Set** defines reusable scenic setup for one or more scenes.
3. **Blocking** defines actor, prop, and movable set-piece events against a scene snapshot.
4. **Cue-lite** defines coordination cues, especially lighting/sound/set-shift references.

Before adding more blocking features, the rendering pipeline should be refactored to use diagram-state JSON as the renderer contract:

```text
ResolvedSnapshot -> DiagramState JSON -> renderer adapter
```

See [diagram_state_rendering_plan.md](diagram_state_rendering_plan.md).

Syntax remains open. A likely final design may use larger fenced blocks for layout and cue definitions, while allowing terse inline or nearby action notation for line-local movement and business.

The compiler may render static SVG first. Animation should be added as a generated visualization layer, not as a requirement of the authoring syntax.
