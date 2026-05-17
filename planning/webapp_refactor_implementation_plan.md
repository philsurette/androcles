# Cuemaster and LineRecorder Refactor Implementation Plan

This is a resumable implementation plan for making the Cuemaster and LineRecorder browser codebases easier to extend safely. The goal is to reduce feature friction, not redesign the products.

## Current Baseline

- Cuemaster unit tests pass with `npm test`.
- Cuemaster production build passes with `npm run build`, with a Vite chunk-size warning.
- LineRecorder unit tests pass with `npm test`.
- LineRecorder had a TypeScript build failure in `linerecorder/src/ui/App.tsx` where `ProjectDetailProps.onViewInfo` did not accept the item argument used by the caller. Fix this before starting broader refactors.
- The main maintainability risk is large screen files that mix rendering, workflow orchestration, storage, browser APIs, and audio state.

## Working Rules

- Keep behavior stable while extracting structure.
- Prefer one small, verified refactor at a time.
- Do not combine CSS restyling with TypeScript extraction.
- Keep app-specific product behavior in `planning/cuemaster/` and `planning/linerecorder/`; this plan tracks implementation cleanup only.
- Run the relevant app's `npm run build` and `npm test` after each meaningful slice.
- When a slice touches cross-app package contracts, check the source specs in `planning/specs/` instead of redefining schema behavior here.

## Phase 0: Restore Build Confidence

- [x] Verify LineRecorder builds with `npm run build`.
- [x] Verify LineRecorder tests still pass with `npm test`.
- [x] Verify Cuemaster builds with `npm run build`.
- [x] Verify Cuemaster tests still pass with `npm test`.
- [x] Decide whether to add a root-level webapp quality command or keep per-app commands only.
  - Decision: keep per-app commands for now; revisit after the browser refactor settles.

## Phase 1: LineRecorder Structure

- [x] Extract project library workflow from `linerecorder/src/ui/App.tsx`.
  - Target module: `linerecorder/src/ui/hooks/useProjectLibrary.ts`.
  - Own project listing, import, open, delete, selected project, project info mode, and accepted item ids.
  - Keep repository calls injectable or isolated behind a small service boundary.
- [x] Extract microphone setup UI from `App.tsx`.
  - Target component: `linerecorder/src/ui/components/MicrophoneSetup.tsx`.
  - Keep browser microphone/session behavior out of the top-level app component.
- [x] Extract recording workspace components from `App.tsx`.
  - Target components: `ProjectLibrary`, `ProjectDetail`, `ProjectSummary`, `ItemList`, `ItemDetail`, `TakeRecorder`, `ContextBlock`.
  - Move one component per commit-sized slice.
- [x] Extract `TakeRecorder` behavior into a hook.
  - Target module: `linerecorder/src/ui/hooks/useTakeRecorder.ts`.
  - Own start/stop recording, playback, accepted take loading, and status text.
- [x] Move pure helpers out of `App.tsx`.
  - Candidate module: `linerecorder/src/ui/recordingItemPresentation.ts`.
  - Include `recordingItemSearchText`, context comparison, level labels, and recording quality labels.
- [x] Add focused tests for extracted pure helpers before changing behavior around them.
- [x] Stop importing concrete repositories directly from large UI components where practical.
  - Introduce a small `LineRecorderStorage` interface if needed.

## Phase 2: Cuemaster Rehearsal Screen

- [x] Extract rehearsal session settings state from `cuemaster/src/ui/screens/RehearsalScreen.tsx`.
  - Target hook: `cuemaster/src/ui/hooks/useRehearsalSettings.ts`.
  - Include playback rate, cue window preset, line reveal defaults, blocking options, speak-along settings, and timing tolerances.
  - Progress: moved settings state ownership and persisted-session initialization into `cuemaster/src/ui/hooks/useRehearsalSettings.ts`.
- [x] Extract playback orchestration from `RehearsalScreen.tsx`.
  - Target hook: `cuemaster/src/ui/hooks/useRehearsalPlayback.ts`.
  - Own `AudioQueue`, cue playback, response playback, callout playback, pause/resume/stop, and playback status.
  - Progress: moved `AudioQueue` lifecycle, generic cue/line/callout playback execution, pause/resume/stop, playback source, and status state into `cuemaster/src/ui/hooks/useRehearsalPlayback.ts`.
- [x] Extract tempo timing from `RehearsalScreen.tsx`.
  - Target hook/service: `cuemaster/src/ui/hooks/useTempoTiming.ts`.
  - Own detector lifecycle, feedback tone, timing attempt save/load, and timing status message generation.
  - Progress: moved feedback tone `AudioContext` lifecycle/playback, voice activity detector start/stop, timing attempt save/load, and timing result/status decision logic into `cuemaster/src/ui/hooks/useTempoTiming.ts`.
- [x] Extract bookmark state from `RehearsalScreen.tsx`.
  - Target hook: `cuemaster/src/ui/hooks/useBookmarks.ts`.
  - Own current bookmark, bookmark list, neighboring bookmarks, and toggle behavior.
- [x] Extract outline browser from `RehearsalScreen.tsx`.
  - Target component: `cuemaster/src/ui/components/RehearsalOutline.tsx`.
  - Move outline search/filter helpers to a tested non-React module.
  - Progress: moved outline search, cue display, and current-line helpers to `cuemaster/src/rehearsal/rehearsalPresentation.ts`; extracted `cuemaster/src/ui/components/RehearsalOutline.tsx`.
- [x] Move timing formatting helpers from `RehearsalScreen.tsx` to a tested module.
  - Candidate module: `cuemaster/src/rehearsal/timingPresentation.ts`.
- [ ] Keep `RehearsalScreen.tsx` as a composition layer only after extraction.
  - Progress: moved options rendering to `cuemaster/src/ui/components/RehearsalOptionsPanel.tsx` and bottom controls/status rendering to `cuemaster/src/ui/components/RehearsalBottomBar.tsx`.
  - Progress: moved the central cue/line workspace to `cuemaster/src/ui/components/RehearsalLineWorkspace.tsx`.
  - Progress: moved shared rehearsal header and options page shell to `cuemaster/src/ui/components/RehearsalHeader.tsx` and `cuemaster/src/ui/components/RehearsalOptionsScreen.tsx`.

## Phase 3: Cuemaster Play Page

- [x] Move play page entry building out of `cuemaster/src/ui/screens/PlayPageScreen.tsx`.
  - Target module: `cuemaster/src/rehearsal/playPageEntries.ts`.
  - Preserve current narration, direction, and audio lookup behavior.
- [x] Move play page search helpers to a tested module.
  - Target module: `cuemaster/src/rehearsal/playPageSearch.ts`.
- [x] Extract playback controls and navigation UI from `PlayPageScreen.tsx`.
  - Target components under `cuemaster/src/ui/components/`.
  - Progress: moved navigation calculations to `cuemaster/src/rehearsal/playPageNavigation.ts`; extracted `cuemaster/src/ui/components/PlayPageControls.tsx`.
- [x] Re-run existing PlayPage and rehearsal tests, then add tests for any newly extracted pure modules.

## Phase 4: Shared Browser-App Boundaries

- [x] Review storage singleton usage in both apps.
  - Cuemaster already has `CuemasterStorage`; prefer passing that through app-level composition.
  - LineRecorder should gain a comparable storage interface if UI extraction still depends directly on concrete repositories.
  - Done: added `LineRecorderStorage` and `indexedDbStorage` for LineRecorder.
- [x] Remove or implement unused placeholder abstractions.
  - Candidate files: `cuemaster/src/rehearsal/cuePlayer.ts`, `cuemaster/src/rehearsal/responsePlayer.ts`.
- [x] Decide whether shared browser utilities should live in a future shared package or remain copied per app.
  - Candidate areas: microphone permissions, downloads, IndexedDB test setup, package import errors.
  - Decision: keep browser utilities app-local for now; revisit after the app boundaries settle and duplication becomes clearer.
- [x] Add a lightweight quality command per app if useful.
  - Candidate script: `quality`, running `npm run build && npm test`.

## Phase 5: CSS Ownership

- [ ] Split `cuemaster/src/styles/app.css` by feature after component extraction.
  - Candidate files: `library.css`, `rehearsal.css`, `play-page.css`, `components.css`.
- [ ] Split `linerecorder/src/styles/app.css` by feature after component extraction.
  - Candidate files: `library.css`, `recording-workspace.css`, `microphone.css`, `components.css`.
- [ ] Keep `theme.css` limited to tokens and global theme variables.
- [ ] Avoid visual redesign during CSS movement; verify screenshots manually or with existing e2e flows.

## Completion Criteria

- [x] Both apps build cleanly.
- [x] Both apps pass unit tests.
- [x] Top-level LineRecorder `App.tsx` is mostly composition and app routing.
- [ ] Cuemaster `RehearsalScreen.tsx` no longer owns storage, playback, timing, bookmarks, outline, and rendering all in one file.
- [x] Cuemaster `PlayPageScreen.tsx` delegates entry building, search, and playback controls to smaller modules.
- [ ] New feature work can usually touch a hook/service plus one component instead of editing a thousand-line screen.
