# Cuemaster

Cuemaster is the local-first rehearsal app for actors learning lines from Stager-generated Playbooks.

This package starts as a Vite + React + TypeScript web app. The initial implementation target is browser/PWA import, validation, local storage, role selection, and rehearsal playback. Native iPhone/Android packaging should come later via Capacitor after the core import and rehearsal loop is stable.

## User Guide

See [USER_GUIDE.md](USER_GUIDE.md) for actor-facing usage, terms, keyboard shortcuts, and microphone troubleshooting.

## Development

```sh
npm install
npm run dev
```

The Cuemaster dev server is pinned to `http://127.0.0.1:5173`.

## Static Deployment Build

```sh
npm run build:static
```

This writes a static deployment bundle to `dist/` with relative asset paths so it can be hosted from either a GitHub Pages user site or project subpath.

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
