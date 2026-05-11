# LineRecorder

LineRecorder is the actor-facing Quince recording app. It imports Stager role recording packs, records accepted WAV takes by `segment_id`, and exports role recording packages for Stager import.

The app is browser-first and local-only. It is scaffolded as a sibling of `cuemaster/` so both apps can share proven architecture before any shared package is introduced.

## Development

Install dependencies from this directory, then run:

```sh
npm run dev
npm run test
npm run build
```

The LineRecorder dev server is pinned to `http://127.0.0.1:5174`.

## Boundaries

- `src/domain/`: app domain records with no React imports.
- `src/specs/`: manifest contracts and validation.
- `src/platform/`: browser capability adapters such as microphone access.
- `src/storage/`: IndexedDB persistence.
- `src/ui/`: React screens and components.

Microphone permission, device selection, constraints, metering, and cleanup should stay small and portable so the code can later move to shared Quince browser code or be copied into Cuemaster.
