# Cuemaster Use Cases

## Purpose

This document describes the primary use cases for Cuemaster, a local-first rehearsal app for actors learning lines from a production-supplied Playbook.

Cuemaster is built around a simple but powerful loop:

```text
Hear cue → speak line from memory → optionally hear reference → advance
```

The app does not require actors to record source material. Instead, a production, school, publisher, or other organizer prepares a Playbook containing structured script metadata and professional audio for cues, role lines, directions, and optional callouts.

This document focuses on what actors, productions, and related users need to do with the app. It is intended to guide product design, implementation priorities, and later acceptance tests.

---

## User Roles

### Actor

The primary user. The actor imports a Playbook, selects a role, and rehearses lines using cue audio, reference audio, navigation controls, and optional tempo feedback.

### Production / School / Publisher

The organization that prepares and distributes Playbooks. This user does not normally interact with Cuemaster during rehearsal, but their needs shape import, packaging, and compatibility requirements.

### Director / Coach / Teacher

A secondary user who may recommend rehearsal settings, review tempo reports, or help actors identify difficult lines. This user may never directly use the app in v1, but future reporting features should leave room for them.

---

## Core Actor Use Cases

### UC-001: Import a Playbook

**Actor goal:** Add a production-supplied Playbook to the app.

**Scenario:**

1. The actor receives a `.zip` Playbook from a production, school, publisher, or rehearsal organizer.
2. The actor opens Cuemaster.
3. The actor chooses **Import Playbook**.
4. The app validates the Playbook manifest and audio assets.
5. The Playbook appears in the actor’s local library.

**Notes:**

- The app should work without accounts or server-side sync.
- Imported Playbooks should be available offline after import.
- Large Playbooks should import without freezing the UI.

---

### UC-002: Select a Role

**Actor goal:** Choose the role they are rehearsing.

**Scenario:**

1. The actor opens a Playbook.
2. Cuemaster shows the available actor roles.
3. The actor selects their role.
4. Cuemaster prepares a role-specific rehearsal sequence.

**Notes:**

- Narrator, caller, announcer, and other special system roles should not appear as normal actor roles by default.
- A user may switch roles later, especially in educational or understudy contexts.

---

### UC-003: Rehearse a Line from a Cue

**Actor goal:** Practice recalling a line after hearing the cue.

**Scenario:**

1. Cuemaster plays the cue audio.
2. Cuemaster waits.
3. The actor speaks their line from memory.
4. The actor chooses one of:
   - hear the reference line,
   - repeat the cue,
   - go back,
   - skip,
   - advance to the next line.

**Notes:**

- The app should not auto-advance after the cue.
- The actor remains in control of pacing through the rehearsal sequence.

---

### UC-004: Hear the Correct Reference Line

**Actor goal:** Compare their attempted line with the Playbook recording.

**Scenario:**

1. The actor attempts their line from memory.
2. The actor taps or commands **Hear My Line**.
3. Cuemaster plays the recorded reference audio for the actor’s line.
4. Cuemaster returns to the waiting state for the same line.

**Notes:**

- This supports self-assessment without algorithmic scoring.
- Reference playback may use variable speed when the actor is rehearsing their own role line.

---

### UC-005: Repeat the Cue

**Actor goal:** Hear the cue again without advancing.

**Scenario:**

1. The actor is waiting to speak or has just attempted a line.
2. The actor chooses **Repeat Cue**.
3. Cuemaster replays the cue audio for the current line.
4. Cuemaster returns to the waiting state.

**Notes:**

- This is especially important for eyes-free rehearsal.
- Hardware and voice controls should support this action.

---

### UC-006: Move to the Next Line

**Actor goal:** Advance after completing a line attempt.

**Scenario:**

1. The actor attempts a line.
2. The actor chooses **Next**.
3. Cuemaster advances to the next line for the selected role.
4. Cuemaster plays the next cue.

**Notes:**

- The actor may advance without hearing the reference line.
- Advancement should always be explicit.

---

### UC-007: Go Back to a Previous Line

**Actor goal:** Rehearse an earlier line again.

**Scenario:**

1. The actor chooses **Back**.
2. Cuemaster moves to the previous line for the selected role.
3. Cuemaster plays the cue for that previous line.

**Notes:**

- Back navigation should work through tap controls, hardware controls, and voice commands where available.

---

### UC-008: Start from a Chosen Scene or Section

**Actor goal:** Jump to a specific part of the play.

**Scenario:**

1. The actor opens the script browser or session setup.
2. The actor chooses a scene, part, or section.
3. Cuemaster moves to the first line for the selected role in that section.
4. Rehearsal begins from there.

**Notes:**

- The Playbook manifest should expose enough structure to support scene-level navigation.
- This is essential for rehearsing assigned scenes without walking through the whole play.

---

### UC-009: Bookmark a Problem Line

**Actor goal:** Mark a difficult line for later practice.

**Scenario:**

1. The actor reaches a difficult line.
2. The actor taps or commands **Bookmark**.
3. Cuemaster saves the current line ID.
4. The actor can later jump directly to bookmarked lines.

**Notes:**

- Bookmarks may later integrate with timing history and problem-line drills.

---

### UC-010: Resume a Previous Session

**Actor goal:** Continue where they left off.

**Scenario:**

1. The actor opens Cuemaster.
2. Cuemaster detects a saved session for a Playbook and role.
3. The actor chooses **Resume**.
4. Cuemaster restores the selected role, line position, and rehearsal settings.

**Notes:**

- Resume should work offline.
- The app should also offer **Start Over**.

---

## Eyes-Free and Mobile Use Cases

### UC-011: Rehearse While Driving

**Actor goal:** Practice lines without looking at or touching the screen.

**Scenario:**

1. The actor starts a rehearsal session before driving.
2. The actor enables driving mode.
3. Cuemaster minimizes visual content.
4. The actor controls the session using hardware media controls and/or voice commands.

**Notes:**

- Text should be hidden or minimized in driving mode.
- Cues and role lines remain audio-first.
- Background audio behavior and media controls must be validated early in mobile development.

---

### UC-012: Use Hardware Media Controls

**Actor goal:** Control rehearsal with steering-wheel, headset, Bluetooth, or lock-screen controls.

**Scenario:**

1. The actor starts a session on a phone.
2. The app registers appropriate media-session actions.
3. The actor uses hardware controls to repeat, advance, pause, or resume.

**Notes:**

- This is a core mobile convenience but depends on license-safe Capacitor/native integration.
- GPL or unclear-license plugins must not be used.

---

### UC-013: Use Voice Commands

**Actor goal:** Control rehearsal hands-free.

**Scenario:**

1. The actor enables voice commands.
2. Cuemaster listens for a constrained wake word.
3. The actor says a command such as:
   - “next,”
   - “again,”
   - “line,”
   - “back,”
   - “pause.”
4. Cuemaster performs the requested action.

**Notes:**

- Voice commands should be constrained to a small vocabulary.
- The app should not require cloud speech recognition.
- Voice command technology must be permissively licensed, including any bundled models.

---

### UC-014: Rehearse While Walking or Doing Chores

**Actor goal:** Use rehearsal time while doing other low-attention activities.

**Scenario:**

1. The actor starts a session.
2. The phone may be locked or in a pocket.
3. Cuemaster continues audio playback.
4. The actor uses headset controls, hardware controls, or voice commands.

**Notes:**

- This overlaps with driving mode but does not require the stricter visual simplification of driving mode.

---

## Desk and Study Use Cases

### UC-015: Rehearse at a Desk

**Actor goal:** Use Cuemaster as a conventional browser app.

**Scenario:**

1. The actor opens the web app on a laptop or desktop.
2. The actor imports a Playbook.
3. The actor uses large on-screen controls to rehearse.
4. The actor may reveal or hide their line text.

**Notes:**

- The Phase 1 browser app should be useful on its own, not merely a throwaway prototype.
- Keyboard shortcuts may be useful later.

---

### UC-016: Reveal the Current Line Text

**Actor goal:** Check the text when stuck.

**Scenario:**

1. The actor is waiting to speak.
2. The actor taps **Reveal Line**.
3. Cuemaster shows the current line text.
4. The actor may hide the text again.

**Notes:**

- The default should encourage recall, not reading.
- Driving mode should not display full line text.

---

### UC-017: Browse the Script Structure

**Actor goal:** Navigate the Playbook by scene or section.

**Scenario:**

1. The actor opens the script browser.
2. Cuemaster displays the play structure.
3. The actor selects a scene or section.
4. Cuemaster jumps to the appropriate line for the selected role.

**Notes:**

- Script browsing should reflect the Playbook manifest structure.
- This does not require full script-authoring functionality.

---

## Cue and Context Use Cases

### UC-018: Rehearse with Minimal Cue Context

**Actor goal:** Practice with only the immediate cue.

**Scenario:**

1. The actor sets cue depth to one.
2. Cuemaster plays only the immediate cue for each line.
3. The actor responds from memory.

**Notes:**

- This is the default line-learning mode.

---

### UC-019: Rehearse with Expanded Cue Context

**Actor goal:** Hear more context before each line.

**Scenario:**

1. The actor increases cue depth.
2. Cuemaster plays multiple preceding cue items before the actor’s line.
3. The actor practices within a broader dramatic context.

**Notes:**

- Expanded context helps when the actor knows the line but not the entrance.
- The app must avoid making cue sequences confusing or overly long.

---

### UC-020: Include Stage Directions in Cue Context

**Actor goal:** Hear relevant directions as part of rehearsal.

**Scenario:**

1. The actor enables stage directions.
2. Cuemaster includes narrator/direction audio where available.
3. The actor hears movement or context cues before speaking.

**Notes:**

- Stage directions should be optional.
- Directions may be important for blocking or scene memory.

---

## Tempo Training Use Cases

Tempo training is a distinct feature cluster. It does not score acting quality and does not judge whether the actor said the correct words. It measures timing.

Tempo training should report two separate measures:

1. **Hesitation** — how long after the cue ends before the actor begins speaking.
2. **Delivery pace** — how long the actor takes to deliver the line after beginning speech, compared with the Playbook recording duration.

These are separate problems. An actor may know a line but begin too late. Another actor may begin promptly but deliver too slowly. Cuemaster should help identify both.

---

### UC-021: Play Actor’s Own Line at Variable Speed

**Actor goal:** Hear their own line more slowly or quickly while practicing.

**Scenario:**

1. The actor selects a rehearsal playback speed.
2. Cuemaster plays cue audio at normal performance speed.
3. When the actor requests their own line, Cuemaster plays the actor’s reference line at the selected speed.

**Notes:**

- Only the selected actor role’s response audio should support variable-speed playback.
- Cue audio should stay at 1.0x performance speed.
- Suggested supported speeds: 0.4x to 1.3x in 0.1x increments.
- Pitch preservation should be enabled where supported.

---

### UC-022: Speak Along with the Reference Line

**Actor goal:** Practice saying the line with the Playbook recording as real-time support.

**Scenario:**

1. The cue plays at normal speed.
2. Cuemaster plays the actor’s own reference line at the selected rehearsal speed.
3. The actor speaks along with the recording.
4. The recording gives real-time correction and forward momentum.

**Notes:**

- This is most useful early in memorization.
- Speak-along mode should not be combined with automatic timing in v1, because the microphone would also hear the reference audio.
- Speak-along mode is a practice aid, not a test mode.

---

### UC-023: Gradually Increase Role-Line Playback Speed

**Actor goal:** Move from slow recall to target performance speed.

**Scenario:**

1. The actor starts with a slow reference speed such as 0.5x or 0.6x.
2. The actor rehearses the line or section.
3. The actor increases speed toward 1.0x.
4. The actor eventually rehearses at or near target pace.

**Notes:**

- This may begin as a manual control.
- A later enhancement could provide automatic speed ramps.

---

### UC-024: Automatically Measure Hesitation After Cue

**Actor goal:** Know whether they are entering promptly after the cue.

**Scenario:**

1. Tempo timing is enabled.
2. Cuemaster plays the cue at normal speed.
3. When the cue ends, Cuemaster opens the microphone immediately.
4. The hesitation timer starts immediately.
5. Cuemaster listens for voice activity.
6. When speech is first detected, Cuemaster stops the hesitation timer.
7. Cuemaster reports the hesitation duration.

**Notes:**

- The app does not need to understand the words.
- Hesitation is measured as time from cue end to first detected speech.
- A default target hesitation should be defined, such as 500ms.
- The Playbook manifest should support optional line-specific target hesitation.

---

### UC-025: Compare Hesitation to a Default Target

**Actor goal:** Receive simple feedback on pickup timing.

**Scenario:**

1. The actor completes a timed attempt.
2. Cuemaster compares the measured hesitation to the default target.
3. Cuemaster reports whether the pickup was sharp, acceptable, or late.

**Example feedback:**

```text
Pickup: 1.3s
Target: 0.5s
Late by: 0.8s
```

**Notes:**

- The default target is a generic rehearsal aid, not a universal acting rule.
- Some lines require a deliberate beat.
- Line-specific target hesitation should override the generic default when available.

---

### UC-026: Use Line-Specific Target Hesitation from the Playbook

**Actor goal:** Rehearse cue pickup according to the intended rhythm of the scene.

**Scenario:**

1. A Playbook line includes a target hesitation value.
2. Cuemaster uses that value instead of the generic default.
3. The actor receives feedback against the line-specific timing target.

**Notes:**

- This supports lines that require an immediate pickup, a deliberate pause, or a longer dramatic beat.
- The absence of line-specific timing metadata should fall back to the default target.

**Example manifest concept:**

```json
{
  "id": "0_5_MEGAERA",
  "timing": {
    "target_hesitation_ms": 500
  }
}
```

---

### UC-027: Automatically Measure Delivery Pace

**Actor goal:** Know whether the spoken line is slower or faster than the Playbook target.

**Scenario:**

1. The actor enables tempo timing.
2. The cue plays.
3. The microphone opens immediately after the cue.
4. Cuemaster detects the actor’s first speech.
5. Delivery timing begins.
6. Cuemaster continues timing through speech and short internal pauses.
7. A longer silence ends the attempt.
8. Cuemaster subtracts the final ending silence from the delivery time.
9. Cuemaster compares measured delivery time with the Playbook response audio duration.

**Notes:**

- This uses voice activity detection, not speech recognition.
- The app should not transcribe, record, or score the actor’s words.
- The Playbook response duration is the target delivery duration.

---

### UC-028: Ignore Short Pauses During Delivery

**Actor goal:** Avoid having normal speech pauses incorrectly end the timing attempt.

**Scenario:**

1. The actor begins speaking.
2. The actor pauses briefly inside a line.
3. Cuemaster treats the pause as part of the delivery.
4. Timing continues.
5. A longer silence indicates the end of the attempt.

**Notes:**

- Internal pause tolerance should be configurable internally.
- A reasonable initial threshold might treat pauses under roughly 750ms as internal pauses.
- A longer threshold, perhaps around 1500ms, may end the attempt.
- Thresholds should be tested with real rehearsal audio and real actors.

---

### UC-029: Subtract Final Silence from Delivery Time

**Actor goal:** Get a fair delivery-time measurement.

**Scenario:**

1. The actor finishes speaking.
2. Cuemaster detects a long silence.
3. Cuemaster stops timing.
4. Cuemaster subtracts the final silence that triggered the stop.
5. Cuemaster reports the measured spoken delivery time.

**Notes:**

- Without this adjustment, every measured attempt would include the app’s end-of-line silence threshold.
- This makes timing feedback more accurate.

---

### UC-030: View Tempo Feedback After an Attempt

**Actor goal:** Understand whether the problem was hesitation, delivery speed, or both.

**Scenario:**

1. The actor completes a timed attempt.
2. Cuemaster displays pickup feedback and delivery feedback separately.

**Example feedback:**

```text
Pickup
  You: 1.3s
  Target: 0.5s
  Result: late

Delivery
  You: 5.8s
  Playbook: 4.2s
  Pace: 72% of target
  Result: slow
```

**Notes:**

- Feedback should be simple and nonjudgmental.
- The app should avoid presenting timing as acting quality.

---

### UC-031: Track Timing History for a Line

**Actor goal:** See whether timing is improving.

**Scenario:**

1. The actor makes multiple timed attempts on the same line.
2. Cuemaster stores hesitation and delivery measurements.
3. The actor views recent attempts or summary statistics.

**Example history:**

```text
Line 0_5_MEGAERA

Attempt 1
  Pickup: 1.8s
  Delivery: 7.1s

Attempt 2
  Pickup: 1.1s
  Delivery: 5.9s

Attempt 3
  Pickup: 0.6s
  Delivery: 4.8s
```

**Notes:**

- This helps the actor see progress.
- Timing history should remain local unless a future sharing feature is explicitly designed.

---

### UC-032: Identify Late Pickup Lines

**Actor goal:** Find lines where they hesitate too long after the cue.

**Scenario:**

1. The actor has accumulated timing attempts.
2. Cuemaster identifies lines where hesitation exceeds the target by a meaningful margin.
3. The actor chooses a drill mode for late pickups.

**Notes:**

- This is valuable because hesitation is often a recall problem, not a delivery problem.
- Late pickup lines should be distinguishable from slow delivery lines.

---

### UC-033: Identify Slow Delivery Lines

**Actor goal:** Find lines that are being spoken too slowly relative to the Playbook.

**Scenario:**

1. The actor has accumulated timing attempts.
2. Cuemaster identifies lines where delivery pace is significantly below target.
3. The actor practices those lines using slower reference playback, speak-along mode, or repeated timed attempts.

**Notes:**

- Slow delivery may indicate weak recall, difficult phrasing, or a misunderstanding of scene rhythm.

---

### UC-034: Identify Rushed Delivery Lines

**Actor goal:** Find lines that are being spoken too quickly.

**Scenario:**

1. The actor has accumulated timing attempts.
2. Cuemaster identifies lines where delivery pace is significantly faster than target.
3. The actor drills those lines with the Playbook reference.

**Notes:**

- Fast delivery may be as problematic as slow delivery.
- The app should describe this as pacing feedback, not performance judgment.

---

### UC-035: Drill Problem Lines by Timing Category

**Actor goal:** Focus practice on the lines most in need of attention.

**Scenario:**

1. The actor opens a drill view.
2. Cuemaster offers categories such as:
   - late pickups,
   - slow delivery,
   - rushed delivery,
   - inconsistent timing,
   - bookmarked lines.
3. The actor selects a category.
4. Cuemaster rehearses only those lines.

**Notes:**

- This could be v1.1 or later.
- It builds naturally on per-line timing history.

---

### UC-036: Practice Pickup Timing Only

**Actor goal:** Improve entrance speed without focusing on full line delivery.

**Scenario:**

1. The actor chooses a pickup drill.
2. Cuemaster plays cue audio.
3. The actor starts the line promptly.
4. Cuemaster measures hesitation.
5. The actor stops after the first word or phrase.
6. Cuemaster repeats or advances.

**Notes:**

- This is especially useful for scenes with rapid exchanges.
- It may require a dedicated drill mode.

---

### UC-037: Practice Delivery Pace Only

**Actor goal:** Improve speaking speed after the line is already known.

**Scenario:**

1. The actor chooses a pace drill.
2. Cuemaster may skip cue timing and focus on delivery duration.
3. The actor speaks the line.
4. Cuemaster compares delivery time with the Playbook duration.

**Notes:**

- This can help actors who know the line but drag or rush it.
- It may be less useful for cue-based recall.

---

## Production and Distribution Use Cases

### UC-038: Production Distributes a Playbook

**Production goal:** Give actors a polished rehearsal resource.

**Scenario:**

1. A production prepares a Playbook from the script, role structure, and recorded audio.
2. The Playbook is distributed by file transfer, shared drive, QR code, CDN link, or rehearsal package.
3. Actors import the Playbook into Cuemaster.
4. Actors rehearse offline.

**Notes:**

- Cuemaster consumes Playbooks but does not author them in v1.
- Playbook authoring remains a separate workflow.

---

### UC-039: Drama School Provides Playbooks to Students

**School goal:** Give students structured rehearsal material.

**Scenario:**

1. A teacher prepares or receives Playbooks for scenes or plays.
2. Students import the Playbooks.
3. Students practice specific roles.
4. Teachers may later use timing reports to guide coaching.

**Notes:**

- Multi-role switching may be more important in school contexts.
- Future sharing/reporting features should not be assumed in v1.

---

### UC-040: Publisher Bundles a Playbook with a Script

**Publisher goal:** Add rehearsal value to a published play script.

**Scenario:**

1. A publisher distributes a script with an accompanying Playbook.
2. Actors or readers import the Playbook into Cuemaster.
3. Users rehearse or study the play.

**Notes:**

- Licensing and distribution terms for audio must be handled outside Cuemaster.
- The app should remain neutral about Playbook source.

---

## Accessibility Use Cases

### UC-041: Actor Uses Screen Reader Support

**Actor goal:** Navigate the app with VoiceOver or TalkBack.

**Scenario:**

1. The actor opens Cuemaster with a screen reader enabled.
2. Controls have meaningful labels.
3. The actor can import, select a role, start rehearsal, and control playback.

**Notes:**

- Audio-first design helps accessibility but does not replace proper UI labeling.
- Tap targets should be large and predictable.

---

### UC-042: Actor Uses Voice and Hardware Controls as Accessibility Aids

**Actor goal:** Rehearse with limited need for visual interaction.

**Scenario:**

1. The actor starts a session.
2. The actor uses voice commands or hardware controls.
3. The actor completes rehearsal without relying heavily on the screen.

**Notes:**

- This overlaps with driving mode but should not be framed only around driving.

---

## Privacy and Trust Use Cases

### UC-043: Actor Uses Microphone for Timing Without Being Recorded

**Actor goal:** Benefit from timing feedback without creating recordings.

**Scenario:**

1. The actor enables tempo timing.
2. Cuemaster requests microphone permission.
3. The app explains that the microphone is used for voice activity detection only.
4. The actor completes timed attempts.
5. No audio is saved or transmitted.

**Notes:**

- The app should be explicit that it is not transcribing, recording, or uploading audio.
- Future recording features, if any, must be opt-in and separately designed.

---

### UC-044: Actor Rehearses Offline

**Actor goal:** Use the app without network access.

**Scenario:**

1. The actor imports a Playbook.
2. The actor later opens Cuemaster without internet access.
3. All core rehearsal features continue to work.

**Notes:**

- Offline operation is central to Cuemaster.
- Cloud sync, accounts, stores, and analytics are not required for v1.

---

## Out-of-Scope Use Cases for v1

The following should not drive the v1 implementation:

- Speech correctness scoring.
- Full transcription of actor attempts.
- Cloud account sync.
- In-app Playbook store.
- Playbook authoring UI.
- Director dashboard.
- Shared cast analytics.
- Video/self-tape recording.
- CarPlay / Android Auto integration.
- AI acting critique.
- Automatic emotional or performance scoring.

---

## Prioritization

### Core v1 Use Cases

- Import Playbook.
- Select role.
- Rehearse from cues.
- Hear reference line.
- Repeat cue.
- Next/back navigation.
- Resume session.
- Basic script/scene navigation.
- Variable-speed playback for actor role lines only.
- Speak-along mode.
- Automatic hesitation timing.
- Automatic delivery pace timing.
- Local timing history.

### Strong v1.1 Candidates

- Timing-based problem-line drills.
- Late-pickup drill.
- Slow/rushed delivery drill.
- Improved timing summaries.
- Scene-level timing overview.
- Voice commands.
- Hardware media controls.
- Mobile background audio hardening.

### Later Candidates

- Teacher/coach review views.
- Shared reports.
- Advanced Playbook timing metadata.
- Adaptive speed ramps.
- CarPlay / Android Auto.
- Optional recording and playback of actor attempts.

---

## Key Product Principles Reinforced by These Use Cases

1. **The actor remains in control.** Cuemaster does not auto-advance through rehearsal unless a specific drill mode is later designed to do so.

2. **Cue rhythm matters.** Cue audio should stay at performance speed so the actor learns real entrances.

3. **Only actor role lines are speed-variable.** Slowing the actor’s own reference line supports memorization without distorting the cue environment.

4. **Timing is not acting judgment.** Hesitation and delivery pace are measurable rehearsal aids, not performance scores.

5. **Microphone use should be narrow and transparent.** Tempo timing requires voice activity detection only. It should not transcribe, record, upload, or evaluate spoken content.

6. **Playbooks should support target hesitation.** A generic hesitation target is useful, but real theatre often requires line-specific pauses, immediate pickups, or deliberate beats.

7. **The app should identify where practice is needed.** Timing history should help actors find late pickups, slow lines, rushed lines, and inconsistent lines.

8. **Offline-first remains essential.** Once imported, a Playbook should support rehearsal without a network connection.
