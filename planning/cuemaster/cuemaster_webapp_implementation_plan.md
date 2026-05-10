# Cuemaster Web App Implementation Plan

## Scope

This plan covers the **Phase 1 browser web app only**.

Capacitor, native mobile packaging, background audio, lock-screen controls, steering-wheel controls, and wake-word voice commands are **not implemented in this phase**. However, the web app must be built in a way that keeps a later Capacitor implementation straightforward.

The goal of Phase 1 is to produce a useful browser-based rehearsal app that can:

- import a Playbook zip,
- store it locally,
- let the actor select a role,
- play cues,
- let the actor advance/back/repeat/hear reference lines,
- support variable-speed playback for the actor's own lines,
- support speak-along practice,
- measure hesitation and delivery pace using microphone-based voice activity detection,
- keep enough architecture clean that Capacitor can wrap it later.

---

## Guiding Principles

- **Web app first.** The browser version should be useful on its own.
- **Capacitor-compatible architecture.** Keep browser-only APIs behind adapters.
- **No GPL-family dependencies.** Avoid GPL, LGPL, AGPL, SSPL, BUSL, unclear-license packages, and unlicensed packages.
- **Domain logic outside React.** React renders the UI; it does not own the rehearsal engine.
- **Audio is simple unless proven otherwise.** Use `HTMLAudioElement` for playback.
- **Cues stay at performance speed.** Cue audio always plays at `1.0x`.
- **Only actor response lines are speed-variable.**
- **Tempo timing is not speech recognition.** It uses voice activity detection only.
- **Do not overbuild.** Implement the core rehearsal loop first; defer reporting, drill modes, and polish until the app is genuinely usable.

---

## Approved Web Stack

| Layer | Choice |
|---|---|
| UI framework | React |
| Build tool | Vite |
| Language | TypeScript |
| State management | React state first; add Zustand only when session/library state becomes awkward to pass explicitly |
| Styling | Plain CSS or CSS modules |
| Audio playback | `HTMLAudioElement` behind an `AudioPlayer` abstraction |
| Variable speed | `HTMLMediaElement.playbackRate` |
| Zip extraction | `jszip` initially; revisit `fflate` only if import performance becomes a problem |
| Zip execution | Main thread for tiny fixtures; move to Web Worker before large realistic imports |
| Browser storage | IndexedDB via Dexie |
| File import | Browser File API |
| Manifest validation | Zod |
| Unit testing | Vitest |
| Browser flow testing | Playwright |
| Microphone timing | Browser microphone APIs + app-owned voice activity detection |

---

## Dependency Rules

Before adding any runtime dependency:

- [ ] Confirm license is MIT, BSD, ISC, Apache-2.0, or otherwise explicitly approved.
- [ ] Confirm the package has a clear license file.
- [ ] Check whether the package pulls in transitive dependencies with incompatible licenses.
- [ ] Avoid abandoned packages for critical features.
- [ ] Prefer small app-owned code for simple behavior.

Explicitly prohibited in shipped app code:

- [ ] GPL
- [ ] LGPL
- [ ] AGPL
- [ ] SSPL
- [ ] BUSL
- [ ] Commons Clause
- [ ] unclear license
- [ ] no license

Development-only tools should also be permissive unless there is a clear reason otherwise.

---

## Current Source Layout

The current scaffold lives under `cuemaster/` and uses this layout:

```text
cuemaster/
  README.md
  package.json
  vite.config.ts
  playwright.config.ts

  src/
    app/
      App.tsx
      providers.tsx
      routes.tsx

    domain/
      context.ts
      cue.ts
      line.ts
      playbook.ts
      role.ts
      session.ts

    playbook/
      extractPlaybookZip.ts
      importPlaybook.ts
      normalizePlaybook.ts
      resolveAudioAsset.ts

    storage/
      audioAssetRepository.ts
      db.ts
      playbookRepository.ts
      sessionRepository.ts

    specs/
      playbookManifest.ts
      validatePlaybookManifest.ts

    rehearsal/
      cuePlayer.ts
      lineNavigator.ts
      rehearsalEngine.ts
      responsePlayer.ts

    ui/
      components/
      screens/

    platform/
      audio.ts
      filesystem.ts

    styles/
      app.css
      theme.css

  tests/
    unit/
    fixtures/
      minimal-playbook/
      androcles-playbook/

  e2e/
```

The `platform/` folder exists even in the web version so later Capacitor work can replace browser-specific behavior without rewriting the app. Do not introduce a separate `audio/`, `state/`, or `tempo/` top-level folder until the relevant milestone creates enough code to justify it.

---

## Domain Model Targets

### Playbook

A Playbook is imported from a `.zip` and normalized into an app-owned internal structure.

Minimum internal model:

```ts
type Playbook = {
  id: string;
  title: string;
  authors: string[];
  source?: string;
  schemaVersion: number;
  context: ContextBlock[];
  roles: Role[];
};

type ContextBlock = {
  id: string;
  partId: number | null;
  blockId: string;
  kind: "heading" | "description" | "direction";
  speaker: "_NARRATOR";
  text: string;
  audioPath: string;
  durationMs: number;
};

type Role = {
  id: string;
  displayName: string;
  reader: string;
  parts: Array<number | null>;
  lines: RehearsalLine[];
};

type RehearsalLine = {
  id: string;
  partId: number | null;
  blockId: string;
  role: string;
  speaker: string;
  cue: CuePayload;
  responseText: string;
  responseSegments: ResponseSegment[];
  previousRoles: string[];
  timing?: LineTiming;
};

type CuePayload = {
  speaker: string;
  text: string;
  audioPath: string;
  durationMs: number;
};

type ResponseSegment = {
  id: string;
  owners: string[];
  text: string;
  audioPath: string;
  durationMs: number;
  simultaneous: boolean;
};

type LineTiming = {
  targetHesitationMs?: number;
};
```

### Session

```ts
type SessionConfig = {
  selectedRoleId: string;
  cueDepth: number;
  includeDirections: boolean;
  startLineId?: string;

  responsePlaybackSpeed: number; // 0.4 to 1.3
  speakAlongEnabled: boolean;
  tempoTimingEnabled: boolean;
  defaultTargetHesitationMs: number; // default 500
};

type SessionState = {
  playbookId: string;
  currentLineId: string;
  playbackMode:
    | "idle"
    | "cue_playing"
    | "waiting"
    | "reference_playing"
    | "speak_along_playing"
    | "timing"
    | "paused";

  lastTimingAttempt?: TimingAttempt;
};
```

### Tempo Attempt

```ts
type TimingAttempt = {
  lineId: string;
  attemptedAt: string;

  cueEndedAtMs: number;
  firstSpeechAtMs: number;
  finalSpeechAtMs: number;

  hesitationMs: number;
  targetHesitationMs: number;

  deliveryMs: number;
  targetDeliveryMs: number;

  paceRatio: number;      // targetDeliveryMs / deliveryMs
  durationRatio: number;  // deliveryMs / targetDeliveryMs

  result: {
    hesitation: "sharp" | "close" | "late";
    delivery: "fast" | "close" | "slow";
  };

  detectionMode: "voice_activity";
};
```

---

## Milestone 0 — Project Skeleton

### Goal

Create a working React/Vite/TypeScript app with the planned folder structure, test setup, and dependency policy.

### Checklist

- [x] Create Vite React TypeScript project under `cuemaster/`.
- [x] Defer Zustand until app state requires it.
- [x] Add Vitest.
- [x] Add Playwright.
- [x] Add `jszip` for initial zip extraction.
- [x] Add Dexie IndexedDB wrapper.
- [x] Add Zod manifest validation.
- [x] Add CSS baseline.
- [x] Add route/screen skeletons.
- [x] Add `platform/` abstraction folder.
- [ ] Add dependency license audit script.
- [ ] Add `THIRD_PARTY_NOTICES.md` placeholder.
- [x] Add `README.md` with web-app-only development instructions.
- [x] Add initial sample manifest fixture from a Stager-generated public-domain Playbook.
- [x] Add a fake in-memory Playbook fixture in unit tests for UI/domain development before zip import works.

### Acceptance Criteria

- [x] `npm install` succeeds.
- [ ] `npm run dev` starts the web app.
- [x] `npm run build` succeeds.
- [x] `npm test` runs Vitest.
- [ ] `npm run e2e` runs Playwright smoke test.
- [x] Home screen renders in the build.
- [ ] No runtime dependency has an incompatible license.

### Remaining Milestone 0 Work

- Add a license audit script and `THIRD_PARTY_NOTICES.md`.
- Add a small committed Playbook manifest fixture generated from public-domain Stager data.
- Run `npm run dev` manually and confirm the browser app starts.
- Run `npm run e2e`; install Playwright browsers first if needed.

After those are done, Milestone 0 is complete.

---

## Immediate Next Implementation Slice

Start with Milestone 1, not zip import UI.

The next code changes should:

- strengthen `src/specs/validatePlaybookManifest.ts` to validate roles, lines, cues, responses, and context fully;
- add public-domain manifest fixtures under `tests/fixtures/minimal-playbook/`;
- add domain/session engine tests that select a role and walk lines forward/backward;
- keep this code independent of React and browser APIs.

This produces a reliable app model before storage, zip import, or UI screens depend on it.

---

## Milestone 1 — Manifest and Rehearsal Domain Engine

### Goal

Implement the framework-independent logic for parsing a manifest, selecting a role, deriving the line sequence, and moving through the rehearsal session.

No real audio or zip import is required yet.

### Checklist

#### Manifest parsing

- [x] Define TypeScript types for the expected Playbook manifest.
- [x] Define app-owned normalized types.
- [x] Implement initial manifest validation.
- [x] Reject manifests with missing play ID/title.
- [x] Reject roles without line arrays.
- [x] Reject lines with missing IDs.
- [x] Reject required cue or response audio fields that are malformed or missing in the manifest.
- [x] Validate and preserve top-level narrator `context`.
- [x] Preserve optional `timing.target_hesitation_ms`.
- [x] Add a fixture generated from `build/androcles/app/manifest.json` or a smaller Stager fixture.

#### Role filtering

- [x] Exclude `_NARRATOR`, `_CALLER`, and `_ANNOUNCER` from normal actor role selection by relying on Stager `roles`.
- [x] Keep `_NARRATOR` context available internally through the manifest `context` array.
- [x] Add tests for role filtering.

#### Session engine

- [x] Select role.
- [x] Start from first line.
- [x] Start from chosen line.
- [x] Advance to next line.
- [x] Go back to previous line.
- [x] Repeat current line/cue.
- [x] Detect beginning/end of role sequence.
- [x] Support `cueDepth` in derived cue list.
- [x] Support `includeDirections` flag where manifest data allows it.
- [x] Expose current line, cue payload, response payload, and position information.

#### Tests

- [x] Test one-role manifest.
- [x] Test multi-role manifest.
- [x] Test special-role filtering.
- [x] Test next/back behavior.
- [x] Test cue-depth behavior.
- [x] Test line-specific target hesitation fallback behavior.

### Acceptance Criteria

- [x] A unit test can load a sample manifest and derive a rehearsal sequence for a selected role.
- [x] A unit test can walk forward and backward through the selected role's lines.
- [x] The domain engine has no React dependency.
- [x] The domain engine has no browser API dependency.

---

## Milestone 2 — Playbook Import: Load and Validate a Zip

### Goal

Allow the user to import a `.zip` Playbook in the browser, extract the manifest, validate it, and display it in the library.

This is the first major useful milestone.

### Checklist

#### File picker

- [x] Add **Import Playbook** button.
- [x] Accept `.zip` files.
- [x] Show selected filename.
- [x] Show import progress state.

#### Zip handling

- [x] Implement initial zip extraction with `jszip`.
- [ ] Move extraction work into a Web Worker before realistic large Playbook imports.
- [x] Read `manifest.json` from the expected location.
- [x] Validate manifest.
- [x] Build asset index from zip entries.
- [x] Detect missing required audio assets.
- [x] Report friendly errors for invalid zips.
- [x] Report friendly errors for invalid manifests.
- [x] Avoid loading all audio into active playback memory.

#### Library integration

- [x] Store imported Playbook metadata.
- [x] Show Playbook in Library screen.
- [x] Show play title.
- [x] Show available actor roles.
- [x] Allow delete/remove from local library.

#### Tests

- [x] Unit-test manifest validation.
- [x] Unit-test asset lookup.
- [ ] Add Playwright test importing a small fixture Playbook.
- [x] Add error-path test for invalid zip.
- [x] Add error-path test for missing manifest.
- [x] Add error-path test for missing required audio.

### Acceptance Criteria

- [x] User can import a valid Playbook zip.
- [x] Imported Playbook appears in the library.
- [x] User can select the Playbook and see roles.
- [x] Invalid Playbooks produce useful error messages.
- [ ] Large import work does not freeze the UI.

---

## Milestone 3 — Browser Storage

### Goal

Persist imported Playbooks and session metadata locally in the browser.

### Checklist

#### IndexedDB storage

- [ ] Define storage interface independent of IndexedDB.
- [ ] Implement `indexedDbStorage`.
- [ ] Store Playbook manifest.
- [ ] Store asset blobs or extractable asset records.
- [ ] Store import metadata.
- [ ] Store selected role per Playbook.
- [ ] Store session position per Playbook/role.
- [ ] Store session config per Playbook/role.
- [ ] Store bookmarks.
- [ ] Store timing attempts.

#### Startup behavior

- [ ] Load Playbook library on app launch.
- [ ] Restore selected role when available.
- [ ] Offer resume when saved position exists.
- [ ] Handle missing/corrupt local storage gracefully.

#### Tests

- [ ] Unit-test storage interface with memory implementation.
- [ ] Integration-test IndexedDB implementation where practical.
- [ ] Playwright test: import Playbook, reload page, Playbook remains in library.
- [ ] Playwright test: save session position, reload page, resume works.

### Acceptance Criteria

- [ ] Imported Playbooks survive page reload.
- [ ] Selected role survives page reload.
- [ ] Current line position survives page reload.
- [ ] Deleting a Playbook removes its manifest, assets, session state, bookmarks, and timing history.
- [ ] Storage code is isolated behind an interface that can later be replaced by Capacitor filesystem/preferences implementations.

---

## Milestone 4 — Role Selection and Session Setup UI

### Goal

Allow the actor to choose a role and configure a rehearsal session.

### Checklist

#### Role select

- [ ] Show actor roles.
- [ ] Hide special roles by default.
- [ ] Show role display names.
- [ ] Save selected role.
- [ ] Allow role switching.

#### Session setup

- [ ] Start from beginning.
- [ ] Resume from saved position.
- [ ] Choose scene/section if manifest structure supports it.
- [ ] Set cue depth.
- [ ] Toggle stage directions.
- [ ] Set response playback speed.
- [ ] Toggle speak-along mode.
- [ ] Toggle tempo timing.
- [ ] Show default target hesitation setting, initially fixed at 500ms or hidden under advanced settings.

#### UI constraints

- [ ] Large tap targets.
- [ ] Clear session start button.
- [ ] No dense settings wall.
- [ ] Settings should be saved per Playbook/role.

### Acceptance Criteria

- [ ] User can import a Playbook, choose a role, configure a session, and enter the Session screen.
- [ ] Selected settings persist across reload.
- [ ] The UI does not expose special roles as normal actor choices.

---

## Milestone 5 — Audio Playback Foundation

### Goal

Implement reliable sequential audio playback in the browser.

This milestone does not yet require the full rehearsal UI.

### Checklist

#### Audio abstraction

- [ ] Create `AudioPlayer` class/wrapper around `HTMLAudioElement`.
- [ ] Support loading an audio asset by app asset ID/path.
- [ ] Support play.
- [ ] Support pause.
- [ ] Support stop.
- [ ] Support ended event.
- [ ] Support error event.
- [ ] Support `playbackRate`.
- [ ] Support pitch preservation where browser exposes it.
- [ ] Expose current playback state.
- [ ] Avoid React dependency.

#### Audio queue

- [ ] Create `AudioQueue`.
- [ ] Play one cue asset.
- [ ] Play multiple cue assets sequentially.
- [ ] Cancel queue.
- [ ] Report queue completion.
- [ ] Report queue failure.

#### Asset resolution

- [ ] Resolve imported Playbook audio assets to playable object URLs.
- [ ] Revoke object URLs when no longer needed.
- [ ] Avoid loading all Playbook audio into memory at once.
- [ ] Handle missing/failed audio asset.

#### Tests

- [ ] Unit-test queue sequencing with mock player.
- [ ] Unit-test cancellation.
- [ ] Unit-test playback speed assignment.
- [ ] Browser/manual test with real audio fixture.

### Acceptance Criteria

- [ ] App can play a cue audio file from an imported Playbook.
- [ ] App can play multiple cue files sequentially.
- [ ] App can play actor response audio at selected speed.
- [ ] Cue audio always plays at `1.0x`.
- [ ] Response audio can play from `0.4x` to `1.3x` in `0.1x` increments.
- [ ] Audio playback logic is isolated enough that a Capacitor-native audio implementation can replace it later if needed.

---

## Milestone 6 — First Useful Rehearsal Loop: Play Cues and Advance

### Goal

Deliver the first truly usable rehearsal loop:

```text
Play cue → wait → actor speaks → next/repeat/back/hear line
```

This is the second major useful milestone.

### Checklist

#### Session screen

- [ ] Show play title.
- [ ] Show selected role.
- [ ] Show current position.
- [ ] Show cue text.
- [ ] Hide actor line by default.
- [ ] Add reveal/hide actor line.
- [ ] Add large controls:
  - [ ] Back
  - [ ] Repeat Cue
  - [ ] Hear My Line
  - [ ] Skip/Next
  - [ ] Pause/Resume

#### Playback behavior

- [ ] On session start, play cue for current line.
- [ ] After cue playback, enter waiting state.
- [ ] Repeat cue replays cue without advancing.
- [ ] Hear My Line plays actor response audio without advancing.
- [ ] Next advances to next actor line and plays next cue.
- [ ] Back moves to previous actor line and plays cue.
- [ ] Pause stops playback and saves state.
- [ ] Resume restores line position and can replay current cue.

#### State persistence

- [ ] Save current line after navigation.
- [ ] Save playback mode safely as idle/waiting on reload; do not resume mid-audio.
- [ ] Save bookmarks.
- [ ] Save reveal-line preference only if desired.

#### Tests

- [ ] Unit-test session transitions.
- [ ] Playwright test: start session, click Next, position changes.
- [ ] Playwright test: Repeat Cue does not advance.
- [ ] Playwright test: Hear My Line does not advance.
- [ ] Playwright test: Back returns to previous line.
- [ ] Playwright test: reload offers resume.

### Acceptance Criteria

- [ ] User can rehearse through a role using on-screen controls.
- [ ] User can repeat cue.
- [ ] User can hear their line.
- [ ] User can advance and go back.
- [ ] User can reload and resume.
- [ ] This milestone is demoable as a basic Cuemaster web app.

---

## Milestone 7 — Variable-Speed Role-Line Playback

### Goal

Support speed-adjusted playback for the actor's own reference lines.

### Checklist

- [ ] Add playback speed control.
- [ ] Support speeds from `0.4x` to `1.3x`.
- [ ] Use `0.1x` increments.
- [ ] Default to `1.0x`.
- [ ] Persist selected speed per Playbook/role.
- [ ] Apply speed only to selected actor response audio.
- [ ] Force cue audio to `1.0x`.
- [ ] Enable pitch preservation where supported.
- [ ] Show current speed clearly in Session screen.
- [ ] Add quick controls:
  - [ ] Slower
  - [ ] Faster
  - [ ] Normal
- [ ] Clamp invalid values.

### Acceptance Criteria

- [ ] Actor can hear their own line at 0.4x through 1.3x.
- [ ] Cue playback is never slowed by this setting.
- [ ] The selected speed persists after reload.
- [ ] Tests verify cue speed stays `1.0x`.

---

## Milestone 8 — Speak-Along Mode

### Goal

Let the actor speak along with the reference line at the selected response playback speed.

### Checklist

- [ ] Add speak-along toggle.
- [ ] Define speak-along behavior:
  - [ ] cue plays at `1.0x`,
  - [ ] response audio plays at selected speed,
  - [ ] actor speaks along,
  - [ ] app returns to waiting state or offers next/retry.
- [ ] Ensure speak-along mode does not enable microphone timing at the same time.
- [ ] Make conflict clear if tempo timing is also enabled.
- [ ] Add Session screen button: **Speak Along** or reuse **Hear My Line** with mode-aware label.
- [ ] Persist speak-along preference.
- [ ] Add tests for cue speed and response speed.

### Acceptance Criteria

- [ ] User can play cue then speak along with their line at selected speed.
- [ ] Speak-along does not trigger timing.
- [ ] Speak-along is useful before automatic timing exists.

---

## Milestone 9 — Microphone Permission and Voice Activity Detection Spike

### Goal

Prove that browser-based microphone access and simple voice activity detection can support tempo timing.

This is a technical spike, but it should leave usable code if successful.

### Checklist

#### Permission

- [ ] Add explicit **Enable Tempo Timing** flow.
- [ ] Explain microphone use:
  - [ ] no recording,
  - [ ] no transcription,
  - [ ] no upload,
  - [ ] voice activity detection only.
- [ ] Request microphone permission.
- [ ] Handle denied permission.
- [ ] Handle missing microphone.
- [ ] Handle browser security restrictions.

#### Voice activity detector

- [ ] Capture microphone stream.
- [ ] Analyze volume/energy over time.
- [ ] Distinguish speech-like activity from silence/noise well enough for a first version.
- [ ] Add calibration or ambient noise baseline if needed.
- [ ] Detect first speech after cue.
- [ ] Detect end of attempt after long silence.
- [ ] Ignore short internal pauses.
- [ ] Subtract final silence from delivery time.
- [ ] Stop and release microphone when timing is disabled.

#### Timing parameters

Initial internal defaults:

- [ ] Default target hesitation: `500ms`.
- [ ] Internal pause grace: approximately `750ms`.
- [ ] End-of-line silence threshold: approximately `1500ms`.
- [ ] Make thresholds constants in one place.
- [ ] Keep thresholds adjustable in code for testing.

#### Tests/manual checks

- [ ] Manual test in quiet room.
- [ ] Manual test with laptop fan/background noise.
- [ ] Manual test with deliberate short internal pause.
- [ ] Manual test with long ending pause.
- [ ] Manual test permission denial.
- [ ] Manual test repeated attempts without leaking mic streams.

### Acceptance Criteria

- [ ] Browser asks for microphone permission only when tempo timing is enabled.
- [ ] App can detect first speech after cue.
- [ ] App can detect end of delivery after long silence.
- [ ] App does not save audio.
- [ ] App does not transcribe audio.
- [ ] App releases microphone when timing is off.
- [ ] Result is good enough to proceed to productized tempo timing, or the spike documents blockers.

---

## Milestone 10 — Automatic Hesitation and Delivery Pace Timing

### Goal

Add tempo timing to the rehearsal loop.

This is the third major useful milestone.

### Checklist

#### Timing flow

- [ ] Cue plays at `1.0x`.
- [ ] Microphone opens immediately after cue ends.
- [ ] Hesitation timer starts immediately when cue ends.
- [ ] First detected speech stops hesitation timer.
- [ ] First detected speech starts delivery timer.
- [ ] Short pauses are treated as part of delivery.
- [ ] Long silence ends the attempt.
- [ ] Final silence is subtracted from delivery time.
- [ ] Tempo feedback is shown.
- [ ] Actor can then:
  - [ ] hear line,
  - [ ] try again,
  - [ ] repeat cue,
  - [ ] next,
  - [ ] back.

#### Target values

- [ ] Use line-specific `timing.target_hesitation_ms` when present.
- [ ] Fall back to default target hesitation, initially `500ms`.
- [ ] Use Playbook response audio duration as target delivery duration.
- [ ] If response has multiple segments, sum their durations.
- [ ] Handle missing duration gracefully.

#### Feedback

- [ ] Show hesitation:
  - [ ] measured pickup time,
  - [ ] target pickup time,
  - [ ] sharp/close/late label.
- [ ] Show delivery:
  - [ ] measured delivery time,
  - [ ] Playbook target duration,
  - [ ] pace relative to target,
  - [ ] fast/close/slow label.
- [ ] Avoid acting-quality language.
- [ ] Keep feedback readable and nonjudgmental.

#### Storage

- [ ] Store timing attempts locally.
- [ ] Store hesitation and delivery separately.
- [ ] Store target values used at the time.
- [ ] Store detection mode.
- [ ] Limit history size if necessary.

#### Tests

- [ ] Unit-test tempo calculations.
- [ ] Unit-test hesitation target fallback.
- [ ] Unit-test multi-segment duration sum.
- [ ] Unit-test result labels.
- [ ] Mock VAD tests for timing state transitions.
- [ ] Playwright/manual test for real microphone timing.

### Acceptance Criteria

- [ ] Actor can complete a timed attempt after hearing a cue.
- [ ] App reports hesitation and delivery pace separately.
- [ ] App uses line-specific target hesitation when available.
- [ ] App stores local timing history.
- [ ] App remains useful if timing is disabled.

---

## Milestone 11 — Timing History and Basic Review

### Goal

Let the actor see which lines need work, without building a full analytics product.

### Checklist

- [ ] Add simple timing history per line.
- [ ] Show last attempt on Session screen.
- [ ] Show recent attempts for current line.
- [ ] Add basic Tempo Review screen.
- [ ] List lines with late pickup.
- [ ] List lines with slow delivery.
- [ ] List lines with rushed delivery.
- [ ] List bookmarked lines.
- [ ] Allow jumping from review list to line.
- [ ] Keep calculations local.
- [ ] Avoid charts unless clearly useful.

### Acceptance Criteria

- [ ] Actor can identify late-pickup lines.
- [ ] Actor can identify slow-delivery lines.
- [ ] Actor can identify rushed-delivery lines.
- [ ] Actor can jump directly to a problem line.
- [ ] Review feature is useful but not overbuilt.

---

## Milestone 12 — Script Browser, Bookmarks, and Navigation Polish

### Goal

Improve navigation once the core loop works.

### Checklist

- [ ] Add script browser modal/screen.
- [ ] Show scenes/parts where manifest structure supports it.
- [ ] Show current position.
- [ ] Show bookmarked lines.
- [ ] Allow jump to scene.
- [ ] Allow jump to bookmarked line.
- [ ] Add bookmark toggle on Session screen.
- [ ] Add keyboard shortcuts for desk rehearsal:
  - [ ] Space: play/pause or repeat depending state.
  - [ ] Right arrow: next.
  - [ ] Left arrow: back.
  - [ ] R: repeat cue.
  - [ ] L: hear line.
- [ ] Ensure shortcuts do not interfere with text inputs.
- [ ] Add accessible labels for all controls.

### Acceptance Criteria

- [ ] Actor can jump around without walking line by line.
- [ ] Actor can bookmark and revisit difficult lines.
- [ ] Desk rehearsal is efficient with keyboard controls.

---

## Milestone 13 — Browser App Hardening

### Goal

Make the web app reliable enough to share with real users for early testing.

### Checklist

#### Error handling

- [ ] Handle bad zip.
- [ ] Handle missing audio.
- [ ] Handle unsupported audio format.
- [ ] Handle browser autoplay restrictions.
- [ ] Handle storage quota errors.
- [ ] Handle microphone permission denial.
- [ ] Handle failed audio playback.
- [ ] Handle stale object URLs.
- [ ] Handle corrupted IndexedDB records.

#### Accessibility

- [ ] Large tap targets.
- [ ] Keyboard navigability.
- [ ] Screen reader labels.
- [ ] Visible focus states.
- [ ] Sufficient contrast.
- [ ] Reduced-motion friendly UI.
- [ ] No essential information conveyed only by color.

#### Performance

- [ ] Import progress remains responsive.
- [ ] Large Playbook import does not freeze UI.
- [ ] App does not keep unnecessary audio blobs in memory.
- [ ] Revoke unused object URLs.
- [ ] Timing detector does not run when disabled.
- [ ] Session screen remains responsive during playback.

#### Privacy

- [ ] Microphone explanation appears before permission request.
- [ ] No audio recording occurs.
- [ ] No analytics by default.
- [ ] No network dependency after import.

#### Testing

- [ ] Playwright happy path.
- [ ] Playwright reload/resume path.
- [ ] Playwright invalid import path.
- [ ] Unit tests for domain/session/tempo.
- [ ] Manual test with at least one realistic Playbook.

### Acceptance Criteria

- [ ] App is good enough for a small group of real actors/testers.
- [ ] Known limitations are documented.
- [ ] No major architecture refactor is obviously required before Capacitor work.

---

## Milestone 14 — Capacitor Readiness Review

### Goal

Before starting native mobile work, confirm the web app is structured so Capacitor can wrap it without major rework.

This milestone does **not** implement Capacitor. It prepares for it.

### Checklist

#### Architecture review

- [ ] Browser file access is isolated behind a platform adapter.
- [ ] IndexedDB storage is isolated behind a storage interface.
- [ ] Audio playback is isolated behind `AudioPlayer`.
- [ ] Microphone access is isolated behind a timing/voice input abstraction.
- [ ] No React component directly calls low-level browser APIs except through adapters.
- [ ] No web-only assumption is hardcoded into domain logic.
- [ ] No dependency blocks mobile packaging.

#### Licensing review

- [ ] Runtime dependency list reviewed.
- [ ] Transitive licenses checked.
- [ ] `THIRD_PARTY_NOTICES.md` generated or updated.
- [ ] No GPL-family dependency present.
- [ ] No unclear-license dependency present.

#### Mobile feature planning

- [ ] Document what must change for Capacitor filesystem.
- [ ] Document what must change for Capacitor preferences.
- [ ] Document what must change for native/background audio.
- [ ] Document what must change for microphone permission.
- [ ] Document what must change for hardware controls.
- [ ] Document what can remain unchanged.

### Acceptance Criteria

- [ ] A developer can identify the adapters that will be replaced or extended in the Capacitor phase.
- [ ] No known v1 web decision prevents mobile implementation.
- [ ] The next step can be a focused Capacitor technical spike rather than a rewrite.

---

## Milestone 15 — Wake-Word / Command Stack Decision Point

### Goal

Choose the likely Phase 2 voice-command direction without implementing it in the web app.

This milestone belongs at the end of web-app Phase 1 because voice commands should not shape the core app too early. The web app should expose a command interface that voice, hardware, keyboard, and buttons can all call later.

### Checklist

#### Command abstraction

- [ ] Define app commands independent of input method:
  - [ ] next,
  - [ ] back,
  - [ ] repeat cue,
  - [ ] hear line,
  - [ ] pause,
  - [ ] resume,
  - [ ] bookmark,
  - [ ] slower,
  - [ ] faster,
  - [ ] normal speed,
  - [ ] start timing / retry timing if needed.
- [ ] Ensure buttons call command functions rather than embedding behavior directly.
- [ ] Ensure keyboard shortcuts call the same command functions.
- [ ] Leave voice commands as a later input layer.

#### Research

- [ ] Review Vosk runtime licensing.
- [ ] Review candidate Vosk model licensing.
- [ ] Investigate native Vosk through a Capacitor plugin bridge.
- [ ] Investigate Vosk WASM feasibility.
- [ ] Investigate whether wake-word-only detection can be constrained to a tiny grammar.
- [ ] Investigate mobile CPU/battery implications.
- [ ] Confirm no GPL or unclear-license dependency is required.
- [ ] Document recommended direction.

#### Output

- [ ] Write a short decision note:
  - [ ] recommended wake-word stack,
  - [ ] rejected alternatives,
  - [ ] licensing status,
  - [ ] technical risks,
  - [ ] proposed Capacitor spike.

### Acceptance Criteria

- [ ] The app has an input-command abstraction ready for voice commands later.
- [ ] There is a documented, license-safe candidate stack for Phase 2 voice commands.
- [ ] No wake-word code is required in the Phase 1 browser release.

---

## Later Planning — Keep Hand-Wavy for Now

The following are intentionally not planned in detail until the core web app is proven useful:

### Advanced drill modes

- Late-pickup-only drill.
- Slow-delivery drill.
- Rushed-delivery drill.
- Inconsistent-line drill.
- Adaptive speed ramps.

### Rich reporting

- Scene-level tempo summaries.
- Progress charts.
- Exportable practice reports.
- Teacher/coach views.

### PWA packaging

- Service worker.
- Install prompt.
- Offline app shell.
- Cache management.
- Update prompts.

This can wait until the normal browser app works. PWA work is not a substitute for Capacitor, but it may make Phase 1 nicer.

### Mobile Phase

- Capacitor project creation.
- Native filesystem implementation.
- Native preferences implementation.
- Background audio.
- Lock-screen controls.
- Bluetooth/headset controls.
- Steering-wheel controls.
- Wake-word voice commands.
- App Store / Google Play packaging.

---

## Suggested Build Order Summary

1. **Skeleton and tests.**
2. **Manifest/session domain engine.**
3. **Playbook zip import.**
4. **IndexedDB persistence.**
5. **Role selection/session setup.**
6. **Audio playback abstraction.**
7. **Usable rehearsal loop: cue, wait, repeat, hear line, next/back.**
8. **Variable-speed actor-line playback.**
9. **Speak-along mode.**
10. **Microphone/VAD spike.**
11. **Automatic hesitation and delivery timing.**
12. **Timing history and basic review.**
13. **Navigation polish.**
14. **Browser hardening.**
15. **Capacitor readiness review.**
16. **Wake-word/command stack decision note.**

---

## Definition of Done for Phase 1 Web App

Phase 1 is complete when:

- [ ] A user can import a valid Playbook zip.
- [ ] The Playbook persists locally.
- [ ] The user can select a role.
- [ ] The user can start or resume a rehearsal session.
- [ ] The app plays cues in sequence.
- [ ] The user can repeat cue, hear line, advance, go back, and pause.
- [ ] The actor's own reference line can play at 0.4x to 1.3x.
- [ ] Cues always play at 1.0x.
- [ ] Speak-along mode works.
- [ ] Tempo timing can measure hesitation and delivery pace.
- [ ] Line-specific target hesitation is supported when present.
- [ ] Timing history is stored locally.
- [ ] Basic problem-line review exists.
- [ ] The app works after reload.
- [ ] The app remains offline after import.
- [ ] Microphone use is transparent and limited.
- [ ] No GPL-family runtime dependency is present.
- [ ] Domain logic is tested.
- [ ] Core browser flows are covered by Playwright.
- [ ] Architecture is ready for a later Capacitor spike.
