# Cuemaster V2 UX And Wireframes

Status: draft for review. The functional mockup lives at `cuemaster-v2/mockups/index.html`.

## Product Thesis

Cuemaster v2 should feel like a focused rehearsal player, not a configurable audio workstation.

The actor's mental model should be:

```text
Pick a playbook -> pick my role -> pick how I want to practice -> press Play
```

The UI should avoid exposing separate cue playback, line playback, speak-along, auto-advance, and replay-line controls as independent concepts. Those details are represented by **Practice Flow**.

## Primary Use Cases

### 1. First-Time Actor Import

Goal: actor receives a `.playbook.zip`, opens Cuemaster, imports it, and starts practicing without understanding package internals.

UI needs:

- Obvious Import Playbook action.
- Clear storage/offline state.
- Playbook cards that show title, version/date, roles, and local status.
- Errors that tell the actor what to do next.

V2 implication:

- Library is a practical workbench, not a dashboard.
- One active production is enough for MVP, but multiple playbooks should not feel broken.

### 2. Resume Practice

Goal: actor opens the app and continues where they left off.

UI needs:

- A clear Resume action on each playbook.
- Last role, position, and flow visible.
- Start-over and choose-role available but secondary.

V2 implication:

- Persist the selected role, current line, flow, cue length, line pace, and display/content preferences.

### 3. Manual Line Practice

Goal: actor hears the cue, says the line, then chooses whether to check, repeat, or move on.

UI needs:

- One primary Play/Pause.
- Repeat cue.
- Hear line.
- Back/Next.
- Optional line reveal, configured outside the footer.

V2 implication:

- Manual is the default flow.
- Manual never auto-advances.
- The old line playback button becomes **Hear line**. It is a reminder action, not a second transport.

### 4. Driving Or Hands-Limited Review

Goal: actor presses Play once and hears useful rehearsal material continuously.

UI needs:

- Listen: cue -> reference -> next.
- Try: cue -> silent window -> next.
- Try Then Hear Line: cue -> silent window -> reference -> next.
- Large pause/resume control.
- No microphone permission.
- Recovery if iPhone requires another tap to continue.

V2 implication:

- This is continuous playback after a user gesture, not HTML autoplay.
- Line pace affects both reference playback and silent response windows.

### 5. Quick Reminder

Goal: actor is unsure and wants to hear the correct line once.

UI needs:

- **Hear line** visible as a secondary icon control.
- Hear line does not change the current line.
- Hear line uses line pace.

V2 implication:

- Avoid "play your line" language because it sounds like a second transport.
- This directly handles the frustration case where the actor does not want to hear the cue again just to be reminded of the line.

### 6. Blocking Reference

Goal: actor sees concise blocking text inline and can open a diagram when needed.

UI needs:

- Blocking note visible when enabled.
- Diagram opens on demand.
- Diagram has Previous, Next, Close in stable positions.
- Diagram never auto-opens during playback.

V2 implication:

- Blocking belongs to the current line context, not as a competing main mode.

### 7. Navigation, Search, And Jumping

Goal: actor jumps to a scene, bookmark, or search result.

UI needs:

- Search/browse affordance that does not compete with primary playback.
- Current position remains obvious.
- Jumping stops any active flow.

V2 implication:

- A read-only script browser can remain, but it should be a drawer/sheet from the single rehearsal surface rather than a second primary app page.
- Navigation is required for v2 MVP. Search can be part of the same drawer.

### 8. Whole-Play Listening

Goal: actor listens to the entire play they are performing in, without filtering to one role.

UI needs:

- A whole-play listening surface reachable from the Playbook card and navigation.
- Scene/part navigation.
- One primary Play/Pause.
- Full-script text display that auto-scrolls with playback, like a lyrics view.
- Current line highlighting.
- Clickable script lines for jumping forward/back.
- Optional inline blocking display where the Playbook includes it.
- Clickable blocking notes that open blocking diagrams.

V2 implication:

- The v1 Play page should not disappear. It should become **Whole Play** or **Listen to Play**, separate from role rehearsal, with autoscrolling script behavior preserved.
- Whole-play listening should reuse audio queue, cue assets, and script navigation, but it should not inherit role Practice Flow controls such as Hear line or Try.

### 9. Tempo Timing

Goal: actor optionally measures pickup/delivery timing.

UI needs:

- Explicit setup because microphone permission is risky on iOS.
- It should be an advanced/manual mode, not mixed with continuous driving flows.
- It should not appear on platforms where microphone setup is expected to cause audio-session problems.

V2 implication:

- Do not include tempo timing in the default options surface.
- Do not request the microphone for Manual, Listen, Try, or Try + Hear Line.
- Hide tempo timing entirely on iOS until testing proves it is usable there.

## Proposed Information Architecture

```text
Library
  -> Role Setup
      -> Rehearsal
         -> Options sheet
          -> Navigation/search sheet
          -> Blocking diagram sheet from inline blocking note
          -> Advanced timing setup
  -> Whole Play
      -> Navigation/search sheet
      -> Blocking diagram sheet from inline blocking note
```

There is one primary rehearsal surface. Everything else is a modal/sheet/drawer on top of that surface.

## Rehearsal Surface

Priority order:

1. Current position.
2. Current cue.
3. Actor line area.
4. Flow/status.
5. Primary transport.
6. Secondary actions.
7. Optional references/settings.

Flow/status should be an always-visible but compact single-row readout, not a tall panel. Rehearsal should use actor-flow language such as "Ready for cue" or "Your turn"; Whole Play should use playback language such as "Ready", "Playing", or "Paused".

The bottom controls should remain stable across states and use familiar icons. In the real app, prefer lucide icons.

```text
Previous   Repeat Cue   Play/Pause   Hear Line   Next
```

Button meanings:

- **Play/Pause**: starts or pauses the selected flow.
- **Previous**: previous actor line.
- **Next**: next actor line.
- **Repeat**: replay current cue.
- **Hear Line**: play the actor reference line once without advancing.

Not in the footer:

- **Flow**: setup/options only.
- **Show line**: setup/options only.
- **Show blocking**: setup/options only; inline blocking appears when enabled.
- **Options**: top app action, not a bottom transport action.
- **Navigation/search**: top app action, not a bottom transport action. Use a browse/search/list icon, not a generic hamburger.

## Practice Flow Selector

Use four actor-facing flow choices:

| Flow | UI Label | Summary |
|---|---|---|
| `manual` | Manual | Cue, then wait for me. |
| `listen` | Listen | Cue and line continuously. |
| `try` | Try | Cue, then give me time to speak. |
| `try_then_check` | Try + Hear Line | Cue, wait, then play the line. |

The mockup uses these labels. Final copy can be tuned after testing.

## Options Surface

Default options:

- Flow.
- Line pace.
- Cue length.
- Start/resume position.
- Text visibility and size.
- Directions, blocking, callouts.

Advanced options:

- Tempo timing setup.
- Timing tolerances.
- Storage diagnostics.

Do not expose old v1 auto-advance and auto-play-line controls.

On iOS, omit tempo timing from the options surface until the audio-session issue is resolved. On supported platforms, show it under Advanced with explicit microphone setup.

## Functional Mockup

Open:

```text
cuemaster-v2/mockups/index.html
```

What it demonstrates:

- Library cards.
- Role/setup screen.
- One rehearsal surface.
- Flow selector in setup/options only.
- Play/Pause sequencing for Manual, Listen, Try, and Try + Hear Line.
- Options sheet.
- Navigation/search sheet.
- Whole-play listening surface with autoscrolling script, clickable lines, and clickable blocking.
- Blocking diagram sheet opened from inline blocking.
- Stable compact icon controls.

What it does not demonstrate:

- Real Playbook import.
- Real audio playback.
- IndexedDB storage.
- Responsive edge cases beyond phone/desktop preview.

## Review Questions

- Are the four Practice Flow labels understandable?
- Is **Hear line** clear enough as the one-off reference-line action?
- Does the one-primary-Play model resolve the cue/line play confusion?
- Are the compact icon buttons clear enough?
- Does the top-left browse/search icon communicate navigation better than the hamburger?
- Does the Whole Play surface now cover the old Play page use case?
- Should tempo timing be hidden on iOS rather than shown as unavailable?
