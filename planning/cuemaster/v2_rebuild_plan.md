# Cuemaster V2 Rebuild Plan

Status: active planning document. Cuemaster v2 should be built in `cuemaster-v2/` while Cuemaster v1 remains available as the working app.

## Why V2

Cuemaster v1 proved the important pieces:

- Playbook import and validation can work in a browser app.
- IndexedDB can hold imported Playbooks and audio assets.
- Role-based rehearsal is useful.
- Blocking diagrams can be carried in Playbooks and rendered client-side.
- The app can be deployed as a static hosted app.

It also accumulated too many session concepts:

- separate cue and line playback controls,
- speak-along mode,
- tempo timing,
- auto-advance modes,
- auto-play-line modes,
- Play page and Rehearse page overlap,
- blocking text and blocking diagrams bolted onto existing views.

The main v2 change is not visual. It is a simpler product model:

```text
Playbook -> Role -> Practice Flow -> Flow Runner -> one rehearsal surface
```

Trying to retrofit that into v1 risks preserving the accidental complexity. V2 should reuse stable v1 services where they fit and replace the rehearsal/session center.

## Directory Strategy

Build v2 in:

```text
cuemaster-v2/
```

Rules:

- Keep v1 in `cuemaster/` until v2 can import a real Playbook, rehearse a role, and pass its own tests.
- V2 may copy code from v1, but copied code should be moved into clearer layers as it enters v2.
- Do not import directly from `../cuemaster/src` at runtime. Copy or extract shared code deliberately so v2 can evolve independently.
- Do not change Playbook manifest contracts as part of the v2 app rewrite.
- Do not weaken Playbook strictness.
- Do not add native/Capacitor code to v2 until the PWA plan records a blocker.

## V2 Product Principles

- One primary Play/Pause control.
- One rehearsal surface for actors.
- A separate whole-play listening surface for listening to the full production with autoscrolling script text.
- Practice Flow is the central session setting.
- Continuous playback starts only from a user gesture.
- No microphone permission for non-microphone flows.
- Manual practice remains the safe default.
- Advanced timing features are separate from continuous driving flows.
- Blocking diagrams are optional references, not part of the primary audio loop.
- App code should make impossible states hard to represent.

## Practice Flows

V2 starts with the flow model from [practice_flow_simplification_plan.md](practice_flow_simplification_plan.md):

| Flow | Sequence |
|---|---|
| Manual | cue -> wait |
| Listen | cue -> reference -> next cue |
| Try | cue -> silent response window -> next cue |
| Try + Hear Line | cue -> silent response window -> reference -> next cue |

Terminology:

- **Cue**: audio/text before the actor's current line.
- **Reference**: the actor's recorded response line.
- **Silent response window**: app waits while the actor says the line; no microphone required.
- **Hear line**: explicit one-time reference playback for the current line.

## Reuse From V1

Copy or adapt these early:

- `src/specs/`: Playbook manifest types and validation.
- `src/playbook/`: zip extraction, import, normalization, asset indexing.
- `src/storage/`: IndexedDB repositories, after reviewing naming and transaction boundaries.
- `src/rehearsal/cueWindowPreset.ts`: cue-length presets, with the existing test against `planning/specs/cue_window_presets.json`.
- `src/staging/`: blocking diagram render-state and SVG rendering, after isolating it from v1 UI assumptions.
- `src/platform/`: storage estimate and filesystem abstractions.
- `src/rehearsal/audioPlayer.ts` and `audioQueue.ts`, after checking whether the queue needs changes for iPhone continuous flow.

Avoid copying these as-is:

- `RehearsalScreen.tsx`
- `RehearsalBottomBar.tsx`
- `RehearsalOptionsPanel.tsx`
- v1 session settings hooks,
- tempo auto-advance hooks,
- Play page controls that duplicate Rehearse page behavior.

## Target Architecture

```text
cuemaster-v2/src/
  app/
    App.tsx
    routes.ts
  domain/
    playbook.ts
    role.ts
    line.ts
    session.ts
  playbook/
    import/
    normalize/
  storage/
    repositories/
  audio/
    AudioPlayer.ts
    AudioQueue.ts
  practice/
    practiceFlow.ts
    practiceFlowRunner.ts
    practiceTiming.ts
  staging/
    renderState/
    svg/
  ui/
    screens/
    components/
    hooks/
  platform/
```

Dependency direction:

```text
ui -> practice -> domain
ui -> playbook/storage/audio adapters
practice -> audio/domain
playbook -> specs/domain
storage -> domain
```

Do not let React components own flow sequencing. Components send commands to a flow runner and render state.

## Initial Scaffold

The initial `cuemaster-v2/` scaffold should contain:

- a separate package named `cuemaster-v2`,
- a Vite/React entry point,
- a placeholder app shell,
- pure `practiceFlow` and `practiceFlowRunner` modules,
- a standalone functional wireframe under `mockups/`,
- unit-test targets for the flow runner,
- dev server port `5174` so v1 can still use `5173`.

The scaffold does not need to import Playbooks yet.

## Implementation Checklist

### Phase 0: Workspace

- [x] Create `cuemaster-v2/`.
- [x] Add independent package metadata and Vite config.
- [x] Add first vertical-slice React app.
- [x] Add initial pure practice-flow modules.
- [x] Add standalone functional wireframe for UX review.
- [ ] Run `npm install` in `cuemaster-v2/` when dependency installation is acceptable.
- [x] Verify `npm --prefix cuemaster-v2 run build`.
- [x] Verify `npm --prefix cuemaster-v2 test`.

### Phase 1: Practice Core

- [x] Finalize `PracticeFlow` names and labels.
- [x] Implement deterministic step building for all flows.
- [x] Implement silent response window duration calculation.
- [x] Add cancellation semantics for flow interruption.
- [x] Add unit tests for Manual, Listen, Try, and Try + Hear Line.
- [x] Add unit tests for line pace and response padding.
- [ ] Add tests for end-of-role behavior.

### Phase 2: Audio Runner

- [ ] Port or rewrite `AudioPlayer`.
- [ ] Port or rewrite `AudioQueue`.
- [x] Add a shared playback runner that can play cue/reference steps and wait silent windows.
- [x] Ensure the first audible playback starts from a user gesture.
- [ ] Catch `play()` promise failures and surface a resumable state.
- [ ] Add manual iPhone Safari test notes for continuous playback.

### Phase 3: Playbook Import

- [x] Copy/adapt manifest types.
- [ ] Copy/adapt package format version checks.
- [x] Copy/adapt zip extraction for main-thread MVP.
- [x] Copy/adapt normalization into v2 domain types.
- [x] Copy/adapt audio resolution.
- [x] Add tests using a Fairies-derived Playbook fixture.
- [x] Confirm v2 can import a current real Playbook through the browser import path.

### Phase 4: Storage

- [ ] Copy/adapt IndexedDB schema with a v2 database name.
- [ ] Store imported Playbooks and audio assets.
- [ ] Store selected role and session state.
- [ ] Store bookmarks.
- [ ] Add migration policy from v1 only if needed; do not block v2 on v1 local data migration.
- [ ] Add clear "remove Playbook" behavior.

### Phase 5: Rehearsal UI

- [x] Build Library screen.
- [x] Build Playbook import flow.
- [x] Build Role Select.
- [x] Build one Rehearsal screen with one primary Play/Pause button.
- [x] Add compact icon controls for Previous, Repeat Cue, Play/Pause, Hear Line, and Next.
- [x] Keep Practice Flow, show-line, show-blocking, and other settings out of the rehearsal footer.
- [x] Build a Navigation drawer for role line and whole-play jumps.
- [x] Build a Whole Play listening surface for listening to the full production.
- [ ] Make Whole Play auto-scroll the script as playback advances.
- [x] Make Whole Play lines clickable for jumping forward/back.
- [x] Make Whole Play inline blocking notes clickable when blocking is enabled.
- [x] Add Practice Flow selector.
- [x] Add Line Pace controls.
- [x] Add Display and Content controls.
- [ ] Keep Advanced collapsed by default.

### Phase 6: Blocking

- [x] Copy/adapt blocking note display.
- [ ] Copy/adapt blocking diagram JSON/SVG renderer.
- [x] Add a blocking button to the single rehearsal surface.
- [ ] Keep diagrams on demand and never auto-open during playback.
- [ ] Verify v2 renders the same diagram state as v1 for a known Playbook.

### Phase 7: PWA

- [ ] Add manifest and icons.
- [ ] Add service worker/app-shell caching.
- [ ] Add offline launch validation.
- [ ] Add app update flow.
- [ ] Add install affordance where supported.
- [ ] Test hosted nested-path behavior.

### Phase 8: Cutover

- [ ] Build a real Playbook in Stager.
- [ ] Import and rehearse it in v1 and v2.
- [ ] Compare blocking display, cue selection, and audio behavior.
- [ ] Confirm v2 passes unit and Playwright smoke tests.
- [ ] Update deployment script to optionally build/deploy v2.
- [ ] Decide whether hosted Cuemaster should point to v1 or v2.
- [ ] Archive v1 implementation notes after v2 becomes primary.

## V2 Acceptance Criteria

- [x] Actor can import a Playbook.
- [x] Actor can select a role.
- [x] Actor can rehearse with Manual flow.
- [x] Actor can use Listen flow in one continuous playback session.
- [x] Actor can use Try flow with silent response windows.
- [x] Actor can use Try + Hear Line flow.
- [x] There is only one primary Play/Pause control.
- [x] There is no separate line-play transport.
- [x] Hear Line plays the current reference line once.
- [ ] Cue length and line pace work.
- [ ] Blocking text and diagrams are available on demand.
- [x] No microphone permission is requested for non-microphone flows.
- [x] V2 can be hosted as a static app.

## Open Decisions

- Should v2 eventually replace `cuemaster/`, or should the directory remain `cuemaster-v2/` through the first production?
- Should v2 support importing existing v1 IndexedDB data, or is reimporting Playbooks acceptable?
- Decision: Whole Play remains a separate listening/script surface from role rehearsal.
- Decision: tempo timing is hidden on iOS until the microphone/audio-session issue is proven safe.
