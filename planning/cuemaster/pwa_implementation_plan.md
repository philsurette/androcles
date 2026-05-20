# Cuemaster PWA Implementation Plan

Status: active plan. Cuemaster should become an installable, offline-capable hosted PWA before any native/Capacitor phone-app work proceeds.

This plan replaces the previous assumption that a native wrapper is the primary mobile path. The hosted Cuemaster web app remains the product. The installable PWA should make that hosted app feel practical on phones: actors can open it from the home screen, rehearse without a network connection after first load/import, and keep Playbooks in local device storage.

Native packaging is now a fallback. Capacitor should be revisited only if real-device PWA testing shows a blocking limitation around storage, import/export, playback lifecycle, media controls, microphone access, or platform integration.

Useful platform references:

- MDN: [Making PWAs installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
- MDN: [Trigger installation from your PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt)
- MDN: [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- web.dev: [PWA caching](https://web.dev/learn/pwa/caching/)
- web.dev: [Installation prompt](https://web.dev/learn/pwa/installation-prompt/)

## Goals

- Make hosted Cuemaster installable from supported mobile and desktop browsers.
- Support offline launch after the actor has visited the app once.
- Support offline rehearsal after a Playbook has been imported.
- Keep Playbook data local in browser storage; do not introduce accounts, sync, or a backend.
- Preserve the current Cloudflare static deployment model.
- Keep the app usable in normal browser tabs for users who do not install it.
- Provide clear install, update, storage, and offline-status UX.
- Validate behavior on real Android devices first, then iOS Safari/iPadOS, then desktop install surfaces.

## Non-Goals

- Do not implement app-store distribution in this milestone.
- Do not require a native shell for import, storage, playback, or microphone timing unless PWA testing proves the browser path insufficient.
- Do not cache imported Playbook zip files in the service worker cache.
- Do not make service-worker caching responsible for user Playbook assets. Imported Playbook content belongs in IndexedDB or a later explicit storage adapter.
- Do not add cloud sync, actor accounts, or remote Playbook libraries.
- Do not weaken Playbook strictness to support incomplete rehearsal packages.
- Do not implement wake-word voice commands as part of the PWA install milestone.

## Product Position

Cuemaster should be a hosted app that actors can install. The producer publishes the app and distributes `.playbook.zip` files. Actors visit the hosted Cuemaster URL, optionally install it, import their Playbook, and rehearse from local storage.

The app should communicate three states clearly:

- **Online and ready:** the app can import Playbooks and check for app updates.
- **Offline app shell:** the app can open, but only already-imported Playbooks are available.
- **Offline with Playbook:** the app can rehearse a previously imported Playbook without network access.

## Browser Support Stance

Install prompts are browser-controlled and not fully uniform. Cuemaster should support a progressive install flow:

- On Chromium browsers that expose `beforeinstallprompt`, show an in-app Install action only after the browser reports that installation is available.
- On browsers without an app-owned install prompt, show concise manual install guidance.
- On iOS/iPadOS, assume installation may require the browser's Share/Add to Home Screen flow rather than a programmatic prompt.
- If installation is unavailable, the hosted app must still work in a browser tab.

Offline behavior should not depend on installation. A service worker can make the app shell available after a first successful visit, whether or not the user installs the app.

## Architecture Direction

- Add a web app manifest owned by Cuemaster.
- Add a service worker for app-shell caching and offline fallback.
- Prefer Vite PWA tooling if it stays simple and inspectable; otherwise keep a small app-owned service worker.
- Cache versioned build assets and the app shell.
- Use a network-first or stale-while-revalidate strategy for lightweight app metadata if needed.
- Keep Playbook import/extraction/storage in existing app modules.
- Store imported Playbook manifests, metadata, and audio assets in IndexedDB through the existing `CuemasterStorage` boundary.
- Add a narrow PWA platform adapter for install prompt availability, display mode detection, service-worker update state, and online/offline state.

## PWA Data Boundaries

Service worker cache:

- App HTML shell.
- Hashed JS/CSS build assets.
- Static icons and manifest assets.
- Offline fallback page or route.

IndexedDB:

- Imported Playbook metadata.
- Normalized Playbook data.
- Audio assets extracted from Playbooks.
- User progress, bookmarks, settings, timing attempts, and local app state.

Do not store user Playbook data in both places unless a later measured performance issue requires a specific cache. Duplicating large audio data would make storage pressure worse and complicate deletion.

## Phase 1: PWA Foundation

Purpose: make Cuemaster technically installable and offline-loadable without changing rehearsal behavior.

Checklist:

- [ ] Add a Cuemaster web app manifest.
- [ ] Add app icons at required sizes, including maskable icon support if practical.
- [ ] Set `name`, `short_name`, `description`, `start_url`, `scope`, `display`, `theme_color`, and `background_color`.
- [ ] Ensure `start_url` and `scope` work under Cloudflare-hosted nested paths.
- [ ] Add service-worker registration in production builds only.
- [ ] Precache the app shell and hashed Vite build assets.
- [ ] Add an offline fallback that opens the Library if cached app state exists.
- [ ] Confirm normal browser development mode is not complicated by service-worker caching.
- [ ] Add a build-time check that required PWA assets are present.
- [ ] Add documentation for clearing stale service-worker state during development.

Acceptance:

- [ ] A fresh production build exposes a valid manifest.
- [ ] A first online visit installs/activates the service worker.
- [ ] Reloading the app while offline still opens Cuemaster.
- [ ] Browser tab usage still works without installing.

## Phase 2: Install UX

Purpose: make installation discoverable without pretending every browser supports the same prompt.

Checklist:

- [ ] Add a `PwaInstallService` or equivalent adapter around `beforeinstallprompt`, display-mode detection, and install outcome state.
- [ ] Add an Install action to the Library or app menu when the browser reports that installation is available.
- [ ] Suppress the Install action when already running in standalone/display-app mode.
- [ ] Add manual install guidance for browsers where no programmatic prompt is available.
- [ ] Keep install guidance short and platform-specific.
- [ ] Add "not now" dismissal state so users are not nagged every session.
- [ ] Add an installed/standalone indicator only if it helps troubleshooting.
- [ ] Add unit tests for install-state decisions.

Acceptance:

- [ ] Chromium Android shows an actionable install path when eligible.
- [ ] iOS/iPadOS users see manual Add to Home Screen guidance instead of a broken button.
- [ ] Installed users are not prompted to install again.
- [ ] Users who never install can continue using the hosted app normally.

## Phase 3: Offline Rehearsal Validation

Purpose: prove that imported Playbooks remain usable without network access.

Checklist:

- [ ] Import a current MP3 Playbook from Cloudflare-hosted Cuemaster.
- [ ] Disable network and reload the app.
- [ ] Confirm the Library lists imported Playbooks while offline.
- [ ] Open a Playbook while offline.
- [ ] Play cue audio and response audio while offline.
- [ ] Navigate Play, Rehearse, blocking views, bookmarks, and settings while offline.
- [ ] Confirm stored blocking render-state/icon data works offline.
- [ ] Confirm tempo timing either works offline or clearly disables only network-dependent pieces.
- [ ] Confirm deletion of a Playbook removes large IndexedDB records.
- [ ] Add Playwright coverage for offline app-shell loading if practical.
- [ ] Add a manual real-device checklist for Android and iOS.

Acceptance:

- [ ] An actor can rehearse an imported Playbook in airplane mode.
- [ ] Offline failures are user-facing and actionable.
- [ ] No Playbook audio fetch depends on network after import.

## Phase 4: Microphone And iOS Audio-Session Validation

Purpose: prove that tempo timing can use the microphone without making playback unusably quiet, especially on iPhone/iPad Safari and installed iOS PWAs.

iOS/WebKit has a known class of problems where opening the microphone with `getUserMedia()` can switch the page into a recording-style audio session. That can duck playback, route audio through a quieter speaker path, change Bluetooth behavior, or leave playback quiet even after the microphone track stops. Treat this as a release risk for tempo timing, not as a general blocker for Playbook rehearsal.

Implementation checklist:

- [ ] Do not request microphone permission during app startup, Playbook import, Library browsing, or normal rehearsal setup.
- [ ] Request microphone access only when the user explicitly enables tempo timing or another microphone feature.
- [ ] Add a platform adapter for microphone setup so iOS-specific sequencing stays out of React screens.
- [ ] Lazy-create or resume any `AudioContext` used for voice activity detection after the user starts microphone setup.
- [ ] Test whether creating/resuming the audio context after microphone permission improves iOS playback volume.
- [ ] Test whether an explicit post-permission audio repair action from a user tap restores normal playback volume.
- [ ] Test `getUserMedia` constraints such as `echoCancellation`, `noiseSuppression`, and `autoGainControl` on iOS and record whether they affect playback volume, input reliability, or feedback.
- [ ] If supported by the target browser, test the WebKit `navigator.audioSession` type sequence as an optional iOS-only mitigation.
- [ ] After microphone setup, play a test cue and ask the user to confirm that playback volume is acceptable before enabling tempo timing.
- [ ] Stop microphone tracks when tempo timing is disabled or the user leaves the timing flow.
- [ ] Add user-facing iPhone troubleshooting for quiet playback after microphone setup.

Manual device matrix:

- [ ] iPhone Safari, browser tab.
- [ ] iPhone installed PWA from Home Screen.
- [ ] iPad Safari, browser tab.
- [ ] iPad installed PWA from Home Screen.
- [ ] iPhone with built-in speaker.
- [ ] iPhone with wired headphones if available.
- [ ] iPhone with AirPods/Bluetooth headphones.
- [ ] Chrome on iOS as a WebKit-based comparison, if target users are likely to try it.

Acceptance:

- [ ] Normal rehearsal playback remains loud before microphone permission is requested.
- [ ] If tempo timing is enabled, cue and response playback remain usable after microphone setup on supported devices.
- [ ] If iOS playback volume cannot be repaired reliably, tempo timing is disabled or clearly warned on affected iOS contexts while normal rehearsal remains available.
- [ ] Any decision to resume native work for microphone timing identifies the exact iOS PWA failure and the native API expected to fix it.

## Phase 5: Storage Readiness And Recovery

Purpose: make local browser storage understandable and recoverable for non-technical actors.

Checklist:

- [ ] Add a storage status view or diagnostic row in the Library.
- [ ] Show approximate imported Playbook size where available.
- [ ] Show browser storage/quota warnings when detectable.
- [ ] Add clear wording for private browsing, blocked storage, quota exhaustion, and corrupted local data.
- [ ] Provide a safe "remove Playbook" path that frees local storage.
- [ ] Provide a "repair/reimport" path for a Playbook that fails validation after storage errors.
- [ ] Confirm failed imports leave no half-installed Playbook.
- [ ] Add tests for quota and IndexedDB failure messages where they can be simulated.

Acceptance:

- [ ] Actors can understand whether a Playbook is stored locally.
- [ ] Storage failures explain what to do next.
- [ ] Removing old Playbooks is visible and reliable.

## Phase 6: App Updates

Purpose: avoid stale hosted app code confusing actors after the producer deploys a fix.

Checklist:

- [ ] Detect when a new service worker has installed and is waiting.
- [ ] Show a small "Update available" action at a non-disruptive point.
- [ ] Apply updates only after explicit user action or at a safe transition.
- [ ] Preserve imported Playbooks and local rehearsal progress across app updates.
- [ ] Add a version/build identifier visible in About or diagnostics.
- [ ] Document how producers can ask actors to update the app.
- [ ] Test update behavior between two local production builds.

Acceptance:

- [ ] A deployed app update can be discovered without clearing browser data.
- [ ] Applying an app update does not delete imported Playbooks.
- [ ] Users are not interrupted mid-cue by a forced reload.

## Phase 7: Real-Device PWA Matrix

Purpose: decide from evidence whether PWA is sufficient or a native fallback is needed.

Checklist:

- [ ] Test Android Chrome install, offline launch, import, storage persistence, playback, and update.
- [ ] Test Android Firefox if it is part of the expected actor environment.
- [ ] Test iPhone Safari Add to Home Screen, offline launch, import, storage persistence, playback, and update.
- [ ] Test iPhone microphone setup and verify playback volume before and after `getUserMedia`.
- [ ] Test iPad Safari if tablets are expected.
- [ ] Test iPad microphone setup and verify playback volume before and after `getUserMedia`.
- [ ] Test desktop Chrome or Edge install for laptop rehearsal.
- [ ] Test macOS Safari Add to Dock if relevant.
- [ ] Measure import time for small, medium, and current real Playbooks.
- [ ] Measure storage behavior for at least one large real Playbook.
- [ ] Test app behavior after browser restart, device restart, and low-storage conditions.
- [ ] Document known limitations in actor-facing language.

Acceptance:

- [ ] Android hosted PWA is viable for real rehearsal.
- [ ] iOS limitations are documented and either acceptable or listed as native-fallback triggers.
- [ ] Any decision to resume Capacitor work names the exact failed PWA capability.

## Native Fallback Triggers

Resume the Capacitor/native plan only if one or more of these are proven on real devices:

- Browser storage quotas or eviction make current Playbooks unreliable.
- File import/export is too confusing or impossible for the actor workflow.
- Foreground audio playback is unreliable for rehearsing.
- Required background playback, lock-screen media controls, or hardware controls cannot be achieved acceptably as a PWA.
- Microphone tempo timing cannot work reliably in the installed PWA.
- iOS microphone setup makes playback volume unusably quiet and cannot be repaired or isolated to optional timing features.
- iOS install/offline limitations are unacceptable for the target users.
- Cloudflare-hosted PWA update behavior creates operational risk that cannot be fixed in the browser app.

The fallback decision should be recorded as an ADR under `planning/decisions/` before native implementation resumes.

## Documentation Tasks

Checklist:

- [ ] Update actor quick-start docs with "Open Cuemaster, install if offered, import Playbook, rehearse offline."
- [ ] Add Android install instructions with screenshots or short device-tested wording.
- [ ] Add iPhone/iPad Add to Home Screen instructions.
- [ ] Add troubleshooting for offline mode, storage, updates, and private browsing.
- [ ] Add producer deployment notes explaining that Cloudflare deployment updates the hosted app, not actor Playbooks.
- [ ] Add a real-device release checklist to the deployment docs.

## Implementation Order

1. PWA foundation and manifest.
2. Service-worker app-shell caching.
3. Install UX.
4. Offline rehearsal validation.
5. Microphone and iOS audio-session validation.
6. Storage readiness and recovery.
7. App update flow.
8. Real-device matrix.
9. Native fallback decision, only if needed.
