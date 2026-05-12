# LineRecorder

LineRecorder is the actor-facing Quince recording app. It imports Stager Recording Requests, records accepted WAV takes by `segment_id`, and exports role recording packages for Stager import.

The app is browser-first and local-only. It is scaffolded as a sibling of `cuemaster/` so both apps can share proven architecture before any shared package is introduced.

## Development

Install dependencies from this directory, then run:

```sh
npm run dev
npm run test
npm run build
```

The LineRecorder dev server is pinned to `http://127.0.0.1:5174/` so it can run beside Cuemaster on Vite's default `5173`.

## Troubleshooting

Microphone access requires a secure browser context. Use `http://127.0.0.1:5174/` during development, not a plain LAN hostname unless it is served securely.

If the browser denies microphone permission, enable microphone access in the browser site settings and reload LineRecorder. On macOS, also check System Settings > Privacy & Security > Microphone for the browser.

If the meter shows no signal, check that the selected input is the intended microphone, then use Stop Mic and Start Setup again. If the device list is empty, grant microphone permission once and reopen the selector.

If input is too quiet, move closer to the microphone, choose a different input, or raise the operating-system input level. Avoid recording many lines until setup shows a usable level.

If input clips, move farther from the microphone or lower the operating-system input level. Clipped takes should be retried.

Clean Recording Mode is the default for performance quality. Use Noisy Room Mode only when the room or microphone needs browser echo cancellation, noise suppression, and automatic gain control.

If export fails, browser storage may be full. Remove old local takes by replacing unneeded recordings, export a smaller partial package, or clear site data after exporting anything you need to keep.

## Boundaries

- `src/domain/`: app domain records with no React imports.
- `src/specs/`: manifest contracts and validation.
- `src/platform/`: browser capability adapters such as microphone access.
- `src/storage/`: IndexedDB persistence.
- `src/ui/`: React screens and components.

Microphone permission, device selection, constraints, metering, and cleanup should stay small and portable so the code can later move to shared Quince browser code or be copied into Cuemaster.
