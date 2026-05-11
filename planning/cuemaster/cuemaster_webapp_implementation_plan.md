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
  tempoTimingPreferred: boolean;
  defaultTargetHesitationMs: number; // default 750
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
- [x] Store Playbook manifest.
- [x] Store asset blobs or extractable asset records.
- [ ] Store import metadata.
- [x] Store selected role per Playbook.
- [x] Store session position per Playbook/role.
- [x] Store basic session config per Playbook/role.
- [ ] Store bookmarks.
- [ ] Store timing attempts.

#### Startup behavior

- [x] Load Playbook library on app launch.
- [x] Restore selected role when available.
- [x] Resume from saved position when available.
- [ ] Handle missing/corrupt local storage gracefully.

#### Tests

- [ ] Unit-test storage interface with memory implementation.
- [ ] Integration-test IndexedDB implementation where practical.
- [ ] Playwright test: import Playbook, reload page, Playbook remains in library.
- [ ] Playwright test: save session position, reload page, resume works.

### Acceptance Criteria

- [x] Imported Playbooks survive page reload.
- [x] Selected role survives page reload.
- [x] Current line position survives page reload.
- [x] Deleting a Playbook removes its manifest and session state.
- [x] Deleting a Playbook removes stored audio assets.
- [ ] Storage code is isolated behind an interface that can later be replaced by Capacitor filesystem/preferences implementations.

---

## Milestone 4 — Role Selection and Session Setup UI

### Goal

Allow the actor to choose a role and configure a rehearsal session.

### Checklist

#### Role select

- [x] Show actor roles.
- [x] Hide special roles by default.
- [x] Show role display names.
- [x] Save selected role.
- [x] Allow role switching.

#### Session setup

- [x] Start from beginning.
- [x] Resume from saved position.
- [ ] Choose scene/section if manifest structure supports it.
- [ ] Set cue depth.
- [ ] Toggle stage directions.
- [ ] Set response playback speed.
- [ ] Toggle speak-along mode.
- [ ] Toggle tempo timing.
- [ ] Show default target hesitation setting, initially fixed at 750ms or hidden under advanced settings.

#### UI constraints

- [ ] Large tap targets.
- [ ] Clear session start button.
- [ ] No dense settings wall.
- [ ] Settings should be saved per Playbook/role.

### Acceptance Criteria

- [ ] User can import a Playbook, choose a role, configure a session, and enter the Session screen.
- [ ] Selected settings persist across reload.
- [x] The UI does not expose special roles as normal actor choices.

---

## Milestone 5 — Audio Playback Foundation

### Goal

Implement reliable sequential audio playback in the browser.

This milestone does not yet require the full rehearsal UI.

### Checklist

#### Audio abstraction

- [x] Create `AudioPlayer` class/wrapper around `HTMLAudioElement`.
- [x] Support loading an audio asset by app asset ID/path.
- [x] Support play.
- [ ] Support pause.
- [x] Support stop.
- [x] Support ended event.
- [x] Support error event.
- [x] Support `playbackRate`.
- [x] Support pitch preservation where browser exposes it.
- [x] Expose current playback state.
- [x] Avoid React dependency.

#### Audio queue

- [x] Create `AudioQueue`.
- [x] Play one cue asset.
- [x] Play multiple cue assets sequentially.
- [x] Cancel queue.
- [x] Report queue completion.
- [x] Report queue failure.

#### Asset resolution

- [x] Resolve imported Playbook audio assets to playable object URLs.
- [x] Revoke object URLs when no longer needed.
- [x] Avoid loading all Playbook audio into memory at once.
- [x] Handle missing/failed audio asset.

#### Tests

- [x] Unit-test queue sequencing with mock player.
- [x] Unit-test cancellation.
- [x] Unit-test playback speed assignment.
- [ ] Browser/manual test with real audio fixture.

### Acceptance Criteria

- [x] App can play a cue audio file from an imported Playbook.
- [x] App can play multiple cue files sequentially.
- [x] App can play actor response audio at selected speed.
- [x] Cue audio always plays at `1.0x`.
- [x] Response audio can play from `0.4x` to `1.3x` in `0.1x` increments.
- [x] Audio playback logic is isolated enough that a Capacitor-native audio implementation can replace it later if needed.

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

- [x] Show play title.
- [x] Show selected role.
- [x] Show current position.
- [x] Show cue text.
- [x] Hide actor line by default.
- [x] Add reveal/hide actor line.
- [ ] Add large controls:
  - [x] Back
  - [x] Repeat Cue
  - [x] Hear My Line
  - [x] Skip/Next
  - [x] Stop

#### Playback behavior

- [ ] On session start, play cue for current line.
- [x] After cue playback, enter waiting state.
- [x] Repeat cue replays cue without advancing.
- [x] Hear My Line plays actor response audio without advancing.
- [x] Next advances to next actor line and plays next cue after session start.
- [x] Back moves to previous actor line and plays cue after session start.
- [x] Stop stops playback and saves state.
- [x] Resume restores line position and can replay current cue.

#### State persistence

- [x] Save current line after navigation.
- [x] Save playback mode safely as idle/waiting on reload; do not resume mid-audio.
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

- [x] User can rehearse through a role using on-screen controls.
- [x] User can repeat cue.
- [x] User can hear their line.
- [x] User can advance and go back.
- [x] User can reload and resume.
- [x] This milestone is demoable as a basic Cuemaster web app.

---

## Milestone 7 — Variable-Speed Role-Line Playback

### Goal

Support speed-adjusted playback for the actor's own reference lines.

### Checklist

- [x] Add playback speed control.
- [x] Support speeds from `0.4x` to `1.3x`.
- [x] Use `0.1x` increments.
- [x] Default to `1.0x`.
- [x] Persist selected speed per Playbook/role.
- [x] Apply speed only to selected actor response audio.
- [x] Force cue audio to `1.0x`.
- [x] Enable pitch preservation where supported.
- [x] Show current speed clearly in Session screen.
- [x] Add quick controls:
  - [x] Slower
  - [x] Faster
  - [x] Normal
- [x] Clamp invalid values.

### Acceptance Criteria

- [x] Actor can hear their own line at 0.4x through 1.3x.
- [x] Cue playback is never slowed by this setting.
- [x] The selected speed persists after reload.
- [x] Tests verify cue speed stays `1.0x`.

---

## Milestone 8 — Speak-Along Mode

### Goal

Let the actor speak along with the reference line at the selected response playback speed.

### Checklist

- [x] Add speak-along toggle.
- [x] Define speak-along behavior:
  - [x] cue plays at `1.0x`,
  - [x] response audio plays at selected speed,
  - [x] actor speaks along,
  - [x] app returns to waiting state or offers next/retry.
- [x] Ensure speak-along mode does not enable microphone timing at the same time.
- [x] Make conflict clear if tempo timing is also enabled.
- [x] Add Session screen button: **Speak Along** or reuse **Hear My Line** with mode-aware label.
- [x] Persist speak-along preference.
- [x] Add tests for cue speed and response speed.

### Acceptance Criteria

- [x] User can play cue then speak along with their line at selected speed.
- [x] Speak-along does not trigger timing.
- [x] Speak-along is useful before automatic timing exists.

---

## Milestone 9 — Microphone Permission and Voice Activity Detection Spike

### Goal

Prove that browser-based microphone access and simple voice activity detection can support tempo timing.

This is a technical spike, but it should leave usable code if successful.

### Checklist

#### Permission

- [x] Add explicit **Enable Tempo Timing** flow.
- [x] Explain microphone use:
  - [x] no recording,
  - [x] no transcription,
  - [x] no upload,
  - [x] voice activity detection only.
- [x] Request microphone permission.
- [x] Handle denied permission.
- [x] Handle missing microphone.
- [x] Handle browser security restrictions.

#### Voice activity detector

- [x] Capture microphone stream.
- [x] Analyze volume/energy over time.
- [x] Distinguish speech-like activity from silence/noise well enough for a first version.
- [ ] Add calibration or ambient noise baseline if needed.
- [x] Detect first speech after cue.
- [x] Detect end of attempt after long silence.
- [x] Ignore short internal pauses.
- [x] Subtract final silence from delivery time.
- [x] Stop and release microphone when timing is disabled.

#### Timing parameters

Initial internal defaults:

- [x] Default target hesitation: `750ms`.
- [x] Internal pause grace: approximately `750ms`.
- [x] End-of-line silence threshold: approximately `1500ms`.
- [x] Make thresholds constants in one place.
- [x] Keep thresholds adjustable in code for testing.

#### Tests/manual checks

- [ ] Manual test in quiet room.
- [ ] Manual test with laptop fan/background noise.
- [ ] Manual test with deliberate short internal pause.
- [ ] Manual test with long ending pause.
- [ ] Manual test permission denial.
- [ ] Manual test repeated attempts without leaking mic streams.

### Acceptance Criteria

- [x] Browser asks for microphone permission only when tempo timing is enabled.
- [x] App can detect first speech after cue.
- [x] App can detect end of delivery after long silence.
- [x] App does not save audio.
- [x] App does not transcribe audio.
- [x] App releases microphone when timing is off.
- [ ] Result is good enough to proceed to productized tempo timing, or the spike documents blockers.

---

## Milestone 10 — Automatic Hesitation and Delivery Pace Timing

### Goal

Add tempo timing to the rehearsal loop.

This is the third major useful milestone.

### Checklist

#### Timing flow

- [x] Cue plays at `1.0x`.
- [x] Microphone timing starts immediately after cue ends.
- [x] Hesitation timer starts immediately when cue ends.
- [x] First detected speech stops hesitation timer.
- [x] First detected speech starts delivery timer.
- [x] Short pauses are treated as part of delivery.
- [x] Long silence ends the attempt.
- [x] Final silence is subtracted from delivery time.
- [x] Tempo feedback is shown.
- [x] Actor can then:
  - [x] hear line,
  - [x] try again,
  - [x] repeat cue,
  - [x] next,
  - [x] back.

#### Target values

- [x] Use line-specific `timing.target_hesitation_ms` when present.
- [x] Fall back to default target hesitation, initially `750ms`.
- [x] Use Playbook response audio duration as target delivery duration.
- [x] If response has multiple segments, sum their durations.
- [x] Handle missing duration gracefully.

#### Feedback

- [x] Show hesitation:
  - [x] measured pickup time,
  - [x] target pickup time,
  - [x] sharp/close/late label.
- [x] Show delivery:
  - [x] measured delivery time,
  - [x] Playbook target duration,
  - [x] pace relative to target,
  - [x] fast/close/slow label.
- [x] Avoid acting-quality language.
- [x] Keep feedback readable and nonjudgmental.

#### Storage

- [x] Store timing attempts locally.
- [x] Store hesitation and delivery separately.
- [x] Store target values used at the time.
- [x] Store detection mode.
- [x] Limit history size if necessary.

#### Tests

- [x] Unit-test tempo calculations.
- [x] Unit-test hesitation target fallback.
- [x] Unit-test multi-segment duration sum.
- [x] Unit-test result labels.
- [x] Mock VAD tests for timing state transitions.
- [ ] Playwright/manual test for real microphone timing.

### Acceptance Criteria

- [x] Actor can complete a timed attempt after hearing a cue.
- [x] App reports hesitation and delivery pace separately.
- [x] App uses line-specific target hesitation when available.
- [x] App stores local timing history.
- [x] App remains useful if timing is disabled.

---

## Milestone 11 — Timing History and Basic Review

### Goal

Let the actor see which lines need work, without building a full analytics product.

### Checklist

- [x] Add simple timing history per line.
- [x] Show last attempt on Session screen.
- [x] Show recent attempts for current line.
- [x] Add basic Tempo Review screen.
- [x] List lines with late pickup.
- [x] List lines with slow delivery.
- [x] List lines with rushed delivery.
- [x] List bookmarked lines.
- [x] Allow jumping from review list to line.
- [x] Keep calculations local.
- [x] Avoid charts unless clearly useful.

### Acceptance Criteria

- [x] Actor can identify late-pickup lines.
- [x] Actor can identify slow-delivery lines.
- [x] Actor can identify rushed-delivery lines.
- [x] Actor can jump directly to a problem line.
- [x] Review feature is useful but not overbuilt.

---

## Milestone 12 — Script Browser, Bookmarks, and Navigation Polish

### Goal

Improve navigation once the core loop works.

### Checklist

- [x] Add script browser modal/screen.
- [x] Show scenes/parts where manifest structure supports it.
- [x] Show current position.
- [x] Show bookmarked lines.
- [x] Allow jump to scene.
- [x] Allow jump to bookmarked line.
- [x] Add bookmark toggle on Session screen.
- [x] Add keyboard shortcuts for desk rehearsal:
  - [x] Space: play/pause or repeat depending state.
  - [x] Right arrow: next.
  - [x] Left arrow: back.
  - [x] R: repeat cue.
  - [x] L: hear line.
  - [x] Escape: stop playback.
- [x] Ensure shortcuts do not interfere with text inputs.
- [x] Add accessible labels for all controls.

### Acceptance Criteria

- [x] Actor can jump around without walking line by line.
- [x] Actor can bookmark and revisit difficult lines.
- [x] Desk rehearsal is efficient with keyboard controls.

---

## Milestone 13 — Browser App Hardening

### Goal

Make the web app reliable enough to share with real users for early testing.

### Checklist

#### Error handling

- [x] Handle bad zip.
- [x] Handle missing audio.
- [x] Handle unsupported audio format.
- [x] Handle browser autoplay restrictions.
- [x] Handle storage quota errors.
- [x] Handle microphone permission denial.
- [x] Handle failed audio playback.
- [x] Handle stale object URLs.
- [x] Handle corrupted IndexedDB records.

#### Accessibility

- [x] Large tap targets.
- [x] Keyboard navigability.
- [x] Screen reader labels.
- [x] Visible focus states.
- [x] Sufficient contrast.
- [x] Reduced-motion friendly UI.
- [x] No essential information conveyed only by color.

#### Performance

- [ ] Import progress remains responsive.
- [ ] Large Playbook import does not freeze UI.
- [x] App does not keep unnecessary audio blobs in memory.
- [x] Revoke unused object URLs.
- [x] Timing detector does not run when disabled.
- [x] Session screen remains responsive during playback.

#### Privacy

- [x] Microphone explanation appears before permission request.
- [x] No audio recording occurs.
- [x] No analytics by default.
- [x] No network dependency after import.

#### Testing

- [x] Playwright happy path.
- [x] Playwright reload/resume path.
- [x] Playwright invalid import path.
- [x] Unit tests for domain/session/tempo.
- [ ] Manual test with at least one realistic Playbook.

### Acceptance Criteria

- [ ] App is good enough for a small group of real actors/testers.
- [x] Known limitations are documented.
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
