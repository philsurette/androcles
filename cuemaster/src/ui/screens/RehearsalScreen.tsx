import { useEffect, useRef, useState } from "react";
import type { Bookmark } from "../../domain/bookmark";
import type { Line } from "../../domain/line";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import type { TimingAttempt } from "../../domain/timingAttempt";
import { AudioQueue } from "../../rehearsal/audioQueue";
import { cueWindowPresetForId, cueWindowPresets } from "../../rehearsal/cueWindowPreset";
import { shortcutForKey } from "../../rehearsal/keyboardShortcuts";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../rehearsal/playbackItems";
import type { RehearsalCommand, RehearsalShortcut } from "../../rehearsal/rehearsalCommand";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import { sectionOptionsForRole } from "../../rehearsal/sectionOptions";
import { scriptBrowserSections } from "../../rehearsal/scriptBrowser";
import { tempoFeedbackFor, type TempoFeedback } from "../../rehearsal/tempoFeedback";
import { defaultTargetHesitationMs } from "../../rehearsal/tempoTimingConfig";
import { VoiceActivityDetector } from "../../rehearsal/voiceActivityDetector";
import type { VoiceActivityResult } from "../../rehearsal/voiceActivityTracker";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { CueCard } from "../components/CueCard";
import { LineCard, type BlockingScope } from "../components/LineCard";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

type RehearsalScreenProps = {
  playbook: Playbook;
  role: Role;
  initialSession: RehearsalSession | null;
  initialStorageStatus?: string;
  onBack: () => void;
};

type PlaybackUiState = "idle" | "playing" | "paused";
type UtilityPanel = "script" | "bookmarks" | "timing" | "options";

export function RehearsalScreen({ playbook, role, initialSession, initialStorageStatus = "", onBack }: RehearsalScreenProps) {
  const [engine] = useState(() =>
    RehearsalEngine.forRole(playbook, role.id, {
      startLineId: role.lines[initialSession?.lineIndex ?? 0]?.id,
      includeDirections: initialSession?.includeDirections
    })
  );
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [position, setPosition] = useState(() => engine.position());
  const [playbackRate, setPlaybackRate] = useState(clampPlaybackRate(initialSession?.playbackRate ?? 1));
  const [cueWindowPresetId, setCueWindowPresetId] = useState(
    cueWindowPresetForId(initialSession?.cueWindowPresetId).id
  );
  const [playbackState, setPlaybackState] = useState<PlaybackUiState>("idle");
  const [playbackStatus, setPlaybackStatus] = useState<string>("");
  const [showLinesByDefault, setShowLinesByDefault] = useState(
    initialSession?.showLinesByDefault ?? initialSession?.revealLine ?? false
  );
  const [isLineRevealed, setIsLineRevealed] = useState(
    initialSession?.showLinesByDefault ?? initialSession?.revealLine ?? false
  );
  const [includeDirections, setIncludeDirections] = useState(engine.includeDirections());
  const [includeBlocking, setIncludeBlocking] = useState(initialSession?.includeBlocking ?? true);
  const [blockingScope, setBlockingScope] = useState<BlockingScope>(initialSession?.blockingScope ?? "role");
  const [hasStarted, setHasStarted] = useState(false);
  const [speakAlongEnabled, setSpeakAlongEnabled] = useState(initialSession?.speakAlongEnabled ?? false);
  const [speakAlongPauseMs, setSpeakAlongPauseMs] = useState(
    initialSession?.speakAlongPauseMs ?? defaultTargetHesitationMs
  );
  const [tempoTargetHesitationMs, setTempoTargetHesitationMs] = useState(
    initialSession?.tempoTargetHesitationMs ?? initialSession?.speakAlongPauseMs ?? defaultTargetHesitationMs
  );
  const [syncPracticeTiming, setSyncPracticeTiming] = useState(initialSession?.syncPracticeTiming ?? true);
  const [tempoTimingEnabled, setTempoTimingEnabled] = useState(false);
  const [tempoTimingPreferred, setTempoTimingPreferred] = useState(initialSession?.tempoTimingPreferred ?? false);
  const [tempoStatus, setTempoStatus] = useState<string>(
    initialSession?.tempoTimingPreferred
      ? "Tempo timing was enabled last session. Enable it again to use the microphone."
      : ""
  );
  const [tempoFeedback, setTempoFeedback] = useState<TempoFeedback | null>(null);
  const [lastTimingAttempt, setLastTimingAttempt] = useState<TimingAttempt | null>(null);
  const [recentTimingAttempts, setRecentTimingAttempts] = useState<TimingAttempt[]>([]);
  const [reviewAttempts, setReviewAttempts] = useState<TimingAttempt[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [storageStatus, setStorageStatus] = useState(initialStorageStatus);
  const [isCurrentLineBookmarked, setIsCurrentLineBookmarked] = useState(false);
  const [activeUtilityPanel, setActiveUtilityPanel] = useState<UtilityPanel | null>(null);
  const [voiceActivityDetector, setVoiceActivityDetector] = useState<VoiceActivityDetector | null>(null);
  const line = engine.currentLine();
  const cues = engine.cuePayloads(cueWindowPresetId);
  const sectionOptions = sectionOptionsForRole(playbook, role);
  const currentSectionId = currentRoleSectionId(sectionOptions, line);

  useEffect(() => {
    void saveSession(engine.position().index);
  }, []);

  useEffect(() => {
    return () => {
      voiceActivityDetector?.stop();
    };
  }, [voiceActivityDetector]);

  useEffect(() => {
    void loadLastTimingAttempt();
    void loadCurrentBookmark();
  }, [line?.id]);

  useEffect(() => {
    void loadBookmarks();
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const shortcut = shortcutForKey(event);
      if (!shortcut) {
        return;
      }
      event.preventDefault();
      void runCommand(commandForShortcut(shortcut));
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  function commandForShortcut(shortcut: RehearsalShortcut): RehearsalCommand {
    if (shortcut !== "toggle-playback") {
      return shortcut;
    }

    if (playbackState === "playing") {
      return "pause";
    }
    if (playbackState === "paused") {
      return "resume";
    }
    return "repeat-cue";
  }

  async function runCommand(command: RehearsalCommand) {
    switch (command) {
      case "next":
        if (!engine.position().atEnd) {
          await goNext();
        }
        return;
      case "back":
        if (!engine.position().atBeginning) {
          await goPrevious();
        }
        return;
      case "repeat-cue":
        await playCue();
        return;
      case "hear-line":
        await playResponse();
        return;
      case "pause":
        pausePlayback();
        return;
      case "resume":
        resumePlayback();
        return;
      case "stop":
        stopPlayback();
        return;
      case "bookmark":
        await toggleBookmark();
        return;
      case "start-timing":
        beginTimedAttempt();
        return;
    }
  }

  async function goNext() {
    engine.next();
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
    if (hasStarted) {
      await playCue();
    }
  }

  async function jumpToLine(lineId: string) {
    const targetLine = role.lines.find((candidate) => candidate.id === lineId);
    if (!targetLine) {
      throw new Error(`Line not found for role ${role.id}: ${lineId}`);
    }
    while (engine.currentLine()?.id !== lineId && !engine.position().atEnd) {
      engine.next();
    }
    while (engine.currentLine()?.id !== lineId && !engine.position().atBeginning) {
      engine.previous();
    }
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
    setActiveUtilityPanel(null);
  }

  async function jumpToSection(sectionId: string) {
    const section = sectionOptions.find((candidate) => candidate.id === sectionId);
    if (!section) {
      throw new Error(`Section not found for role ${role.id}: ${sectionId}`);
    }
    await jumpToLine(section.startLineId);
  }

  async function goPrevious() {
    engine.previous();
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
    if (hasStarted) {
      await playCue();
    }
  }

  function updatePosition(options: { revealLine?: boolean } = {}) {
    const nextPosition = engine.position();
    const nextRevealLine = options.revealLine ?? isLineRevealed;
    setPosition(nextPosition);
    setTempoFeedback(null);
    void saveSession(
      nextPosition.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      nextRevealLine
    );
  }

  async function saveSession(
    lineIndex: number,
    nextPlaybackRate = playbackRate,
    nextSpeakAlongEnabled = speakAlongEnabled,
    nextTempoTimingPreferred = tempoTimingPreferred,
    nextRevealLine = isLineRevealed,
    nextCueWindowPresetId = cueWindowPresetId,
    nextIncludeDirections = includeDirections,
    nextShowLinesByDefault = showLinesByDefault,
    nextSpeakAlongPauseMs = speakAlongPauseMs,
    nextTempoTargetHesitationMs = tempoTargetHesitationMs,
    nextSyncPracticeTiming = syncPracticeTiming,
    nextIncludeBlocking = includeBlocking,
    nextBlockingScope = blockingScope
  ) {
    try {
      await indexedDbStorage.sessions.save({
        playbookId: playbook.id,
        roleId: role.id,
        lineIndex,
        cueDepth: 1,
        includeDirections: nextIncludeDirections,
        includeBlocking: nextIncludeBlocking,
        blockingScope: nextBlockingScope,
        revealLine: nextRevealLine,
        showLinesByDefault: nextShowLinesByDefault,
        cueWindowPresetId: nextCueWindowPresetId,
        playbackRate: nextPlaybackRate,
        speakAlongEnabled: nextSpeakAlongEnabled,
        speakAlongPauseMs: nextSpeakAlongPauseMs,
        tempoTargetHesitationMs: nextTempoTargetHesitationMs,
        syncPracticeTiming: nextSyncPracticeTiming,
        tempoTimingPreferred: nextTempoTimingPreferred,
        updatedAt: Date.now()
      });
      setStorageStatus("");
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function playCue() {
    const currentLine = engine.currentLine();
    setHasStarted(true);
    setPlaybackStatus(speakAlongEnabled ? "Speak along: playing cue, then your line..." : "Playing cue...");
    setPlaybackState("playing");
    try {
      if (speakAlongEnabled && currentLine) {
        await audioQueue.play(
          speakAlongPlaybackItems(
            engine.cuePayloads(cueWindowPresetId),
            currentLine,
            playbackRate,
            cueWindowPresetId,
            speakAlongPauseMs
          )
        );
        setPlaybackStatus("Speak-along complete.");
      } else {
        await audioQueue.play(cuePlaybackItems(engine.cuePayloads(cueWindowPresetId), cueWindowPresetId));
        setPlaybackStatus("Cue complete.");
      }
      setPlaybackState("idle");
      if (!speakAlongEnabled) {
        beginTimedAttempt();
      }
    } catch (error) {
      setPlaybackState("idle");
      setPlaybackStatus(userFacingErrorMessage(error));
    }
  }

  async function playResponse() {
    if (!line) {
      return;
    }
    setPlaybackStatus("Playing your line...");
    setPlaybackState("playing");
    try {
      await audioQueue.play(responsePlaybackItems(line, playbackRate));
      setPlaybackStatus("Line complete.");
      setPlaybackState("idle");
    } catch (error) {
      setPlaybackState("idle");
      setPlaybackStatus(userFacingErrorMessage(error));
    }
  }

  function pausePlayback() {
    if (playbackState !== "playing") {
      return;
    }
    audioQueue.pause();
    setPlaybackState("paused");
    setPlaybackStatus("Playback paused.");
  }

  function resumePlayback() {
    if (playbackState !== "paused") {
      return;
    }
    audioQueue.resume();
    setPlaybackState("playing");
    setPlaybackStatus("Playback resumed.");
  }

  function stopPlayback() {
    audioQueue.cancel();
    setPlaybackState("idle");
    setPlaybackStatus("Playback stopped.");
    setTempoStatus(tempoTimingEnabled ? "Tempo timing is idle." : tempoStatus);
  }

  function changePlaybackRate(nextPlaybackRate: number) {
    const clampedPlaybackRate = clampPlaybackRate(nextPlaybackRate);
    setPlaybackRate(clampedPlaybackRate);
    void saveSession(position.index, clampedPlaybackRate);
  }

  function changeCueWindowPreset(nextCueWindowPresetId: string) {
    const preset = cueWindowPresetForId(nextCueWindowPresetId);
    setCueWindowPresetId(preset.id);
    void saveSession(position.index, playbackRate, speakAlongEnabled, tempoTimingPreferred, isLineRevealed, preset.id);
  }

  function changeSpeakAlongPauseMs(nextPauseMs: number) {
    setSpeakAlongPauseMs(nextPauseMs);
    const nextTempoTargetMs = syncPracticeTiming ? nextPauseMs : tempoTargetHesitationMs;
    if (syncPracticeTiming) {
      setTempoTargetHesitationMs(nextTempoTargetMs);
    }
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      includeDirections,
      showLinesByDefault,
      nextPauseMs,
      nextTempoTargetMs
    );
  }

  function changeTempoTargetHesitationMs(nextTargetMs: number) {
    setTempoTargetHesitationMs(nextTargetMs);
    const nextSpeakAlongPauseMs = syncPracticeTiming ? nextTargetMs : speakAlongPauseMs;
    if (syncPracticeTiming) {
      setSpeakAlongPauseMs(nextSpeakAlongPauseMs);
    }
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      includeDirections,
      showLinesByDefault,
      nextSpeakAlongPauseMs,
      nextTargetMs
    );
  }

  function changeSyncPracticeTiming(nextSyncPracticeTiming: boolean) {
    setSyncPracticeTiming(nextSyncPracticeTiming);
    const nextTempoTargetMs = nextSyncPracticeTiming ? speakAlongPauseMs : tempoTargetHesitationMs;
    if (nextSyncPracticeTiming) {
      setTempoTargetHesitationMs(nextTempoTargetMs);
    }
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      includeDirections,
      showLinesByDefault,
      speakAlongPauseMs,
      nextTempoTargetMs,
      nextSyncPracticeTiming
    );
  }

  function toggleLineReveal() {
    const nextRevealLine = !isLineRevealed;
    setIsLineRevealed(nextRevealLine);
    void saveSession(position.index, playbackRate, speakAlongEnabled, tempoTimingPreferred, nextRevealLine);
  }

  function changeShowLinesByDefault(nextShowLinesByDefault: boolean) {
    setShowLinesByDefault(nextShowLinesByDefault);
    setIsLineRevealed(nextShowLinesByDefault);
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      nextShowLinesByDefault,
      cueWindowPresetId,
      includeDirections,
      nextShowLinesByDefault
    );
  }

  function changeIncludeDirections(nextIncludeDirections: boolean) {
    engine.setIncludeDirections(nextIncludeDirections);
    setIncludeDirections(nextIncludeDirections);
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      nextIncludeDirections
    );
  }

  function changeIncludeBlocking(nextIncludeBlocking: boolean) {
    setIncludeBlocking(nextIncludeBlocking);
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      includeDirections,
      showLinesByDefault,
      speakAlongPauseMs,
      tempoTargetHesitationMs,
      syncPracticeTiming,
      nextIncludeBlocking
    );
  }

  function changeBlockingScope(nextBlockingScope: BlockingScope) {
    setBlockingScope(nextBlockingScope);
    void saveSession(
      position.index,
      playbackRate,
      speakAlongEnabled,
      tempoTimingPreferred,
      isLineRevealed,
      cueWindowPresetId,
      includeDirections,
      showLinesByDefault,
      speakAlongPauseMs,
      tempoTargetHesitationMs,
      syncPracticeTiming,
      includeBlocking,
      nextBlockingScope
    );
  }

  function changeSpeakAlongEnabled(nextSpeakAlongEnabled: boolean) {
    setSpeakAlongEnabled(nextSpeakAlongEnabled);
    if (nextSpeakAlongEnabled && tempoTimingEnabled) {
      void disableTempoTiming("Tempo timing disabled while speak-along practice is enabled.");
    }
    if (nextSpeakAlongEnabled) {
      setTempoTimingPreferred(false);
    }
    void saveSession(position.index, playbackRate, nextSpeakAlongEnabled, nextSpeakAlongEnabled ? false : tempoTimingPreferred);
  }

  async function enableTempoTiming() {
    setTempoStatus("Requesting microphone permission...");
    const detector = new VoiceActivityDetector(handleVoiceActivity);

    try {
      await detector.start();
      voiceActivityDetector?.stop();
      setVoiceActivityDetector(detector);
      setTempoTimingEnabled(true);
      setTempoTimingPreferred(true);
      setSpeakAlongEnabled(false);
      setTempoStatus("Tempo timing enabled. Press Start or Repeat Cue to time an attempt.");
      await saveSession(position.index, playbackRate, false, true);
    } catch (error) {
      detector.stop();
      setTempoTimingEnabled(false);
      setTempoStatus(userFacingErrorMessage(error));
    }
  }

  async function disableTempoTiming(message = "Tempo timing disabled."): Promise<void> {
    voiceActivityDetector?.stop();
    setVoiceActivityDetector(null);
    setTempoTimingEnabled(false);
    setTempoTimingPreferred(false);
    setTempoStatus(message);
    await saveSession(position.index, playbackRate, speakAlongEnabled, false);
  }

  function beginTimedAttempt() {
    if (!tempoTimingEnabled || !voiceActivityDetector) {
      return;
    }
    setTempoFeedback(null);
    setTempoStatus("Listening for your pickup...");
    voiceActivityDetector.beginAttempt();
  }

  function handleVoiceActivity(result: VoiceActivityResult) {
    if (!line) {
      return;
    }
    if (result.event === "speech-started") {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      setTempoStatus(`Pickup detected after ${hesitationMs} ms. Continue speaking; pause when finished.`);
    } else {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      const deliveryMs = Math.round(result.deliveryMs ?? 0);
      const feedback = tempoFeedbackFor(line, { hesitationMs, deliveryMs }, tempoTargetHesitationMs);
      setTempoFeedback(feedback);
      void saveTimingAttempt(line.id, feedback);
      setTempoStatus("Timed attempt complete.");
    }
  }

  async function saveTimingAttempt(lineId: string, feedback: TempoFeedback) {
    if (!feedback.delivery) {
      return;
    }
    const attempt: TimingAttempt = {
      id: crypto.randomUUID(),
      playbookId: playbook.id,
      roleId: role.id,
      lineId,
      createdAt: Date.now(),
      hesitationMs: feedback.hesitation.measuredMs,
      deliveryMs: feedback.delivery.measuredMs,
      targetHesitationMs: feedback.hesitation.targetMs,
      targetDeliveryMs: feedback.delivery.targetMs,
      hesitationLabel: feedback.hesitation.label,
      deliveryLabel: feedback.delivery.label,
      detectionMode: "energy"
    };
    try {
      await indexedDbStorage.timingAttempts.save(attempt);
      setStorageStatus("");
      setLastTimingAttempt(attempt);
      await loadRecentTimingAttempts();
      await loadReviewAttempts();
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadLastTimingAttempt() {
    if (!line) {
      setLastTimingAttempt(null);
      return;
    }
    try {
      setLastTimingAttempt((await indexedDbStorage.timingAttempts.latestForLine(playbook.id, role.id, line.id)) ?? null);
      await loadRecentTimingAttempts();
    } catch (error) {
      setLastTimingAttempt(null);
      setRecentTimingAttempts([]);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadRecentTimingAttempts() {
    if (!line) {
      setRecentTimingAttempts([]);
      return;
    }
    try {
      setRecentTimingAttempts(await indexedDbStorage.timingAttempts.recentForLine(playbook.id, role.id, line.id, 5));
    } catch (error) {
      setRecentTimingAttempts([]);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadReviewAttempts() {
    try {
      setReviewAttempts(await indexedDbStorage.timingAttempts.latestForRole(playbook.id, role.id));
    } catch (error) {
      setReviewAttempts([]);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadCurrentBookmark() {
    if (!line) {
      setIsCurrentLineBookmarked(false);
      return;
    }
    try {
      setIsCurrentLineBookmarked(Boolean(await indexedDbStorage.bookmarks.get(playbook.id, role.id, line.id)));
    } catch (error) {
      setIsCurrentLineBookmarked(false);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadBookmarks() {
    try {
      setBookmarks(await indexedDbStorage.bookmarks.listForRole(playbook.id, role.id));
    } catch (error) {
      setBookmarks([]);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function toggleBookmark() {
    if (!line) {
      return;
    }
    try {
      if (isCurrentLineBookmarked) {
        await indexedDbStorage.bookmarks.delete(playbook.id, role.id, line.id);
        setIsCurrentLineBookmarked(false);
      } else {
        await indexedDbStorage.bookmarks.save({
          id: `${playbook.id}:${role.id}:${line.id}`,
          playbookId: playbook.id,
          roleId: role.id,
          lineId: line.id,
          createdAt: Date.now()
        });
        setIsCurrentLineBookmarked(true);
      }
      setStorageStatus("");
      await loadBookmarks();
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function showUtilityPanel(panel: UtilityPanel) {
    const nextPanel = activeUtilityPanel === panel ? null : panel;
    setActiveUtilityPanel(nextPanel);
    if (nextPanel === "timing") {
      await loadReviewAttempts();
    }
  }

  return (
    <main className="shell">
      <section className="hero rehearsal">
        <header className="rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary"
              aria-label="Back to roles."
              data-tooltip="Back to roles"
              onClick={onBack}
            >
              <span aria-hidden="true">←</span>
            </button>
            <p className="breadcrumb">
              {playbook.title} / {role.displayName}
            </p>
          </div>
          <p className="line-position">{line ? line.id : "No lines"}</p>
        </header>
        {storageStatus ? (
          <p className="error" role="alert">
            {storageStatus}
          </p>
        ) : null}

        {line ? (
          <div className="rehearsal-line-layout">
            <section className="cue-strip" aria-label="Cue">
              <div className="cue-strip-cards">
                {cues.map((cue, index) => (
                  <CueCard cue={cue} key={`${line.id}-cue-${index}`} />
                ))}
              </div>
            </section>

            <section className="stack" aria-label="Your Line">
              <div className="line-heading">
                <h2>Your Line</h2>
                <div className="transport inline-transport">
                  <div className="transport-group" aria-label="Playback controls">
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label="Go to previous line. Shortcut: Left arrow."
                      data-tooltip="Previous line"
                      disabled={position.atBeginning}
                      onClick={() => void runCommand("back")}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        ⏮
                      </span>
                    </button>
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label={`${hasStarted ? "Repeat cue" : "Start cue"}. Shortcut: Space or R.`}
                      data-tooltip={`${hasStarted ? "Repeat cue" : "Start cue"}`}
                      onClick={() => void runCommand("repeat-cue")}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        {hasStarted ? "↻" : "▶"}
                      </span>
                    </button>
                    {playbackState === "paused" ? (
                      <button
                        type="button"
                        className="transport-button secondary"
                        aria-label="Resume playback. Shortcut: Space."
                        data-tooltip="Resume"
                        onClick={() => void runCommand("resume")}
                      >
                        <span aria-hidden="true" className="transport-icon">
                          ▶
                        </span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="transport-button secondary"
                        aria-label="Pause playback. Shortcut: Space."
                        data-tooltip="Pause"
                        disabled={playbackState !== "playing"}
                        onClick={() => void runCommand("pause")}
                      >
                        <span aria-hidden="true" className="transport-icon">
                          ⏸
                        </span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label="Stop playback. Shortcut: Escape."
                      data-tooltip="Stop"
                      onClick={() => void runCommand("stop")}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        ■
                      </span>
                    </button>
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label="Go to next line. Shortcut: Right arrow."
                      data-tooltip="Next line"
                      disabled={position.atEnd}
                      onClick={() => void runCommand("next")}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        ⏭
                      </span>
                    </button>
                  </div>
                  <div className="transport-group secondary-actions" aria-label="Line controls">
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label={isCurrentLineBookmarked ? "Remove bookmark from current line." : "Bookmark current line."}
                      data-tooltip={isCurrentLineBookmarked ? "Remove bookmark" : "Bookmark"}
                      disabled={!line}
                      onClick={() => void runCommand("bookmark")}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        {isCurrentLineBookmarked ? "★" : "☆"}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="transport-button secondary"
                      aria-label="Hear your line. Shortcut: L."
                      data-tooltip="Hear line"
                      onClick={() => void runCommand("hear-line")}
                      disabled={!line}
                    >
                      <span aria-hidden="true" className="transport-icon">
                        ♫
                      </span>
                    </button>
                  </div>
                </div>
                <label className="line-visibility-toggle">
                  <input
                    type="checkbox"
                    checked={isLineRevealed}
                    disabled={!line}
                    onChange={toggleLineReveal}
                  />
                  Show my line
                </label>
              </div>
              {isLineRevealed ? (
                <LineCard
                  line={line}
                  includeDirections={includeDirections}
                  includeBlocking={includeBlocking}
                  blockingScope={blockingScope}
                />
              ) : (
                <article className="card hidden-line">Line hidden</article>
              )}
            </section>
          </div>
        ) : (
          <p className="empty">This role has no rehearsable lines.</p>
        )}

        <div className="session-settings">
          <label className="section-jumper">
            Jump to
            <select
              value={currentSectionId}
              disabled={sectionOptions.length === 0}
              onChange={(event) => void jumpToSection(event.target.value)}
            >
              {sectionOptions.map((section) => (
                <option key={section.id} value={section.id}>
                  {section.title}
                </option>
              ))}
            </select>
          </label>
          {tempoStatus ? (
            <p className="status" aria-live="polite">
              {tempoStatus}
            </p>
          ) : null}
          {tempoFeedback ? <TempoFeedbackPanel feedback={tempoFeedback} /> : null}
          {!tempoFeedback && lastTimingAttempt ? <TimingAttemptPanel attempt={lastTimingAttempt} /> : null}
          {recentTimingAttempts.length > 1 ? <RecentAttemptsPanel attempts={recentTimingAttempts} /> : null}
          {playbackStatus ? (
            <p className="status" aria-live="polite">
              {playbackStatus}
            </p>
          ) : null}
          <div className="utility-drawer">
            <div className="utility-tabs" aria-label="Rehearsal utilities">
              <button
                type="button"
                className={activeUtilityPanel === "script" ? "utility-tab active" : "utility-tab"}
                aria-pressed={activeUtilityPanel === "script"}
                onClick={() => void showUtilityPanel("script")}
              >
                <span aria-hidden="true">▤</span>
                Script
              </button>
              <button
                type="button"
                className={activeUtilityPanel === "bookmarks" ? "utility-tab active" : "utility-tab"}
                aria-pressed={activeUtilityPanel === "bookmarks"}
                onClick={() => void showUtilityPanel("bookmarks")}
              >
                <span aria-hidden="true">★</span>
                Bookmarks
              </button>
              <button
                type="button"
                className={activeUtilityPanel === "timing" ? "utility-tab active" : "utility-tab"}
                aria-pressed={activeUtilityPanel === "timing"}
                onClick={() => void showUtilityPanel("timing")}
              >
                <span aria-hidden="true">⏱</span>
                Timing Issues
              </button>
              <button
                type="button"
                className={activeUtilityPanel === "options" ? "utility-tab active" : "utility-tab"}
                aria-pressed={activeUtilityPanel === "options"}
                onClick={() => void showUtilityPanel("options")}
              >
                <span aria-hidden="true">⚙</span>
                Options
              </button>
            </div>
            {activeUtilityPanel ? (
              <div className="utility-content">
                {activeUtilityPanel === "options" ? (
                  <div className="practice-options-panel">
                    <label className="timing-setting">
                      Cue length
                      <select value={cueWindowPresetId} onChange={(event) => changeCueWindowPreset(event.target.value)}>
                        {cueWindowPresets.map((preset) => (
                          <option key={preset.id} value={preset.id}>
                            {preset.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="timing-setting">
                      Response speed
                      <select
                        value={playbackRate}
                        onChange={(event) => changePlaybackRate(Number(event.target.value))}
                      >
                        {playbackRates.map((rate) => (
                          <option key={rate} value={rate}>
                            {rate.toFixed(1)}x
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="check-setting">
                      <input
                        type="checkbox"
                        checked={speakAlongEnabled}
                        disabled={tempoTimingEnabled}
                        onChange={(event) => changeSpeakAlongEnabled(event.target.checked)}
                      />
                      Speak-along practice
                    </label>
                    <label className="check-setting">
                      <input
                        type="checkbox"
                        checked={includeDirections}
                        onChange={(event) => changeIncludeDirections(event.target.checked)}
                      />
                      Show stage directions
                    </label>
                    <label className="check-setting">
                      <input
                        type="checkbox"
                        checked={includeBlocking}
                        onChange={(event) => changeIncludeBlocking(event.target.checked)}
                      />
                      Show blocking
                    </label>
                    <label className="timing-setting">
                      Blocking scope
                      <select
                        value={blockingScope}
                        disabled={!includeBlocking}
                        onChange={(event) => changeBlockingScope(event.target.value as BlockingScope)}
                      >
                        <option value="role">My role</option>
                        <option value="all">All roles</option>
                      </select>
                    </label>
                    <label className="check-setting">
                      <input
                        type="checkbox"
                        checked={showLinesByDefault}
                        onChange={(event) => changeShowLinesByDefault(event.target.checked)}
                      />
                      Show lines by default
                    </label>
                    <label className="check-setting">
                      <input
                        type="checkbox"
                        checked={tempoTimingEnabled}
                        onChange={(event) => {
                          if (event.target.checked) {
                            void enableTempoTiming();
                          } else {
                            void disableTempoTiming();
                          }
                        }}
                      />
                      Enable Tempo Timing
                    </label>
                    <fieldset className="timing-options">
                      <legend>Timing targets</legend>
                      <div className="timing-options-controls">
                        <label className="timing-setting">
                          Speak-along pause
                          <select
                            value={speakAlongPauseMs}
                            onChange={(event) => changeSpeakAlongPauseMs(Number(event.target.value))}
                          >
                            {practiceTimingOptionsMs.map((optionMs) => (
                              <option key={optionMs} value={optionMs}>
                                {formatTimingOption(optionMs)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="timing-setting">
                          Tempo pickup target
                          <select
                            value={tempoTargetHesitationMs}
                            disabled={syncPracticeTiming}
                            onChange={(event) => changeTempoTargetHesitationMs(Number(event.target.value))}
                          >
                            {practiceTimingOptionsMs.map((optionMs) => (
                              <option key={optionMs} value={optionMs}>
                                {formatTimingOption(optionMs)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="check-setting timing-sync">
                          <input
                            type="checkbox"
                            checked={syncPracticeTiming}
                            onChange={(event) => changeSyncPracticeTiming(event.target.checked)}
                          />
                          Keep timing targets in sync
                        </label>
                      </div>
                    </fieldset>
                    <p className="status">
                      Tempo timing uses microphone energy only: no recording, no transcription, no upload.
                    </p>
                  </div>
                ) : null}
                {activeUtilityPanel === "script" ? (
                  <ScriptBrowserPanel
                    currentLineId={line?.id ?? null}
                    includeBlocking={includeBlocking}
                    blockingScope={blockingScope}
                    includeDirections={includeDirections}
                    lines={role.lines}
                    sections={playbook.sections}
                    onSelectLine={(lineId) => void jumpToLine(lineId)}
                  />
                ) : null}
                {activeUtilityPanel === "bookmarks" ? (
                  <BookmarksPanel bookmarks={bookmarks} role={role} onSelectLine={(lineId) => void jumpToLine(lineId)} />
                ) : null}
                {activeUtilityPanel === "timing" ? (
                  <TimingIssuesPanel
                    attempts={reviewAttempts}
                    role={role}
                    onSelectLine={(lineId) => void jumpToLine(lineId)}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}

function ScriptBrowserPanel({
  currentLineId,
  includeBlocking,
  blockingScope,
  includeDirections,
  lines,
  sections,
  onSelectLine
}: {
  currentLineId: string | null;
  includeBlocking: boolean;
  blockingScope: BlockingScope;
  includeDirections: boolean;
  lines: Line[];
  sections: Playbook["sections"];
  onSelectLine: (lineId: string) => void;
}) {
  const currentLineRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    currentLineRef.current?.scrollIntoView({ block: "center" });
  }, [currentLineId]);

  return (
    <div className="script-browser">
      <h2>Script</h2>
      {scriptBrowserSections(lines, sections).map((section) => (
        <section key={section.id}>
          <h3>{section.title}</h3>
          <ol>
            {section.lines.map((line) => (
              <li
                key={line.id}
                className={line.id === currentLineId ? "current-script-line" : undefined}
                ref={line.id === currentLineId ? currentLineRef : undefined}
              >
                <button type="button" className="secondary" onClick={() => onSelectLine(line.id)}>
                  <strong>{line.id}</strong>
                  <span>{line.speaker}</span>
                  {includeDirections && line.directions.length > 0 ? (
                    <small>{line.directions.map((direction) => direction.text).join(" ")}</small>
                  ) : null}
                  {includeBlocking && visibleBlockingForLine(line, blockingScope).length > 0 ? (
                    <small>
                      {visibleBlockingForLine(line, blockingScope)
                        .map((blocking) => `${blocking.targets.join(", ")}: ${blocking.text}`)
                        .join(" ")}
                    </small>
                  ) : null}
                  {line.responseText.slice(0, 120)}
                </button>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function visibleBlockingForLine(line: Line, blockingScope: BlockingScope) {
  return (line.blocking ?? []).filter(
    (blocking) => blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role)
  );
}

function TempoFeedbackPanel({ feedback }: { feedback: TempoFeedback }) {
  return (
    <div className="tempo-feedback">
      <p>
        Pickup: {feedback.hesitation.measuredMs} ms target {feedback.hesitation.targetMs} ms,{" "}
        {feedback.hesitation.label}.
      </p>
      {feedback.delivery ? (
        <p>
          Delivery: {feedback.delivery.measuredMs} ms target {feedback.delivery.targetMs} ms,{" "}
          {feedback.delivery.label}.
        </p>
      ) : null}
    </div>
  );
}

function TimingAttemptPanel({ attempt }: { attempt: TimingAttempt }) {
  return (
    <div className="tempo-feedback">
      <p>Last attempt:</p>
      <p>
        Pickup: {attempt.hesitationMs} ms target {attempt.targetHesitationMs} ms, {attempt.hesitationLabel}.
      </p>
      <p>
        Delivery: {attempt.deliveryMs} ms target {attempt.targetDeliveryMs} ms, {attempt.deliveryLabel}.
      </p>
    </div>
  );
}

function RecentAttemptsPanel({ attempts }: { attempts: TimingAttempt[] }) {
  return (
    <div className="tempo-feedback">
      <p>Recent attempts:</p>
      <ol className="attempt-list">
        {attempts.map((attempt) => (
          <li key={attempt.id}>
            pickup {attempt.hesitationMs} ms ({attempt.hesitationLabel}), delivery {attempt.deliveryMs} ms (
            {attempt.deliveryLabel})
          </li>
        ))}
      </ol>
    </div>
  );
}

function BookmarksPanel({
  bookmarks,
  role,
  onSelectLine
}: {
  bookmarks: Bookmark[];
  role: Role;
  onSelectLine: (lineId: string) => void;
}) {
  const linesById = new Map(role.lines.map((line) => [line.id, line]));

  return (
    <div className="review-panel">
      <h2>Bookmarks</h2>
      <BookmarkReviewSection bookmarks={bookmarks} linesById={linesById} onSelectLine={onSelectLine} />
    </div>
  );
}

function TimingIssuesPanel({
  attempts,
  role,
  onSelectLine
}: {
  attempts: TimingAttempt[];
  role: Role;
  onSelectLine: (lineId: string) => void;
}) {
  const linesById = new Map(role.lines.map((line) => [line.id, line]));
  const latePickupAttempts = attempts.filter((attempt) => attempt.hesitationLabel === "late");
  const slowDeliveryAttempts = attempts.filter((attempt) => attempt.deliveryLabel === "slow");
  const rushedDeliveryAttempts = attempts.filter((attempt) => attempt.deliveryLabel === "fast");

  return (
    <div className="review-panel">
      <h2>Timing Issues</h2>
      <div className="timing-review-grid">
        <TimingReviewSection title="Late Pickup" attempts={latePickupAttempts} linesById={linesById} onSelectLine={onSelectLine} />
        <TimingReviewSection title="Slow Delivery" attempts={slowDeliveryAttempts} linesById={linesById} onSelectLine={onSelectLine} />
        <TimingReviewSection title="Rushed Delivery" attempts={rushedDeliveryAttempts} linesById={linesById} onSelectLine={onSelectLine} />
      </div>
      {attempts.length === 0 ? <p className="empty">No timing attempts yet.</p> : null}
    </div>
  );
}

function TimingReviewSection({
  title,
  attempts,
  linesById,
  onSelectLine
}: {
  title: string;
  attempts: TimingAttempt[];
  linesById: Map<string, Line>;
  onSelectLine: (lineId: string) => void;
}) {
  return (
    <section>
      <h3>{title}</h3>
      {attempts.length === 0 ? (
        <p className="empty">None.</p>
      ) : (
        <ul>
          {attempts.map((attempt) => (
            <li key={attempt.id}>
              <button type="button" className="secondary" onClick={() => onSelectLine(attempt.lineId)}>
                {attempt.lineId} {linesById.get(attempt.lineId)?.responseText.slice(0, 80) ?? ""}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function BookmarkReviewSection({
  bookmarks,
  linesById,
  onSelectLine
}: {
  bookmarks: Bookmark[];
  linesById: Map<string, Line>;
  onSelectLine: (lineId: string) => void;
}) {
  return (
    <>
      {bookmarks.length === 0 ? (
        <p className="empty">None.</p>
      ) : (
        <ul>
          {bookmarks.map((bookmark) => (
            <li key={bookmark.id}>
              <button type="button" className="secondary" onClick={() => onSelectLine(bookmark.lineId)}>
                {bookmark.lineId} {linesById.get(bookmark.lineId)?.responseText.slice(0, 80) ?? ""}
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function currentRoleSectionId(
  sections: Array<{ id: string; partId: number | null }>,
  line: Line | null
): string {
  if (!line || sections.length === 0) {
    return "";
  }
  return sections.find((section) => section.partId === line.partId)?.id ?? sections[0].id;
}

const minPlaybackRate = 0.4;
const maxPlaybackRate = 1.3;
const playbackRates = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];
const practiceTimingOptionsMs = [250, 500, 750, 1000, 1250, 1500, 2000];

function formatTimingOption(optionMs: number): string {
  return `${(optionMs / 1000).toFixed(optionMs % 1000 === 0 ? 0 : 2)}s`;
}

export function clampPlaybackRate(playbackRate: number): number {
  const roundedPlaybackRate = Math.round(playbackRate * 10) / 10;
  return Math.min(maxPlaybackRate, Math.max(minPlaybackRate, roundedPlaybackRate));
}
