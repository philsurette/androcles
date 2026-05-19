# Future Staging Features

These features are intentionally outside the completed static point-in-time rendering MVP.

## Spec And Packaging Hardening

- formal JSON schema or validation helper for `quince.blocking.diagram_bundle`
- machine-readable fixture packages for cross-language renderer checks
- configurable checkpoint policy for large scenes
- checkpoint insertion on set changes and delta-size thresholds
- additional delta operations such as `set_visible` and `replace_stage` if real packages need them

## Animation And Timeline Playback

Animation should follow after static state resolution is reliable.

Future animation work may include:

- generated timeline JSON
- richer movement paths with timing, not just current static previous/next arrows
- JavaScript-controlled SVG playback
- pause, scrub, and jump-to-line controls
- audio synchronization
- playback speed controls
- Cuemaster rehearsal integration

Native SVG animation may be useful for export or demos, but JavaScript-controlled playback is likely the better interactive format because it can support pause, scrub, audio sync, and rehearsal controls.

## Rich Blocking Semantics

Later blocking features may include:

- prop ownership and handoff validation
- pickup, put, give, and carry state
- movement path validation across z changes
- reusable set/setup variants across a production
- editor diagnostics
- drag-to-adjust stage locations

## Producer UX

- friendlier authoring UI for stage/set/scene setup
- diagnostics that point back to `production.md` locations
- import/export of alternate blocking files for the same script
- optional visual editor for placing anchors, set pieces, props, and actors

## Cuemaster UX

- mobile pan/zoom and fit-to-entity controls
- actor-only or role-focused diagram filters
- setting to hide blocking diagrams while keeping text blocking notes
- clearer navigation between all blocking notes and role-relevant blocking notes
