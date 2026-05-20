# Cuemaster Practice Flow Simplification Plan

Status: proposed implementation plan. This should be implemented before adding more autoplay, speak-along, or auto-advance controls.

## Problem

Cuemaster's rehearsal controls are becoming hard to explain:

- Cue playback and line playback have separate play buttons.
- `speakAlongEnabled`, `speakAlongPauseMs`, `autoAdvanceMode`, `autoPlayLineMode`, tempo timing, and playback rate interact in ways that are not obvious.
- The current UI exposes implementation switches instead of actor goals.
- The car use case needs continuous playback after one user gesture, but it should not require microphone access.
- iPhone support needs the first audible playback to come from a user tap, then continue through a controlled app playback queue.

The objective is to reduce the feature surface while supporting the most important rehearsal flows.

## Product Direction

Replace separate "speak along", "autoadvance", and "replay line" controls with one user-facing setting:

```ts
type PracticeFlow =
  | "manual"
  | "listen"
  | "try"
  | "try_then_check";
```

User-facing labels:

| Flow | Sequence | Use Case |
|---|---|---|
| Manual | cue -> wait | Normal line practice. The actor chooses next/check/repeat. |
| Listen | cue -> reference -> next cue | Driving or passive review. |
| Try | cue -> silent response window -> next cue | Driving practice without hearing the answer. |
| Try, Then Check | cue -> silent response window -> reference -> next cue | Driving practice with immediate correction. |

The word "autoplay" should not be used in the main UI. Use **Flow** or **Practice Flow**. Technically this is continuous playback after the actor presses Play, not browser autoplay.

## Simplified Configuration

Keep these visible settings:

- **Flow**: Manual, Listen, Try, Try then Check.
- **Line pace**: 0.4x-1.3x, used for reference playback and derived silent response windows.
- **Cue length**: existing preset from `planning/specs/cue_window_presets.json`.
- **Start**: Resume, beginning, scene, bookmark.
- **Text**: lines shown/hidden, text size.
- **Content**: directions, blocking, callouts.

Move these out of the primary settings surface:

- `speakAlongEnabled`
- `speakAlongPauseMs`
- `autoAdvanceMode`
- `autoPlayLineMode`
- synced speak-along/tempo pace controls
- auto-advance-on-good-tempo behavior

Keep tempo timing as a separate optional feature, but do not combine it with continuous Flow modes in the MVP. Tempo timing remains a manual/mic-based practice mode because iOS microphone setup is a separate risk.

## Timing Rules

Line pace affects both reference playback and silent response windows.

```text
referencePlaybackRate = linePace
adjustedResponseMs = responseDurationMs / linePace
silentWindowMs = adjustedResponseMs + responsePaddingMs
```

Initial `responsePaddingMs`: 750ms.

Rules:

- Cue audio always plays at 1.0x.
- Callout audio always plays at 1.0x.
- Actor reference/response audio plays at `linePace`.
- Silent response windows are based on the target response duration adjusted by `linePace`.
- If a line has no response duration, fall back to a conservative text-derived estimate only if such an estimator already exists; otherwise use a default 3s window and log/report the missing duration as a Playbook quality problem.
- Manual flow never advances automatically.
- Listen, Try, and Try then Check advance until paused/stopped or the role ends.

## One Primary Transport

Remove the separate cue-play and line-play mental model.

Use one primary Play/Pause button:

- In Manual flow, Play means "play the current cue".
- In Listen flow, Play starts/resumes the continuous cue/reference sequence.
- In Try flow, Play starts/resumes the continuous cue/silent-window sequence.
- In Try then Check flow, Play starts/resumes the continuous cue/silent-window/reference sequence.
- While reference audio is playing, the same button pauses/resumes the current flow.
- Stop ends the current flow but keeps the cursor on the current line unless the line has already advanced.

Use secondary controls for deliberate jumps/actions:

- Back: previous role line.
- Repeat: replay current cue.
- Check: play the current actor reference line once.
- Next: advance to the next role line.
- Bookmark.

This reduces the confusing "which play button do I press?" question. There is one Play button for the session, and "Check" is a named action for hearing the correct line.

## Mobile Session Mockup

Normal portrait phone layout:

```text
┌────────────────────────────────────┐
│ The Curious Case...          P-3   │
│ Role: LILLIAN             Flow ▾   │
├────────────────────────────────────┤
│ CUE: CHRISTINE                    │
│ Do you mind if I record?           │
│                                    │
│ LILLIAN                            │
│ [hidden line text or current line] │
│                                    │
│ Status: Waiting for you            │
├────────────────────────────────────┤
│        ◀      ▶ / ⏸      ▶        │
│      Back      Play      Next      │
│                                    │
│        ↺      ✓       ★     ⚙     │
│      Repeat  Check  Bookmark Opts │
└────────────────────────────────────┘
```

Notes:

- The central button is always the session Play/Pause.
- "Check" replaces the old "play your line" button.
- "Repeat" means repeat cue, not repeat line.
- Flow is visible but compact.
- Options opens the full setup drawer/page.

Continuous-flow active state:

```text
┌────────────────────────────────────┐
│ The Curious Case...          P-3   │
│ Role: LILLIAN             Listen  │
├────────────────────────────────────┤
│ CUE: CHRISTINE                    │
│ Do you mind if I record?           │
│                                    │
│ LILLIAN                            │
│ Please do.                         │
│                                    │
│ Status: Playing reference          │
├────────────────────────────────────┤
│        ◀        ⏸        ▶        │
│      Back     Pause     Next       │
│                                    │
│        ↺      ✓       ★     ⚙     │
└────────────────────────────────────┘
```

Try flow waiting state:

```text
┌────────────────────────────────────┐
│ The Curious Case...          P-3   │
│ Role: LILLIAN              Try     │
├────────────────────────────────────┤
│ CUE: CHRISTINE                    │
│ Do you mind if I record?           │
│                                    │
│ LILLIAN                            │
│ [line hidden]                      │
│                                    │
│ Speak now        2.8s remaining    │
├────────────────────────────────────┤
│        ◀        ⏸        ▶        │
│      Back     Pause     Next       │
│                                    │
│        ↺      ✓       ★     ⚙     │
└────────────────────────────────────┘
```

## Options Mockup

The options panel should lead with actor-level choices, not timing internals.

```text
Practice
┌────────────────────────────────────┐
│ Flow                               │
│ [ Manual ] [ Listen ]              │
│ [ Try ]    [ Try, then Check ]     │
│                                    │
│ Line pace                          │
│ 0.8x  0.9x  [1.0x]  1.1x  1.2x    │
│                                    │
│ Cue length                         │
│ [ Full cue              ▾ ]        │
└────────────────────────────────────┘

Display
┌────────────────────────────────────┐
│ [ ] Show my line by default        │
│ Text size [ Normal ▾ ]             │
│ Blocking [ My role ▾ ]             │
└────────────────────────────────────┘

Content
┌────────────────────────────────────┐
│ [x] Include directions             │
│ [x] Blocking notes                 │
│ [x] Cue callouts                   │
└────────────────────────────────────┘

Advanced
┌────────────────────────────────────┐
│ Tempo timing setup                 │
│ Timing tolerances                  │
└────────────────────────────────────┘
```

Advanced should be collapsed by default. Continuous-flow users should never need to learn tempo-timing or auto-advance terminology.

## Flow State Machine

Implement a small app-owned flow runner separate from React components.

```ts
type FlowStep =
  | { kind: "cue"; lineId: string }
  | { kind: "silent-response"; lineId: string; durationMs: number }
  | { kind: "reference"; lineId: string }
  | { kind: "advance"; fromLineId: string };

type FlowRunState =
  | "idle"
  | "playing-cue"
  | "waiting-silent-response"
  | "playing-reference"
  | "paused";
```

Responsibilities:

- Build the next step sequence from `practiceFlow`, current line, cue preset, line pace, and content settings.
- Drive `AudioQueue` for cue/reference playback.
- Drive a cancelable timer for silent response windows.
- Advance the rehearsal engine only from the runner, not from scattered UI callbacks.
- Stop cleanly when the actor changes role, line, Playbook, cue preset, or practice flow.
- Surface a single display status for the UI.

## iPhone Playback Strategy

The user must press Play to start a flow. From that gesture:

- Start the first audible cue immediately.
- Chain later cue/reference playback through the same flow runner.
- Do not rely on the HTML `autoplay` attribute.
- Catch `HTMLMediaElement.play()` rejections.
- If iOS blocks continuation, pause the runner and show "Tap Play to continue."
- Do not request microphone permission for Listen, Try, or Try then Check.

## Reduced Functionality Decisions

Remove or defer these for the first simplified flow release:

- Conditional auto-advance based on tempo quality.
- Auto-play line only when off target.
- Separate speak-along toggle.
- Separate line playback transport.
- Simultaneous tempo timing and continuous flow.

Keep as explicit actions:

- Check current line.
- Repeat cue.
- Next/back.
- Tempo timing as an Advanced/manual mode.

## Implementation Checklist

### Phase 1: Domain Model

- [ ] Add `PracticeFlow` type.
- [ ] Add `practiceFlow` to session configuration and persistence.
- [ ] Keep conservative compatibility mapping from old settings:
  - [ ] `autoAdvanceMode=disabled` -> `manual`, even if `speakAlongEnabled=true`.
  - [ ] `autoAdvanceMode!==disabled` plus `autoPlayLineMode=disabled` -> `try`.
  - [ ] `autoAdvanceMode!==disabled` plus `autoPlayLineMode=always` -> `try_then_check`.
  - [ ] `autoAdvanceMode!==disabled` plus ambiguous conditional settings -> `manual` with a one-time local setting reset if preserving behavior is unclear.
- [ ] Stop writing new `autoAdvanceMode`/`autoPlayLineMode` values once the new flow is active.
- [ ] Add unit tests for old-setting migration.

### Phase 2: Flow Runner

- [ ] Add a flow runner service under `cuemaster/src/rehearsal/`.
- [ ] Build step sequences for Manual, Listen, Try, and Try then Check.
- [ ] Add silent response timers derived from adjusted response duration.
- [ ] Add cancellation for role/line/settings changes.
- [ ] Add play rejection handling for iOS/browser policy failures.
- [ ] Add unit tests for step sequencing and silent-window duration.

### Phase 3: Rehearsal Screen Controls

- [ ] Replace separate cue/line play controls with one primary Play/Pause.
- [ ] Rename "Hear my line" to "Check".
- [ ] Keep Repeat as "repeat cue".
- [ ] Keep Back/Next as line navigation.
- [ ] Ensure controls stay in stable positions across flow states.
- [ ] Ensure keyboard shortcuts map to the simplified commands.

### Phase 4: Options UI

- [ ] Replace Speak-along/Autoadvance option groups with Flow.
- [ ] Keep Line pace and Cue length visible.
- [ ] Move tempo timing and tolerance controls into Advanced.
- [ ] Remove sync controls from the default surface.
- [ ] Add concise help text only where needed for Flow choices.

### Phase 5: Product Design And Tests

- [ ] Update `planning/cuemaster/product_design.md` to describe Practice Flow as the core session model.
- [ ] Update user-facing docs once the UI is implemented.
- [ ] Add unit tests for persisted session migration.
- [ ] Add Playwright coverage for starting each flow.
- [ ] Manually test iPhone Safari and installed PWA for continuous playback after one Play tap.
- [ ] Manually test that no microphone permission is requested in continuous flows.

## Acceptance Criteria

- [ ] A new actor can start rehearsal with one Play button and does not see separate cue/line play buttons.
- [ ] Manual flow preserves cue-first, actor-speaks, explicit-next behavior.
- [ ] Listen flow plays cue -> reference -> next cue continuously after one Play tap.
- [ ] Try flow plays cue -> silent response window -> next cue continuously after one Play tap.
- [ ] Try then Check flow plays cue -> silent response window -> reference -> next cue continuously after one Play tap.
- [ ] Reference playback and silent windows respect configured line pace.
- [ ] The default options screen has fewer concepts than the current Speak-along/Tempo/Cue Pickup/Autoadvance grouping.
- [ ] iPhone testing confirms either continuous playback works or the UI recovers with "Tap Play to continue."
