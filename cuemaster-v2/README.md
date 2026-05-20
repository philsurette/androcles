# Cuemaster V2

Cuemaster v2 is a clean rebuild of the actor rehearsal app. It keeps the Playbook contract and reuses stable Cuemaster v1 code deliberately, but it rebuilds the rehearsal/session model around Practice Flow and one primary playback surface.

The implementation plan is [planning/cuemaster/v2_rebuild_plan.md](../planning/cuemaster/v2_rebuild_plan.md).

## Goals

- One primary Play/Pause control.
- One actor rehearsal surface.
- Practice Flow as the core session model.
- PWA-first hosted deployment.
- No microphone permission for Listen, Try, or Try + Hear Line flows.

## Development

This workspace is intentionally separate from `../cuemaster` so v1 can remain usable while v2 is built.

```sh
npm install
npm run dev
```

The v2 dev server uses `http://127.0.0.1:5174` so it can run alongside Cuemaster v1 on port `5173`.

## Current State

The first vertical slice is implemented:

- A Fairies-derived demo fixture loads by default.
- A real `.playbook.zip` can be imported in the browser.
- Playbook manifests are normalized into a v2 domain model.
- Role rehearsal supports Manual, Listen, Try, and Try + Hear Line flows.
- Whole Play renders the script stream with clickable entries.
- A shared playback runner handles audio, waits, advancing, pausing, and completion.
- Blocking notes are visible and open a blocking sheet. Diagram rendering is still a follow-on item until the Playbook includes the `format_version: 1.1.0` staging bundle.

## Wireframes

The current functional wireframe can be opened directly in a browser:

```text
mockups/index.html
```

It does not require `npm install`.
