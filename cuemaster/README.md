# Cuemaster

Cuemaster is the local-first rehearsal app for actors learning lines from Stager-generated Playbooks.

This package starts as a Vite + React + TypeScript web app. The initial implementation target is browser/PWA import, validation, local storage, role selection, and rehearsal playback. Native iPhone/Android packaging should come later via Capacitor after the core import and rehearsal loop is stable.

## Development

```sh
npm install
npm run dev
```

## Key Boundaries

- `src/specs/`: Playbook manifest contract and validation.
- `src/domain/`: Cuemaster runtime model after manifest import.
- `src/playbook/`: Playbook zip/import/normalization logic.
- `src/storage/`: local persistence.
- `src/rehearsal/`: cue/response playback and line progression.
- `src/platform/`: browser/native filesystem and audio seams.

## Tests

```sh
npm test
npm run e2e
```
