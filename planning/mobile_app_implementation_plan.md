# Mobile App Implementation Plan

Status: future fallback plan. Cuemaster is now PWA-first; active install/offline work belongs in [cuemaster/pwa_implementation_plan.md](cuemaster/pwa_implementation_plan.md). Resume this native/Capacitor plan only if real-device PWA testing proves a blocking limitation.

This plan covers Capacitor-based phone apps for Cuemaster and LineRecorder if the hosted PWA route is not sufficient. The browser apps remain the primary source of product behavior; any native work should wrap and extend them through narrow platform adapters rather than forking the apps.

## Goals

- Provide a fallback path for Android phone builds if PWA storage, import/export, playback, microphone, or install behavior blocks production use.
- Preserve the hosted browser apps and local-first file handoff workflow.
- Keep one React/Vite codebase per app and add native adapters only where the browser/WebView path is insufficient.
- Prove native storage, file import/export, audio playback, recording, lifecycle, and permissions only after the corresponding PWA capability has failed real-device testing.
- Keep dependency licensing compatible with permissive open-source or commercial distribution.

## Non-Goals

- Do not add accounts, sync, or a hosted backend.
- Do not make Google Drive, Dropbox, or a cloud picker required for v1.
- Do not implement Cuemaster wake-word or voice commands in the first mobile milestone.
- Do not add native-only product behavior that cannot be reasoned about from the existing app model.
- Do not optimize for large local libraries before one active production works reliably.
- Do not weaken Stager Playbook generation strictness unless a later design explicitly introduces a new package type or manifest mode.
- Do not start native implementation until the PWA-first plan records a specific native fallback trigger.

## Fallback Entry Criteria

Before resuming this plan, complete the real-device matrix in [cuemaster/pwa_implementation_plan.md](cuemaster/pwa_implementation_plan.md) and record why PWA is insufficient.

Valid fallback triggers include:

- Browser storage quotas or eviction make current Playbooks unreliable.
- File import/export is too confusing or impossible for the actor workflow.
- Foreground audio playback is unreliable for rehearsing.
- Required background playback, lock-screen media controls, or hardware controls cannot be achieved acceptably as a PWA.
- Microphone tempo timing cannot work reliably in the installed PWA.
- iOS install/offline limitations are unacceptable for target users.

Checklist:

- [ ] Complete the PWA real-device matrix.
- [ ] Identify the exact PWA limitation that blocks production use.
- [ ] Decide whether the limitation applies to Cuemaster only, LineRecorder only, or both.
- [ ] Record the fallback decision as an ADR under `planning/decisions/`.
- [ ] Confirm native implementation will preserve the hosted app as the source of product behavior.

## Product Shape Decision: Separate Apps Or Integrated Actor App

Before building LineRecorder Android, decide whether actors should install:

1. **Two apps:** Cuemaster for rehearsal and LineRecorder for recording.
2. **One actor app:** Cuemaster also imports Recording Requests and records replacement/missing lines.

Current recommendation: keep the first Android milestone focused on Cuemaster rehearsal, then evaluate an integrated actor app before implementing LineRecorder Android. Integration may reduce actor confusion, but it changes important package and missing-audio assumptions.

### Benefits Of Integrating LineRecorder Into Cuemaster

- One app for actors to install, learn, and grant permissions to.
- Cuemaster can surface a bad/missing/stale line and send the actor directly into a recording flow.
- Replacement recording requests can be created from rehearsal context without making the actor juggle apps.
- Mobile file import/export and sharing code can be reused inside one shell.
- Eventually, actors can rehearse, record corrections, and export returns from one local project.

### Costs And Risks

- Cuemaster currently consumes Playbooks, while LineRecorder consumes Recording Requests. Merging them risks muddying two clean package contracts.
- Cuemaster Playbook generation is intentionally strict: every rehearsable non-meta role line must have cue and response audio. Relaxing that would make rehearsal failures easier to ship accidentally.
- Recording needs deeper microphone, WAV capture, take storage, export validation, and troubleshooting than Cuemaster timing.
- A single app will need clear mode boundaries so "rehearse" and "record" do not confuse actors.
- Missing-audio tolerance can become a footgun if incomplete Playbooks are distributed as normal rehearsal packages.

### Missing Audio Policy If Integrated

Do not make normal Playbooks casually tolerate missing audio. Prefer one of these explicit designs:

- **Strict Playbook plus Recording Request import:** Cuemaster remains strict for Playbooks. The integrated app can separately import Recording Request packages and open a recording workflow. This preserves the current clean contracts.
- **Strict Playbook with repair requests:** A Playbook may include metadata saying specific lines need replacement, but required rehearsal audio still exists. Recording is a correction workflow, not a way to make an incomplete Playbook usable.
- **New draft/incomplete package mode:** If truly needed, define a separate manifest mode such as `package_type: "rehearsal_draft"` or an explicit `allow_missing_audio` flag. Cuemaster would show missing audio as a blocking warning and disable playback for those lines. This must be a new spec change, not an accidental relaxation of Playbook rules.

Recommended first choice: **strict Playbook plus Recording Request import**. It gives a single phone app later without weakening the Playbook contract that protects rehearsal quality today.

Checklist:

- [ ] Decide whether mobile v1 should remain two apps or become one integrated actor app.
- [ ] If integrated, decide whether the app name remains Cuemaster or becomes a broader actor-facing Quince app.
- [ ] Keep normal Playbook generation strict unless a new draft/incomplete package type is designed.
- [ ] Define how Recording Request import appears in the Cuemaster Library if integration is chosen.
- [ ] Define whether recording output remains a LineRecorder `role_recordings` package even when produced by Cuemaster.
- [ ] Define UI boundaries between rehearsal mode and recording mode.
- [ ] Decide whether LineRecorder web app remains a standalone hosted app after integration.

## Architecture Direction

- Use Capacitor, not React Native, for v1 mobile packaging.
- Create separate native app identities for Cuemaster and LineRecorder.
- Keep app domain logic, manifest validation, navigation, rehearsal state, recording state, and package validation in existing TypeScript modules.
- Keep browser adapters working. Add native adapters behind existing platform/storage/audio seams.
- Prefer official Capacitor plugins first. Any third-party native plugin needs license, maintenance, and platform-behavior review before adoption.
- Keep GPL-family, unclear-license, and unlicensed runtime dependencies out of shipped apps.

## Mobile App Identities

Suggested initial package ids:

- Cuemaster Android: `com.quince.cuemaster`
- LineRecorder Android: `com.quince.linerecorder`
- iOS bundle ids should mirror these only after Android proves the adapter shape.

These ids can change before store release, but changing them after external testing will create install/update friction.

## Shared Preflight

Checklist:

- [ ] Confirm Android development environment requirements in `planning/mobile_android_setup.md` or equivalent:
  - [ ] JDK version,
  - [ ] Android Studio version,
  - [ ] Android SDK/API target,
  - [ ] emulator setup,
  - [ ] physical-device USB debugging setup.
- [ ] Add a license-review checklist for Capacitor and native plugins.
- [ ] Decide whether to place Capacitor native folders inside each app (`cuemaster/android`, `linerecorder/android`) or under a shared `mobile/` folder.
- [ ] Add `.gitignore` entries for native build outputs while keeping native project source committed.
- [ ] Define package ids, app names, icons, and splash-screen placeholders.
- [ ] Add scripts for Android sync/build/run that do not disturb browser build scripts.
- [ ] Add documentation for local debug builds versus release builds.
- [ ] Keep Cloudflare/static web deployment scripts unchanged.

## Phase 1: Cuemaster Android Shell

Purpose: prove the existing Cuemaster web app can run as an Android app without behavior changes.

Checklist:

- [ ] Add Capacitor dependencies to `cuemaster/`.
- [ ] Initialize Capacitor for Cuemaster with Android as the first platform.
- [ ] Configure the Android app id and display name.
- [ ] Configure Vite build output as the Capacitor web asset directory.
- [ ] Add `cuemaster` scripts:
  - [ ] `mobile:sync:android`,
  - [ ] `mobile:open:android`,
  - [ ] `mobile:build:android`,
  - [ ] `mobile:run:android` if practical.
- [ ] Confirm a debug APK launches on Android emulator.
- [ ] Confirm a debug APK launches on a physical Android phone.
- [ ] Confirm the app starts offline after first install.
- [ ] Confirm app startup does not require the Cloudflare-hosted site.
- [ ] Add a short manual-test checklist for each Android build.

Acceptance:

- [ ] Android app opens to the Cuemaster Library screen.
- [ ] Browser-hosted Cuemaster still builds and passes existing tests.
- [ ] No runtime dependency with an incompatible license is added.

## Phase 2: Cuemaster Android Import And Storage

Purpose: prove Playbook import and persistence on Android before changing storage architecture.

Recommended first approach: preserve the current browser/WebView file input and IndexedDB storage. Only move to native filesystem storage if real-device testing shows quota, performance, or playback problems.

Checklist:

- [ ] Import a small fixture `.playbook.zip` on Android emulator.
- [ ] Import the same fixture on physical Android.
- [ ] Reload/restart the app and confirm the Playbook remains available.
- [ ] Confirm stored audio assets resolve after restart.
- [ ] Import a current MP3 Playbook built from a real production.
- [ ] Measure import time and UI responsiveness.
- [ ] Measure storage used and any quota warnings.
- [ ] Try replacement import with a newer Playbook and confirm compatible local progress is preserved.
- [ ] Try invalid Playbook import and confirm error text is actionable.
- [ ] If WebView file input is awkward, add a native file-picker adapter behind the import boundary.
- [ ] If IndexedDB fails or quota is too low, design a native filesystem-backed audio asset repository before implementing it.

Acceptance:

- [ ] An Android actor can import a Playbook from device storage.
- [ ] The Playbook survives app restart.
- [ ] Cue and response audio can be loaded from persisted storage.
- [ ] The app gives clear failure text for invalid files or storage limits.

## Phase 3: Cuemaster Android Playback And Lifecycle

Purpose: make rehearsal playback credible on a phone.

Checklist:

- [ ] Play cue audio and actor response audio through the existing `AudioQueue`.
- [ ] Confirm pause/resume/next/back/repeat behavior while the app is foregrounded.
- [ ] Confirm playback after screen lock.
- [ ] Confirm behavior when Android sends the app to background.
- [ ] Confirm behavior when another audio app starts playback.
- [ ] Confirm behavior during notification and call interruptions.
- [ ] Decide whether browser `HTMLAudioElement` is good enough for v1 foreground playback.
- [ ] If background playback or media controls are required for v1, add a native audio/media-control spike with license-approved plugins only.
- [ ] Test Bluetooth earbuds play/pause controls if media controls are added.
- [ ] Document whether Android v1 supports background playback or only foreground playback.

Acceptance:

- [ ] Foreground rehearsal playback is reliable on Android.
- [ ] Lifecycle limitations are documented in user-facing terms.
- [ ] Any native audio plugin has passed license review.

## Phase 4: Cuemaster Android Tempo Timing

Purpose: verify microphone-based timing behavior on Android without adding voice commands.

Checklist:

- [ ] Confirm microphone permission prompt text and timing.
- [ ] Enable tempo timing and confirm the app gets microphone input.
- [ ] Confirm microphone input is released when timing is disabled.
- [ ] Confirm cue playback and microphone timing do not conflict.
- [ ] Test quiet room, laptop/phone speaker leakage, earbuds, and noisy room.
- [ ] Compare pickup/delivery labels against browser behavior.
- [ ] Document Android-specific troubleshooting.

Acceptance:

- [ ] Tempo timing works well enough for Android testing or is explicitly disabled/deferred with clear UI.

## Phase 5: Cuemaster Android Release Candidate

Checklist:

- [ ] App icon and splash screen are present.
- [ ] App permissions are minimal and explainable.
- [ ] Privacy wording says Playbooks and timing data stay local.
- [ ] Android debug build is reproducible.
- [ ] Android release build can be produced locally.
- [ ] Manual smoke test passes on at least one physical Android phone.
- [ ] Existing Cuemaster unit and Playwright tests still pass.
- [ ] Add Android build instructions to Cuemaster README or a mobile setup doc.

Acceptance:

- [ ] Cuemaster Android is ready for private sideload testing.

## Phase 6: LineRecorder Android Shell

Purpose: bring LineRecorder to Android only after Cuemaster proves the packaging and storage approach.

Before starting this phase, complete the "Separate Apps Or Integrated Actor App" decision above. If the decision is to integrate, this phase should become "Cuemaster Recording Mode" rather than a separate LineRecorder Android shell.

Checklist:

- [ ] Add Capacitor dependencies to `linerecorder/`.
- [ ] Initialize Capacitor for LineRecorder with Android as the first platform.
- [ ] Configure the Android app id and display name.
- [ ] Add LineRecorder Android sync/build/run scripts.
- [ ] Launch the app on emulator and physical Android.
- [ ] Import a Recording Request from device storage.
- [ ] Confirm local project persistence after app restart.
- [ ] Confirm export package download/share path on Android.

Acceptance:

- [ ] Android app opens to LineRecorder project library.
- [ ] Recording Request import works on physical Android.
- [ ] Export path is clear enough for an actor to send the zip back.

## Phase 7: LineRecorder Android Recording Spike

Purpose: verify real phone recording quality and lifecycle before calling the mobile recorder viable.

Checklist:

- [ ] Request microphone permission through the WebView/browser API first.
- [ ] Confirm device selection behavior on Android.
- [ ] Confirm Clean Recording Mode constraints are honored or document what Android ignores.
- [ ] Confirm Noisy Room Mode behavior.
- [ ] Record, stop, play back, accept, retry, and export a short take.
- [ ] Verify exported WAV metadata:
  - [ ] sample rate,
  - [ ] channels,
  - [ ] duration,
  - [ ] clipping/quiet/no-signal flags.
- [ ] Confirm recordings persist after app restart.
- [ ] Confirm microphone is released when leaving the recording screen.
- [ ] Test interruption behavior:
  - [ ] app backgrounded,
  - [ ] screen locked,
  - [ ] notification,
  - [ ] phone call if available.
- [ ] Import the exported recording package into Stager.
- [ ] Build a Playbook from the imported recording.
- [ ] If WebView recording quality or permissions are insufficient, design a native recording adapter before implementing it.

Acceptance:

- [ ] A physical Android phone can produce a valid LineRecorder recording package that Stager imports.
- [ ] Known Android recording limitations are documented.

## Phase 8: iOS Follow-Up

Start iOS only after Android proves the adapter shape.

Checklist:

- [ ] Repeat Cuemaster shell/import/storage/playback tests on iPhone.
- [ ] Repeat Cuemaster tempo timing tests on iPhone.
- [ ] Repeat LineRecorder shell/import/export tests on iPhone.
- [ ] Repeat LineRecorder recording tests on iPhone.
- [ ] Resolve iOS-specific file picker and share-sheet behavior.
- [ ] Resolve iOS microphone permission and WebView lifecycle behavior.
- [ ] Decide whether any native adapters differ between Android and iOS.

Acceptance:

- [ ] iOS implementation can reuse the Android-proven TypeScript/native adapter boundaries without a product fork.

## Phase 9: Store And Distribution Readiness

Checklist:

- [ ] Decide initial distribution path:
  - [ ] private APK sideload,
  - [ ] internal Google Play testing,
  - [ ] TestFlight,
  - [ ] public stores later.
- [ ] Add app icons, splash screens, display names, and versioning.
- [ ] Add privacy policy text for local storage, file import/export, playback, and microphone timing/recording.
- [ ] Add third-party notices for mobile runtime dependencies.
- [ ] Add release build signing docs without committing secrets.
- [ ] Add backup/restore guidance for local app data.
- [ ] Add user-facing docs for importing files on Android/iOS.

## Deferred Features

- Cuemaster wake-word and voice commands.
- Native background audio if foreground playback is acceptable for first Android test.
- Google Drive Picker or provider-specific file integrations.
- Push notifications.
- Cross-device sync.
- Native waveform editing.
- Native Stager/producer tools.

## Test Matrix

Minimum manual device matrix before broader testing:

- [ ] Android emulator, current stable API.
- [ ] Physical Android phone, current or recent OS.
- [ ] Older physical Android phone if available.
- [ ] Bluetooth earbuds for Cuemaster playback.
- [ ] Wired or built-in microphone for LineRecorder.
- [ ] iPhone only after Android milestones complete.

For each device, record:

- device model,
- OS version,
- app version/build,
- Playbook or Recording Request used,
- import/export time,
- storage used,
- playback/recording result,
- permission prompts,
- lifecycle failures.

## Definition Of Done For First Android Milestone

- [ ] Cuemaster Android debug build installs on a physical phone.
- [ ] Actor imports a Playbook from local device storage.
- [ ] Actor rehearses at least one role line with cue and response audio.
- [ ] App survives restart with the Playbook still available.
- [ ] Existing web app tests still pass.
- [ ] New Android-specific limitations are documented.

## Definition Of Done For First LineRecorder Android Milestone

- [ ] LineRecorder Android debug build installs on a physical phone.
- [ ] Actor imports a Recording Request from local device storage.
- [ ] Actor records, accepts, and exports at least one take.
- [ ] Stager imports the exported package.
- [ ] Existing browser LineRecorder tests still pass.
- [ ] New Android-specific limitations are documented.
