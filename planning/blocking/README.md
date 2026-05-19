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
- `implementation-plan.md` — staged implementation plan and acceptance tests.
- `point_in_time_svg_implementation_plan.md` — focused plan for a standalone stage-description-to-SVG vertical slice before Quince/Playbook integration.
- `examples/README.md` — standalone point-in-time stage examples and render commands.
- `examples/production-staging-example.md` — sample embedded usage in `production.md`.

## Design stance

This is deliberately not a full theatre production-control standard. It is a small, local-first, Markdown-friendly staging layer that can be edited by humans and rendered by Stager.

The system should keep three concerns separate:

1. **Layout** defines the stage world.
2. **Blocking** defines actor, prop, and set-piece events against that world.
3. **Cue-lite** defines coordination cues, especially lighting/sound/set-shift references.

Syntax remains open. A likely final design may use larger fenced blocks for layout and cue definitions, while allowing terse inline or nearby action notation for line-local movement and business.

The compiler may render static SVG first. Animation should be added as a generated visualization layer, not as a requirement of the authoring syntax.
