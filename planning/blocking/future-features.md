# Future Staging Features

These features are intentionally outside the immediate static point-in-time rendering path.

## Animation And Timeline Playback

Animation should follow after static state resolution is reliable.

Future animation work may include:

- generated timeline JSON
- movement paths with arrow markers
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
- multiple layouts per production
- editor diagnostics
- drag-to-adjust stage locations
