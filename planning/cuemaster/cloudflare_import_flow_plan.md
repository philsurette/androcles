# Cuemaster Cloudflare Import Flow Plan

Status: in progress. This plan covers the hosted static Cuemaster flow where actors open the Cloudflare-hosted app and import a local `.playbook.zip` file from disk. Cuemaster remains local-first after import; it does not fetch production data from a backend.

## Goals

- Make the hosted import path obvious to non-technical actors.
- Keep Playbook extraction and storage responsive for large MP3 Playbooks.
- Provide clear diagnostics for invalid Playbooks and browser storage failures.
- Verify the static build works when served from a non-root Cloudflare path.
- Keep manual local file import as the primary supported workflow.

## Non-Goals

- Do not add Google Drive Picker or OAuth in this slice.
- Do not add server-side upload, sync, or account state.
- Do not make Cuemaster download Playbooks automatically from Cloudflare.
- Do not require a native wrapper.

## Phase 1: Hosted Import UX

Checklist:

- [x] Add concise Library-screen copy that explains the hosted app stores imported Playbooks in browser storage.
- [x] Make the import control explicitly name `.playbook.zip` files.
- [x] Show selected filename and file size before/during import.
- [x] Keep extraction/progress states visible while large Playbooks import.
- [x] Show import success text with play title, role count, role names, production source/version, and storage persistence result.
- [x] Keep replacement/import success text distinct so actors know whether a Playbook was added or replaced.
- [x] Add unit tests for import success message formatting.

## Phase 2: Storage And Browser Diagnostics

Checklist:

- [x] Detect and explain quota failures.
- [x] Detect and explain blocked or unavailable IndexedDB, including private browsing and browser policy cases.
- [x] Keep invalid Playbook errors precise and separate from storage failures.
- [x] Show storage usage and persistence status in the About panel.
- [x] Add browser compatibility wording favoring current Chrome, Edge, Firefox, and Safari.
- [x] Add unit tests for storage/browser error mapping.

## Phase 3: Hosted Static Verification

Checklist:

- [x] Build Cuemaster with `npm run build:static`.
- [x] Serve the built `dist/` folder from a nested/subdirectory path to simulate Cloudflare routing.
- [x] Verify the app shell loads with relative assets.
- [x] Verify local file import works from the nested path.
- [x] Verify imported Playbook audio assets are available after reload.
- [x] Add Playwright coverage for the nested-path static import flow.

## Phase 4: Documentation

Checklist:

- [x] Update actor quick-start docs to say the app is hosted but Playbooks are imported from local files.
- [x] Document browser storage limitations and what to try when import fails.
- [x] Document that actors can re-import a newer Playbook without losing compatible local rehearsal progress.
- [x] Cross-link this plan from the deployment implementation plan.

## Acceptance Criteria

- [x] An actor opening the Cloudflare-hosted app can identify the correct `.playbook.zip` file to import.
- [x] Import progress remains visible for large Playbooks.
- [x] Successful imports tell the actor which play and roles are available.
- [x] Storage failures produce actionable user-facing messages.
- [x] The static build imports a fixture Playbook correctly from a Cloudflare-like nested path.
