import { useEffect, useMemo, useRef, useId, useState } from "react";
import type { Bookmark } from "../../domain/bookmark";
import type { ContextBlock } from "../../domain/context";
import type { Cue } from "../../domain/cue";
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
import { scriptBrowserSections } from "../../rehearsal/scriptBrowser";
import { deliveryLabel, tempoFeedbackFor } from "../../rehearsal/tempoFeedback";
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
  onSelectRole: () => void;
};

type PlaybackUiState = "idle" | "playing" | "paused";
type PlaybackSource = "cue" | "line";
type OutlineMode = "cues" | "lines";
type TimingLineStatus = "untimed" | "slow" | "fast" | "good";
type TimingLabel = "fast" | "slow" | "good";
type TimingPill = "delivery" | "pickup";
type TimingStatusPill = {
  delivery: {
    label: TimingLabel;
    measuredMs: number;
    targetMs: number;
  };
  pickup: {
    label: TimingLabel;
    measuredMs: number;
    targetMs: number;
  };
  details: string;
};

type PracticeSelectOption = {
  value: string;
  label: string;
};

function PracticeSelect({
  label,
  value,
  options,
  onSelect,
  disabled = false
}: {
  label: string;
  value: string;
  options: PracticeSelectOption[];
  onSelect: (nextValue: string) => void;
  disabled?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement | null>(null);
  const selectId = useId();

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (!selectRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!disabled) {
      return;
    }
    setIsOpen(false);
  }, [disabled]);

  const selectedLabel = options.find((option) => option.value === value)?.label ?? value;

  return (
    <div className="practice-select-wrap" ref={selectRef}>
      <button
        type="button"
        className="practice-select-trigger"
        aria-label={label}
        aria-expanded={isOpen}
        aria-controls={`${selectId}-options`}
        onClick={() => setIsOpen((current) => !current)}
        disabled={disabled}
      >
        <span>{selectedLabel}</span>
        <span className="practice-select-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      <div id={`${selectId}-options`} role="listbox" className={`practice-select-options ${isOpen ? "open" : ""}`} aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="option"
            aria-selected={option.value === value}
            className={option.value === value ? "practice-select-option active" : "practice-select-option"}
            onClick={() => {
              onSelect(option.value);
              setIsOpen(false);
            }}
            disabled={disabled}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function RehearsalScreen({
  playbook,
  role,
  initialSession,
  initialStorageStatus = "",
  onBack,
  onSelectRole
}: RehearsalScreenProps) {
  const [engine] = useState(() =>
    RehearsalEngine.forRole(playbook, role.id, {
      startLineId: role.lines[initialSession?.lineIndex ?? 0]?.id,
      includeDirections: initialSession?.includeDirections
    })
  );
  const [activeLineId, setActiveLineId] = useState(() => {
    const startLine = role.lines[engine.position().index];
    return startLine ? startLine.id : null;
  });
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [position, setPosition] = useState(() => engine.position());
  const [playbackRate, setPlaybackRate] = useState(clampPlaybackRate(initialSession?.playbackRate ?? 1));
  const [cueWindowPresetId, setCueWindowPresetId] = useState(
    cueWindowPresetForId(initialSession?.cueWindowPresetId).id
  );
  const [playbackState, setPlaybackState] = useState<PlaybackUiState>("idle");
  const [playbackSource, setPlaybackSource] = useState<PlaybackSource | null>(null);
  const [playbackStatus, setPlaybackStatus] = useState<string>("");
  const [timingStatusMessage, setTimingStatusMessage] = useState<TimingStatusPill | null>(null);
  const [expandedTimingPill, setExpandedTimingPill] = useState<TimingPill | null>(null);
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
  const [practiceTargetPaceMultiplier, setPracticeTargetPaceMultiplier] = useState(
    normalizePracticeTargetPaceMultiplier(initialSession?.practiceTargetPaceMultiplier)
  );
  const [tempoTargetHesitationMs, setTempoTargetHesitationMs] = useState(
    initialSession?.tempoTargetHesitationMs ?? initialSession?.speakAlongPauseMs ?? defaultTargetHesitationMs
  );
  const [syncPracticeTiming, setSyncPracticeTiming] = useState(initialSession?.syncPracticeTiming ?? true);
  const [tempoTimingEnabled, setTempoTimingEnabled] = useState(initialSession?.tempoTimingPreferred ?? false);
  const [tempoTimingPreferred, setTempoTimingPreferred] = useState(initialSession?.tempoTimingPreferred ?? false);
  const [reviewAttempts, setReviewAttempts] = useState<TimingAttempt[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [storageStatus, setStorageStatus] = useState(initialStorageStatus);
  const [isCurrentLineBookmarked, setIsCurrentLineBookmarked] = useState(false);
  const [showLineInfo, setShowLineInfo] = useState(false);
  const [isOptionsPageVisible, setIsOptionsPageVisible] = useState(false);
  const [isCompactViewport, setIsCompactViewport] = useState(() => isCompactRehearsalViewport());
  const [isOutlineOpen, setIsOutlineOpen] = useState(() => !isCompactRehearsalViewport());
  const [voiceActivityDetector, setVoiceActivityDetector] = useState<VoiceActivityDetector | null>(null);
  const activeTimingLineIdRef = useRef<string | null>(null);
  const tempoTimingRestoreStartedRef = useRef(false);
  const line = useMemo(
    () => role.lines.find((candidate) => candidate.id === activeLineId) ?? null,
    [activeLineId, role.lines]
  );
  const lineLengthMs = useMemo(() => {
    if (!line) {
      return 0;
    }
    return line.responseSegments.reduce((total, segment) => total + segment.durationMs, 0);
  }, [line]);
  const latestLineTimingAttempt = useMemo(
    () => reviewAttempts.find((attempt) => attempt.lineId === line?.id) ?? null,
    [reviewAttempts, line?.id]
  );
  const cues = engine.cuePayloads(cueWindowPresetId);
  const visibleCues = useMemo(
    () => visibleCuesForDisplay(cues, includeDirections, playbook.context, playbook, line),
    [cues, includeDirections, playbook, line]
  );
  const bookmarkedLineIds = useMemo(() => new Set(bookmarks.map((bookmark) => bookmark.lineId)), [bookmarks]);
  const lineTimingStatusByLineId = useMemo(() => {
    const statusByLine = new Map<string, TimingLineStatus>(
      role.lines.map((roleLine) => [roleLine.id, "untimed" as const])
    );
    for (const attempt of reviewAttempts) {
      const attemptDeliveryLabel = deliveryLabel(attempt.deliveryMs, attempt.targetDeliveryMs, practiceTargetPaceMultiplier);
      if (attemptDeliveryLabel === "slow") {
        statusByLine.set(attempt.lineId, "slow");
        continue;
      }
      if (attemptDeliveryLabel === "fast") {
        statusByLine.set(attempt.lineId, "fast");
        continue;
      }
      statusByLine.set(attempt.lineId, "good");
    }
    return statusByLine;
  }, [practiceTargetPaceMultiplier, reviewAttempts, role.lines]);
  const displayedPlaybackStatus = useMemo(() => {
    if (timingStatusMessage) {
      return timingStatusMessage;
    }
    if (!playbackStatus) {
      return null;
    }
    if (/^Line Timed\.?$/i.test(playbackStatus) && latestLineTimingAttempt) {
      return formatTimingAttempt(latestLineTimingAttempt, practiceTargetPaceMultiplier);
    }
    return playbackStatus;
  }, [playbackStatus, latestLineTimingAttempt, practiceTargetPaceMultiplier, timingStatusMessage]);

  useEffect(() => {
    void saveSession(engine.position().index);
  }, []);

  useEffect(() => {
    return () => {
      voiceActivityDetector?.stop();
    };
  }, [voiceActivityDetector]);

  useEffect(() => {
    if (tempoTimingRestoreStartedRef.current || !tempoTimingPreferred || tempoTimingEnabled || speakAlongEnabled) {
      return;
    }
    tempoTimingRestoreStartedRef.current = true;
    void enableTempoTiming();
  }, [tempoTimingPreferred, tempoTimingEnabled, speakAlongEnabled]);

  useEffect(() => {
    if (!timingStatusMessage || !latestLineTimingAttempt) {
      return;
    }
    if (!line || latestLineTimingAttempt.lineId !== line.id) {
      return;
    }
    const nextTimingStatusMessage = formatTimingAttempt(latestLineTimingAttempt, practiceTargetPaceMultiplier);
    setTimingStatusMessage((current) => {
      if (current && current.details === nextTimingStatusMessage.details) {
        return current;
      }
      return nextTimingStatusMessage;
    });
  }, [line?.id, latestLineTimingAttempt, practiceTargetPaceMultiplier, timingStatusMessage]);

  useEffect(() => {
    void loadCurrentBookmark();
  }, [line?.id]);

  useEffect(() => {
    setShowLineInfo(false);
  }, [line?.id]);

  useEffect(() => {
    void loadBookmarks();
    void loadReviewAttempts();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const layoutQuery = window.matchMedia(REHEARSAL_COMPACT_MEDIA_QUERY);

    const handleViewportChange = () => {
      const compactViewport = layoutQuery.matches;
      setIsCompactViewport(compactViewport);
      if (compactViewport) {
        setIsOutlineOpen(false);
      } else {
        setIsOutlineOpen(true);
      }
    };

    handleViewportChange();
    if (typeof layoutQuery.addEventListener === "function") {
      layoutQuery.addEventListener("change", handleViewportChange);
      return () => layoutQuery.removeEventListener("change", handleViewportChange);
    }
    // Safari 13 and earlier support only addListener/removeListener.
    // @ts-expect-error - Safari fallback support for deprecated listener API.
    layoutQuery.addListener(handleViewportChange);
    return () => {
      // @ts-expect-error - Safari fallback support for deprecated listener API.
      layoutQuery.removeListener(handleViewportChange);
    };
  }, []);

  useEffect(() => {
    if (!isCompactViewport || !isOutlineOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isCompactViewport, isOutlineOpen]);

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

  function currentLineFromEngine(): Line | null {
    return resolveCurrentLineFromEngine(role.lines, engine.position().index, engine.currentLine() ?? null);
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
    activeTimingLineIdRef.current = null;
    setTimingStatusMessage(null);
    engine.next();
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
    if (hasStarted) {
      await playCue();
    }
  }

  async function jumpToLine(lineId: string) {
    activeTimingLineIdRef.current = null;
    setTimingStatusMessage(null);
    const targetLine = engine.jumpToLine(lineId);
    if (!targetLine) {
      throw new Error(`Line not found for role ${role.id}: ${lineId}`);
    }
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
  }

  async function jumpFromOutline(lineId: string) {
    await jumpToLine(lineId);
    if (isCompactViewport) {
      setIsOutlineOpen(false);
    }
  }

  async function goPrevious() {
    activeTimingLineIdRef.current = null;
    setTimingStatusMessage(null);
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
    setActiveLineId(nextPosition.index >= 0 && nextPosition.index < role.lines.length ? role.lines[nextPosition.index].id : null);
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
    nextBlockingScope = blockingScope,
    nextPracticeTargetPaceMultiplier = practiceTargetPaceMultiplier
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
        practiceTargetPaceMultiplier: nextPracticeTargetPaceMultiplier,
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
    const currentLine = currentLineFromEngine();
    setHasStarted(true);
    setPlaybackSource("cue");
    setTimingStatusMessage(null);
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
      setPlaybackSource(null);
      if (!speakAlongEnabled) {
        beginTimedAttempt();
      }
    } catch (error) {
      setPlaybackState("idle");
      setPlaybackSource(null);
      setPlaybackStatus(userFacingErrorMessage(error));
    }
  }

  async function playResponse() {
    if (!line) {
      return;
    }
    setPlaybackSource("line");
    setTimingStatusMessage(null);
    setPlaybackStatus("Playing your line...");
    setPlaybackState("playing");
    try {
      await audioQueue.play(responsePlaybackItems(line, playbackRate));
      setPlaybackStatus("Line complete.");
      setPlaybackState("idle");
      setPlaybackSource(null);
    } catch (error) {
      setPlaybackState("idle");
      setPlaybackSource(null);
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
    activeTimingLineIdRef.current = null;
    setTimingStatusMessage(null);
    setPlaybackState("idle");
    setPlaybackSource(null);
    setPlaybackStatus("Playback stopped.");
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

  function changePracticeTargetPaceMultiplier(nextMultiplier: number) {
    const normalizedMultiplier = normalizePracticeTargetPaceMultiplier(nextMultiplier);
    setPracticeTargetPaceMultiplier(normalizedMultiplier);
    if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
      setTimingStatusMessage(formatTimingAttempt(latestLineTimingAttempt, normalizedMultiplier));
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
      tempoTargetHesitationMs,
      syncPracticeTiming,
      includeBlocking,
      blockingScope,
      normalizedMultiplier
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
      void disableTempoTiming();
    }
    if (nextSpeakAlongEnabled) {
      setTempoTimingPreferred(false);
    }
    void saveSession(position.index, playbackRate, nextSpeakAlongEnabled, nextSpeakAlongEnabled ? false : tempoTimingPreferred);
  }

  async function enableTempoTiming() {
    const detector = new VoiceActivityDetector(handleVoiceActivity);

    try {
      await detector.start();
      voiceActivityDetector?.stop();
      setVoiceActivityDetector(detector);
      activeTimingLineIdRef.current = null;
      setTempoTimingEnabled(true);
      setTempoTimingPreferred(true);
      setSpeakAlongEnabled(false);
      await saveSession(position.index, playbackRate, false, true);
    } catch (error) {
      detector.stop();
      setTempoTimingEnabled(false);
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function disableTempoTiming(): Promise<void> {
    voiceActivityDetector?.stop();
    activeTimingLineIdRef.current = null;
    setVoiceActivityDetector(null);
    setTempoTimingEnabled(false);
    setTempoTimingPreferred(false);
    await saveSession(position.index, playbackRate, speakAlongEnabled, false);
  }

  async function beginTimedAttempt() {
    const timingLine = currentLineFromEngine();
    if (!timingLine) {
      return;
    }
    if (!tempoTimingEnabled) {
      setPlaybackStatus("Enable Tempo timing to start timing capture.");
      setTimingStatusMessage(null);
      return;
    }
    let detector = voiceActivityDetector;
    if (!detector) {
      detector = new VoiceActivityDetector(handleVoiceActivity);
      try {
        await detector.start();
      } catch (error) {
        setStorageStatus(userFacingErrorMessage(error));
        return;
      }
      setVoiceActivityDetector(detector);
      // Keep capture running for the remainder of the timing session.
      void saveSession(position.index, playbackRate, speakAlongEnabled, true, isLineRevealed);
    }
    activeTimingLineIdRef.current = timingLine.id;
    setTimingStatusMessage(null);
    setPlaybackStatus("Waiting for your line...");
    detector.beginAttempt();
  }

  function handleVoiceActivity(result: VoiceActivityResult) {
    const timingLineId = activeTimingLineIdRef.current;
    if (!timingLineId) {
      return;
    }
    const timingLine = role.lines.find((candidate) => candidate.id === timingLineId);
    if (!timingLine) {
      activeTimingLineIdRef.current = null;
      return;
    }
    if (result.event === "speech-started") {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      setTimingStatusMessage(null);
      setPlaybackStatus(`Speech detected${hesitationMs > 0 ? ` (${hesitationMs}ms pause)` : ""}.`);
    } else if (result.event === "delivery-ended") {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      const deliveryMs = Math.max(0, Math.round(result.deliveryMs ?? 0));
      const feedback = tempoFeedbackFor(
        timingLine,
        { hesitationMs, deliveryMs },
        tempoTargetHesitationMs,
        practiceTargetPaceMultiplier
      );
      const timingResult = formatTimingResult(feedback, practiceTargetPaceMultiplier);
      setTimingStatusMessage(timingResult);
      setPlaybackStatus(timingResult.details);
      void saveTimingAttempt(timingLine.id, feedback);
      activeTimingLineIdRef.current = null;
    } else {
      return;
    }
  }

  async function saveTimingAttempt(lineId: string, feedback: ReturnType<typeof tempoFeedbackFor>) {
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
      await loadReviewAttempts();
    } catch (error) {
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

  const bookmarkNeighbors = useMemo(() => {
    const lineIndexById = new Map(role.lines.map((playbookLine, index) => [playbookLine.id, index]));
    const orderedBookmarks = bookmarks
      .map((bookmark) => bookmark.lineId)
      .filter((lineId) => lineIndexById.has(lineId))
      .sort((left, right) => (lineIndexById.get(left) ?? 0) - (lineIndexById.get(right) ?? 0));

    if (!line) {
      return { previousLineId: null, nextLineId: null };
    }

    const currentLineIndex = lineIndexById.get(line.id);
    if (currentLineIndex === undefined) {
      return { previousLineId: null, nextLineId: null };
    }

    let previousLineId: string | null = null;
    let nextLineId: string | null = null;
    for (const bookmarkLineId of orderedBookmarks) {
      const bookmarkedLineIndex = lineIndexById.get(bookmarkLineId);
      if (bookmarkedLineIndex === undefined) {
        continue;
      }
      if (bookmarkedLineIndex < currentLineIndex) {
        previousLineId = bookmarkLineId;
      } else if (bookmarkedLineIndex > currentLineIndex && nextLineId === null) {
        nextLineId = bookmarkLineId;
      }
    }

    return { previousLineId, nextLineId };
  }, [bookmarks, line, role.lines]);

  function openOptionsPage() {
    void loadReviewAttempts();
    setIsOptionsPageVisible(true);
  }

  function closeOptionsPage() {
    setIsOptionsPageVisible(false);
  }

  const practiceOptionsPanel = (
    <div className="practice-options-page">
      <div className="practice-options-panel">
        <label className="timing-setting">
          Cue length
          <PracticeSelect
            label="Cue length"
            value={cueWindowPresetId}
            options={cueWindowPresets.map((preset) => ({ value: preset.id, label: preset.label }))}
            onSelect={changeCueWindowPreset}
          />
        </label>
        <label className="timing-setting">
          Speakalong speed
          <PracticeSelect
            label="Response speed"
            value={String(playbackRate)}
            options={playbackRates.map((rate) => ({ value: String(rate), label: `${rate.toFixed(1)}x` }))}
            onSelect={(next) => changePlaybackRate(Number(next))}
          />
        </label>
        <label className="timing-setting">
          Blocking scope
          <PracticeSelect
            label="Blocking scope"
            value={blockingScope}
            disabled={!includeBlocking}
            options={[
              { value: "role", label: "My role" },
              { value: "all", label: "All roles" }
            ]}
            onSelect={(next) => changeBlockingScope(next as BlockingScope)}
          />
        </label>
        <fieldset className="timing-options">
          <legend>Timing targets</legend>
          <div className="timing-options-controls">
            <div className="timing-targets-row">
              <div className="timing-targets-controls">
                <label className="timing-setting">
                  Speaking pause
                  <PracticeSelect
                    label="Speaking pause"
                    value={String(speakAlongPauseMs)}
                    options={practiceTimingOptionsMs.map((optionMs) => ({
                      value: String(optionMs),
                      label: formatTimingOption(optionMs)
                    }))}
                    onSelect={(next) => changeSpeakAlongPauseMs(Number(next))}
                  />
                </label>
                <label className="timing-setting">
                  Tempo pickup target
                  <PracticeSelect
                    label="Tempo pickup target"
                    value={String(tempoTargetHesitationMs)}
                    options={practiceTimingOptionsMs.map((optionMs) => ({
                      value: String(optionMs),
                      label: formatTimingOption(optionMs)
                    }))}
                    onSelect={(next) => changeTempoTargetHesitationMs(Number(next))}
                    disabled={syncPracticeTiming}
                  />
                </label>
              </div>
              <button
                type="button"
                className={`timing-sync-toggle ${syncPracticeTiming ? "linked" : ""}`}
                aria-label={syncPracticeTiming ? "Disable sync for timing targets." : "Keep timing targets in sync."}
                aria-pressed={syncPracticeTiming}
                data-tooltip={syncPracticeTiming ? "Unlock timing targets" : "Lock timing targets"}
                onClick={() => changeSyncPracticeTiming(!syncPracticeTiming)}
                title={syncPracticeTiming ? "Timing targets linked" : "Timing targets unlinked"}
              >
                <span aria-hidden="true">{syncPracticeTiming ? "🔒" : "🔓"}</span>
              </button>
            </div>
            <label className="timing-setting">
              Practice target pace multiplier
              <PracticeSelect
                label="Practice target pace multiplier"
                value={String(practiceTargetPaceMultiplier)}
                options={practicePaceMultiplierOptions.map((optionMultiplier) => ({
                  value: String(optionMultiplier),
                  label: `${optionMultiplier.toFixed(1)}x`
                }))}
                onSelect={(next) => changePracticeTargetPaceMultiplier(Number(next))}
              />
            </label>
          </div>
        </fieldset>
        <p className="status">
          Tempo timing uses microphone energy only: no recording, no transcription, no upload.
        </p>
      </div>
    </div>
  );

  if (isOptionsPageVisible) {
    return (
      <main className="shell">
        <section className="hero rehearsal">
          <header className="rehearsal-header">
            <div className="breadcrumb-row">
              <button
                type="button"
                className="icon-button secondary"
                aria-label="Back to rehearsal."
                data-tooltip="Back to rehearsal"
                onClick={closeOptionsPage}
              >
                <span aria-hidden="true">←</span>
              </button>
              <div className="rehearsal-title-stack">
                <p className="rehearsal-play-title">{playbook.title}</p>
                <p className="rehearsal-role-title">Options</p>
              </div>
            </div>
          </header>
          {storageStatus ? (
            <p className="error" role="alert">
              {storageStatus}
            </p>
          ) : null}
          <div className="rehearsal-workspace">
            {practiceOptionsPanel}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="hero rehearsal">
        <header className="rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary rehearsal-nav-icon"
              aria-label="Back to library."
              data-tooltip="Back to library."
              onClick={onBack}
            >
              <span aria-hidden="true">📚</span>
            </button>
            <div className="rehearsal-title-stack">
              <p className="rehearsal-play-title">{playbook.title}</p>
              <p className="rehearsal-role-title">{role.displayName}</p>
            </div>
          </div>
          <div className="rehearsal-line-metadata">
            <button
              type="button"
              className="outline-open-button icon-button secondary"
              aria-label={isOutlineOpen ? "Browse cues" : "Open cues"}
              data-tooltip={isOutlineOpen ? "Browse cues" : "Open cues"}
              onClick={() => setIsOutlineOpen(true)}
            >
              <span aria-hidden="true">📋</span>
            </button>
            <p className="line-position">{line ? line.id : "No lines"}</p>
          </div>
        </header>
        {storageStatus ? (
          <p className="error" role="alert">
            {storageStatus}
          </p>
        ) : null}

        <div className="rehearsal-body">
          <div
            className={
              isOutlineOpen
                ? "rehearsal-workspace"
                : isCompactViewport
                  ? "rehearsal-workspace no-outline"
                  : "rehearsal-workspace outline-collapsed"
            }
          >
            <OutlineSidecar
            currentLineId={line?.id ?? null}
            includeBlocking={includeBlocking}
            blockingScope={blockingScope}
            includeDirections={includeDirections}
            bookmarkedLineIds={bookmarkedLineIds}
            lineTimingStatusByLineId={lineTimingStatusByLineId}
            isOpen={isOutlineOpen}
            isCompactViewport={isCompactViewport}
            lines={role.lines}
            playbook={playbook}
            sections={playbook.sections}
            onSelectLine={(lineId) => void jumpFromOutline(lineId)}
            onToggleOpen={() => setIsOutlineOpen((current) => !current)}
          />
          <div className="rehearsal-main">
            {line ? (
              <div className="rehearsal-line-layout">
                <section className="cue-section-panel" aria-label={`Cue: ${visibleCues[0]?.speaker ?? role.displayName}`}>
                  <h2 className="cue-section-title">{`Cue: ${visibleCues[0]?.speaker ?? role.displayName}`}</h2>
                  <section className="cue-strip" aria-label="Cue">
                    <section className="control-strip cue-control-strip" aria-label="Cue controls">
                      <div className="transport">
                        <div className="control-group transport-group cue-play-group">
                          {playbackSource === "cue" && playbackState === "playing" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label="Pause cue playback. Shortcut: Space."
                              data-tooltip="Pause cue"
                              onClick={() => void runCommand("pause")}
                            >
                              <span aria-hidden="true" className="transport-icon">
                                ⏸
                              </span>
                            </button>
                          ) : null}
                          {playbackSource === "cue" && playbackState === "paused" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label="Resume cue playback. Shortcut: Space."
                              data-tooltip="Resume cue"
                              onClick={() => void runCommand("resume")}
                            >
                              <span aria-hidden="true" className="transport-icon">
                                ▶
                              </span>
                            </button>
                          ) : null}
                          {playbackSource !== "cue" || playbackState === "idle" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label={`${hasStarted ? "Replay cue" : "Play cue"}. Shortcut: R.`}
                              data-tooltip={hasStarted ? "Replay cue" : "Play cue"}
                              onClick={() => void runCommand("repeat-cue")}
                            >
                              <span aria-hidden="true" className="transport-icon">
                                ▶
                              </span>
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="transport-button secondary"
                            aria-label="Stop cue playback. Shortcut: Escape."
                            data-tooltip="Stop"
                            onClick={() => void runCommand("stop")}
                          >
                            <span aria-hidden="true" className="transport-icon">
                              ■
                            </span>
                          </button>
                        </div>
                        <div className="control-group transport-group cue-navigation-group">
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
                        <div className="control-group transport-group cue-bookmark-group">
                          <button
                            type="button"
                            className="quick-toggle"
                            aria-label="Go to previous bookmark."
                            data-tooltip="Previous bookmark"
                            onClick={() => bookmarkNeighbors.previousLineId && jumpToLine(bookmarkNeighbors.previousLineId)}
                            disabled={!bookmarkNeighbors.previousLineId}
                          >
                            <span aria-hidden="true">↤</span>
                          </button>
                          <button
                            type="button"
                            className={isCurrentLineBookmarked ? "quick-toggle active" : "quick-toggle"}
                            aria-pressed={isCurrentLineBookmarked}
                            aria-label={
                              isCurrentLineBookmarked
                                ? "Remove bookmark from current line."
                                : "Bookmark current line."
                            }
                            data-tooltip={isCurrentLineBookmarked ? "Bookmarked" : "Bookmark"}
                            onClick={() => void runCommand("bookmark")}
                          >
                            <span aria-hidden="true">{isCurrentLineBookmarked ? "★" : "☆"}</span>
                          </button>
                          <button
                            type="button"
                            className="quick-toggle"
                            aria-label="Go to next bookmark."
                            data-tooltip="Next bookmark"
                            onClick={() => bookmarkNeighbors.nextLineId && jumpToLine(bookmarkNeighbors.nextLineId)}
                            disabled={!bookmarkNeighbors.nextLineId}
                          >
                            <span aria-hidden="true">↦</span>
                          </button>
                        </div>
                      </div>
                    </section>
                    <div className="cue-strip-cards">
                    {visibleCues.map((cue, index) => (
                      <CueCard cue={cue} showSpeaker={false} key={`${line.id}-cue-${index}`} />
                      ))}
                      {includeBlocking
                        ? visibleBlockingForLine(line, blockingScope)
                            .filter((blocking) => blocking.placement !== "inline")
                            .map((blocking) => (
                              <article
                                className="card cue-card cue-blocking-card"
                                key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}
                              >
                                <p className="speaker blocking-target">{blocking.targets.join(", ")}</p>
                                <p className="cue-blocking-text">({blocking.text})</p>
                              </article>
                            ))
                        : null}
                    </div>
                  </section>
                </section>

                <section className="stack" aria-label="Current cue and line">
                  <div className="line-practice-controls">
                    <section className="control-strip line-control-strip" aria-label="Line controls">
                      <div className="transport">
                        <div className="transport-group">
                          <button
                            type="button"
                            className="transport-button secondary"
                            aria-label="Play your line. Shortcut: L."
                            data-tooltip="Play your line"
                            onClick={() => void runCommand("hear-line")}
                            disabled={!line}
                          >
                            <span aria-hidden="true" className="transport-icon">
                              ▶
                            </span>
                          </button>
                          {playbackSource === "line" && playbackState === "playing" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label="Pause line playback. Shortcut: Space."
                              data-tooltip="Pause line"
                              onClick={() => void runCommand("pause")}
                            >
                              <span aria-hidden="true" className="transport-icon">
                                ⏸
                              </span>
                            </button>
                          ) : null}
                          {playbackSource === "line" && playbackState === "paused" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label="Resume line playback. Shortcut: Space."
                              data-tooltip="Resume line"
                              onClick={() => void runCommand("resume")}
                            >
                              <span aria-hidden="true" className="transport-icon">
                                ▶
                              </span>
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="transport-button secondary"
                            aria-label="Stop line playback. Shortcut: Escape."
                            data-tooltip="Stop line"
                            onClick={() => void runCommand("stop")}
                          >
                            <span aria-hidden="true" className="transport-icon">
                              ■
                            </span>
                          </button>
                        </div>
                      </div>
                    </section>
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
          </div>
        </div>

          <div className="session-settings">
          <div className="quick-practice-toggles rehearsal-quick-toggles" aria-label="Quick practice toggles">
            <div className="rehearsal-practice-toggles-inline">
              <button
                type="button"
                className={tempoTimingEnabled ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={tempoTimingEnabled}
                aria-label={tempoTimingEnabled ? "Disable tempo timing." : "Enable tempo timing."}
                data-tooltip={tempoTimingEnabled ? "Tempo timing on" : "Tempo timing off"}
                disabled={speakAlongEnabled}
                onClick={() => void (tempoTimingEnabled ? disableTempoTiming() : enableTempoTiming())}
              >
                <span aria-hidden="true">⏱</span>
              </button>
              <button
                type="button"
                className={speakAlongEnabled ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={speakAlongEnabled}
                aria-label={speakAlongEnabled ? "Disable speak-along practice." : "Enable speak-along practice."}
                data-tooltip={speakAlongEnabled ? "Speak-along on" : "Speak-along off"}
                disabled={tempoTimingEnabled}
                onClick={() => changeSpeakAlongEnabled(!speakAlongEnabled)}
              >
                <span aria-hidden="true">👄</span>
              </button>
              <button
                type="button"
                className={showLinesByDefault ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={showLinesByDefault}
                aria-label={showLinesByDefault ? "Hide lines." : "Show lines."}
                data-tooltip={showLinesByDefault ? "Show lines on" : "Show lines off"}
                onClick={() => changeShowLinesByDefault(!showLinesByDefault)}
              >
                <span aria-hidden="true">👁</span>
              </button>
              <button
                type="button"
                className={includeBlocking ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={includeBlocking}
                aria-label={includeBlocking ? "Hide blocking." : "Show blocking."}
                data-tooltip={includeBlocking ? "Blocking on" : "Blocking off"}
                onClick={() => changeIncludeBlocking(!includeBlocking)}
              >
                <span aria-hidden="true">♿</span>
              </button>
              <button
                type="button"
                className={includeDirections ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={includeDirections}
                aria-label={includeDirections ? "Hide stage directions." : "Show stage directions."}
                data-tooltip={includeDirections ? "Directions on" : "Directions off"}
                onClick={() => changeIncludeDirections(!includeDirections)}
              >
                <span aria-hidden="true">⌞⌝</span>
              </button>
            </div>
            <div className="rehearsal-quick-actions">
              <button
                type="button"
                className="quick-toggle"
                aria-label={showLineInfo ? "Hide line info." : "Show line info."}
                aria-pressed={showLineInfo}
                data-tooltip="Line info"
                onClick={() => setShowLineInfo((current) => !current)}
              >
                <span aria-hidden="true">ⓘ</span>
              </button>
              <button
                type="button"
                className="quick-toggle"
                aria-label="Choose role."
                data-tooltip="Choose role."
                onClick={onSelectRole}
              >
                <span aria-hidden="true">🎭</span>
              </button>
              <button
                type="button"
                className="quick-toggle rehearsal-options-button"
                aria-label="Open options"
                data-tooltip="Options"
                onClick={openOptionsPage}
              >
                <span aria-hidden="true">⚙</span>
              </button>
            </div>
          </div>
          {displayedPlaybackStatus ? (
            <p className={typeof displayedPlaybackStatus === "string" ? "status" : "status status-timing"} aria-live="polite">
              {typeof displayedPlaybackStatus === "string" ? (
                displayedPlaybackStatus
              ) : (
                <>
                  <button
                    type="button"
                    className={`timing-status-pill timing-status-pill--${displayedPlaybackStatus.delivery.label}`}
                    aria-label={`Delivery: ${displayedPlaybackStatus.delivery.label}`}
                    aria-expanded={expandedTimingPill === "delivery"}
                    onClick={() =>
                      setExpandedTimingPill((current) => (current === "delivery" ? null : "delivery"))
                    }
                  >
                    <span aria-hidden="true">{deliveryPillForLabel(displayedPlaybackStatus.delivery.label)}</span>
                    <span>delivery</span>
                  </button>
                  <button
                    type="button"
                    className={`timing-status-pill timing-status-pill--${displayedPlaybackStatus.pickup.label}`}
                    aria-label={`Pickup: ${displayedPlaybackStatus.pickup.label}`}
                    aria-expanded={expandedTimingPill === "pickup"}
                    onClick={() => setExpandedTimingPill((current) => (current === "pickup" ? null : "pickup"))}
                  >
                    <span aria-hidden="true">{pickupPillForLabel(displayedPlaybackStatus.pickup.label)}</span>
                    <span>pickup</span>
                  </button>
                  {expandedTimingPill === "delivery" ? (
                    <span className="timing-status-details">
                      Delivery: {timingDeltaText(displayedPlaybackStatus.delivery.measuredMs, displayedPlaybackStatus.delivery.targetMs)}.
                    </span>
                  ) : null}
                  {expandedTimingPill === "pickup" ? (
                    <span className="timing-status-details">
                      Pickup: {timingDeltaText(displayedPlaybackStatus.pickup.measuredMs, displayedPlaybackStatus.pickup.targetMs)}.
                    </span>
                  ) : null}
                </>
              )}
            </p>
          ) : null}
          {showLineInfo && line ? (
            <div className="line-duration-panel" role="note" aria-live="polite">
              <p>Playbook: {playbook.id}</p>
              <p>Line/Cue ID: {line.id}</p>
              <p>Cue file: {line.cue.audioPath}</p>
              <p>Cue length: {formatDurationMs(line.cue.durationMs)}</p>
              <p>Line length: {formatDurationMs(lineLengthMs)}</p>
              {latestLineTimingAttempt ? (
                <p>Timing target: {formatDurationMs(latestLineTimingAttempt.targetDeliveryMs)}</p>
              ) : (
                <p>Timing target: {formatDurationMs(lineLengthMs)}</p>
              )}
            </div>
          ) : null}
        </div>
      </div>
      </section>
    </main>
  );
}

function OutlineSidecar({
  currentLineId,
  includeBlocking,
  blockingScope,
  includeDirections,
  bookmarkedLineIds,
  lineTimingStatusByLineId,
  isOpen,
  isCompactViewport,
  playbook,
  lines,
  sections,
  onSelectLine,
  onToggleOpen
}: {
  currentLineId: string | null;
  includeBlocking: boolean;
  blockingScope: BlockingScope;
  includeDirections: boolean;
  bookmarkedLineIds: Set<string>;
  lineTimingStatusByLineId: Map<string, TimingLineStatus>;
  isOpen: boolean;
  isCompactViewport: boolean;
  playbook: Playbook;
  lines: Line[];
  sections: Playbook["sections"];
  onSelectLine: (lineId: string) => void;
  onToggleOpen: () => void;
}) {
  if (isCompactViewport && !isOpen) {
    return null;
  }
  if (!isOpen) {
    return (
      <aside className="outline-sidecar collapsed" aria-label="Rehearsal outline">
        <button
          type="button"
          className="outline-disclosure-button"
          aria-label="Show outline."
          title="Show outline"
          onClick={onToggleOpen}
        >
          <span className="context-disclosure" aria-hidden="true" />
        </button>
        <span className="outline-progress" aria-label={`${currentLineId ?? "No line"} selected`}>
          {currentLineId ?? "No line"}
          <span>current</span>
        </span>
      </aside>
    );
  }

  return (
    <OutlinePanel
      currentLineId={currentLineId}
      includeBlocking={includeBlocking}
      blockingScope={blockingScope}
      includeDirections={includeDirections}
      playbook={playbook}
      lines={lines}
      sections={sections}
      bookmarkedLineIds={bookmarkedLineIds}
      lineTimingStatusByLineId={lineTimingStatusByLineId}
      onSelectLine={onSelectLine}
      onToggleOpen={onToggleOpen}
    />
  );
}

function OutlinePanel({
  currentLineId,
  includeBlocking,
  blockingScope,
  includeDirections,
  bookmarkedLineIds,
  lineTimingStatusByLineId,
  playbook,
  lines,
  sections,
  onSelectLine,
  onToggleOpen
}: {
  currentLineId: string | null;
  includeBlocking: boolean;
  blockingScope: BlockingScope;
  includeDirections: boolean;
  bookmarkedLineIds: Set<string>;
  lineTimingStatusByLineId: Map<string, TimingLineStatus>;
  playbook: Playbook;
  lines: Line[];
  sections: Playbook["sections"];
  onSelectLine: (lineId: string) => void;
  onToggleOpen: () => void;
}) {
  const [mode, setMode] = useState<OutlineMode>("cues");
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showBookmarksOnly, setShowBookmarksOnly] = useState(false);
  const [activeTimingFilters, setActiveTimingFilters] = useState<TimingLineStatus[]>([]);
  const currentLineRef = useRef<HTMLButtonElement | null>(null);
  const modeMenuRef = useRef<HTMLDivElement | null>(null);
  const showAllTimings = activeTimingFilters.length === 0;
  const normalizedSearchQuery = searchQuery.trim();
  const sectionGroups = scriptBrowserSections(lines, sections)
    .map((section) => ({
      ...section,
      lines: section.lines
        .filter((line) => (showBookmarksOnly ? bookmarkedLineIds.has(line.id) : true))
        .filter((line) =>
          showAllTimings ? true : activeTimingFilters.includes(lineTimingStatusByLineId.get(line.id) ?? "untimed")
        )
        .filter((line) =>
          outlineSearchText(line, mode, includeDirections, includeBlocking, blockingScope, playbook)
            .toLocaleLowerCase()
            .includes(normalizedSearchQuery.toLocaleLowerCase())
      )
    }))
    .filter((section) => section.lines.length > 0);
  const activeTimingFilterSummary = showAllTimings ? "" : activeTimingFilters.join(" + ");

  function toggleTimingFilter(target: TimingLineStatus) {
    setActiveTimingFilters((current) => {
      if (current.includes(target)) {
        return current.filter((status) => status !== target);
      }
      return [...current, target];
    });
  }

  function timingFilterGlyph(status: TimingLineStatus): string {
    if (status === "slow") {
      return "🐢";
    }
    if (status === "fast") {
      return "🐇";
    }
    if (status === "good") {
      return "🎯";
    }
    return "⏱";
  }

  function timingFilterLabel(status: TimingLineStatus): string {
    if (status === "slow") {
      return "slow";
    }
    if (status === "fast") {
      return "fast";
    }
    if (status === "good") {
      return "on target";
    }
    return "untimed";
  }

  useEffect(() => {
    currentLineRef.current?.scrollIntoView({ block: "nearest" });
  }, [currentLineId, mode]);

  useEffect(() => {
    if (!isModeMenuOpen) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (!modeMenuRef.current?.contains(event.target as Node)) {
        setIsModeMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsModeMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isModeMenuOpen]);

  return (
    <aside className="outline-sidecar outline-browser" aria-label="Rehearsal outline">
      <div className="outline-header">
        <div className="outline-header-actions">
          <div className="outline-timing-filter-group" aria-label="Timing filters">
            {(["slow", "good", "fast", "untimed"] as TimingLineStatus[]).map((status) => {
              const isActive = activeTimingFilters.includes(status);
              return (
                <button
                  type="button"
                  key={status}
                  className={`outline-timing-filter ${isActive ? "active" : ""}`}
                  aria-pressed={isActive}
                  aria-label={`Show ${timingFilterLabel(status)} lines`}
                  title={isActive ? `Hide ${timingFilterLabel(status)} lines` : `Show ${timingFilterLabel(status)} lines`}
                  onClick={() => toggleTimingFilter(status)}
                >
                  {timingFilterGlyph(status)}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            className={showBookmarksOnly ? "outline-bookmark-filter active" : "outline-bookmark-filter"}
            aria-pressed={showBookmarksOnly}
            aria-label={showBookmarksOnly ? "Show all lines" : "Show bookmarked lines only"}
            onClick={() => setShowBookmarksOnly((current) => !current)}
            title={showBookmarksOnly ? "Show all lines" : "Show bookmarked lines only"}
          >
            {showBookmarksOnly ? "★" : "☆"}
          </button>
          <div className="outline-mode-select-wrap" ref={modeMenuRef}>
            <button
              type="button"
              className="outline-mode-select"
              aria-label="Outline mode"
              aria-expanded={isModeMenuOpen}
              aria-controls="outline-mode-options"
              onClick={() => setIsModeMenuOpen((current) => !current)}
            >
              <span>{mode === "cues" ? "Cues" : "Lines"}</span>
              <span className="outline-mode-select-caret" aria-hidden="true">
                ▾
              </span>
            </button>
            <div
              id="outline-mode-options"
              className={`outline-mode-select-options ${isModeMenuOpen ? "open" : ""}`}
              role="listbox"
              aria-label="Outline mode"
            >
              <button
                type="button"
                role="option"
                className={mode === "cues" ? "outline-mode-select-option active" : "outline-mode-select-option"}
                aria-selected={mode === "cues"}
                onClick={() => {
                  setMode("cues");
                  setIsModeMenuOpen(false);
                }}
              >
                Cues
              </button>
              <button
                type="button"
                role="option"
                className={mode === "lines" ? "outline-mode-select-option active" : "outline-mode-select-option"}
                aria-selected={mode === "lines"}
                onClick={() => {
                  setMode("lines");
                  setIsModeMenuOpen(false);
                }}
              >
                Lines
              </button>
            </div>
          </div>
          <button
            type="button"
            className="outline-disclosure-button expanded"
            aria-label="Hide outline."
            title="Hide outline"
            onClick={onToggleOpen}
          >
            <span className="context-disclosure" aria-hidden="true" />
          </button>
        </div>
      </div>
      <label className="outline-search">
        <span>Search {mode === "cues" ? "cues" : "lines"}</span>
        <div>
          <input
            type="search"
            value={searchQuery}
            placeholder={mode === "cues" ? "Find a cue or line" : "Find a line"}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          {searchQuery ? (
            <button type="button" aria-label="Clear outline search." onClick={() => setSearchQuery("")}>
              ×
            </button>
          ) : null}
        </div>
      </label>
      <div className="outline-list">
        {sectionGroups.length === 0 ? (
          <p className="outline-empty">
            No matching {showBookmarksOnly ? "bookmarked " : ""}
            {!showAllTimings ? ` ${activeTimingFilterSummary} ` : ""}
            {mode === "cues" ? "cues" : "lines"}.
          </p>
        ) : null}
        {sectionGroups.map((section) => (
          <section className="outline-section" key={section.id}>
            <h3>{section.title}</h3>
            <div className="outline-section-list">
              {section.lines.map((line) => (
                <button
                  type="button"
                  key={line.id}
                  className={line.id === currentLineId ? "outline-row selected" : "outline-row"}
                  ref={line.id === currentLineId ? currentLineRef : undefined}
                  onClick={() => onSelectLine(line.id)}
                >
                  <span
                    className={`status-dot timing timing-${lineTimingStatusByLineId.get(line.id) ?? "untimed"}`}
                    title={timingLineStatusToLabel(lineTimingStatusByLineId.get(line.id) ?? "untimed")}
                    aria-hidden="true"
                  >
                    {timingLineStatusToGlyph(lineTimingStatusByLineId.get(line.id) ?? "untimed")}
                  </span>
                  <span
                    className={`status-dot${bookmarkedLineIds.has(line.id) ? " bookmark" : ""}`}
                    aria-hidden="true"
                  >
                    {bookmarkedLineIds.has(line.id) ? "★" : null}
                  </span>
                  <strong>{line.id}</strong>
                  <span className="outline-speaker">{outlineSpeaker(line, mode, includeDirections, playbook)}</span>
                  <span className="outline-text">{outlineText(line, mode, includeDirections, playbook)}</span>
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
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}

export function outlineSearchText(
  line: Line,
  mode: OutlineMode,
  includeDirections: boolean,
  includeBlocking: boolean,
  blockingScope: BlockingScope,
  playbook: Playbook
): string {
  const parts = [
    line.id,
    outlineSpeaker(line, mode, includeDirections, playbook),
    outlineText(line, mode, includeDirections, playbook)
  ];
  if (mode === "cues") {
    parts.push(line.speaker, line.responseText);
  }
  if (includeDirections) {
    parts.push(...line.directions.map((direction) => direction.text));
  }
  if (includeBlocking) {
    parts.push(...visibleBlockingForLine(line, blockingScope).map((blocking) => `${blocking.targets.join(" ")} ${blocking.text}`));
  }
  return parts.join(" ");
}

function outlineSpeaker(line: Line, mode: OutlineMode, includeDirections: boolean, playbook: Playbook): string {
  if (mode === "lines") {
    return line.speaker;
  }
  return visibleCuesForDisplay([line.cue], includeDirections, playbook.context, playbook, line)[0]?.speaker ?? line.cue.speaker;
}

function outlineText(line: Line, mode: OutlineMode, includeDirections: boolean, playbook: Playbook): string {
  if (mode === "lines") {
    return line.responseText;
  }
  return visibleCuesForDisplay([line.cue], includeDirections, playbook.context, playbook, line)[0]?.text ?? line.cue.text;
}

function visibleBlockingForLine(line: Line, blockingScope: BlockingScope) {
  return (line.blocking ?? []).filter(
    (blocking) => blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role)
  );
}

function timingLineStatusToGlyph(status: TimingLineStatus): string {
  if (status === "slow") {
    return "🐢";
  }
  if (status === "fast") {
    return "🐇";
  }
  if (status === "good") {
    return "🎯";
  }
  return "⏱";
}

function timingLineStatusToLabel(status: TimingLineStatus): string {
  if (status === "slow") {
    return "Slow timing";
  }
  if (status === "fast") {
    return "Fast timing";
  }
  if (status === "good") {
    return "Good timing";
  }
  return "Untimed";
}

function formatTimingResult(
  feedback: ReturnType<typeof tempoFeedbackFor>,
  practiceTargetPaceMultiplier = 1
): TimingStatusPill {
  const deliveryLabel = feedback.delivery?.label === "fast" ? "fast" : feedback.delivery?.label === "slow" ? "slow" : "good";
  const pickupLabel = feedback.hesitation.label === "sharp" ? "fast" : feedback.hesitation.label === "late" ? "slow" : "good";
  const measuredDeliveryMs = feedback.delivery?.measuredMs ?? 0;
  const baseTargetDeliveryMs = feedback.delivery?.targetMs ?? 0;
  const normalizedPracticeTargetPaceMultiplier = normalizePracticeTargetPaceMultiplier(practiceTargetPaceMultiplier);
  const targetDeliveryMs = baseTargetDeliveryMs / normalizedPracticeTargetPaceMultiplier;
  const measuredPickupMs = feedback.hesitation.measuredMs;
  const targetPickupMs = feedback.hesitation.targetMs;
  return {
    delivery: {
      label: deliveryLabel,
      measuredMs: measuredDeliveryMs,
      targetMs: targetDeliveryMs
    },
    pickup: {
      label: pickupLabel,
      measuredMs: measuredPickupMs,
      targetMs: targetPickupMs
    },
    details: `${deliveryLabel} ${(measuredDeliveryMs / 1000).toFixed(2)}s←${(targetDeliveryMs / 1000).toFixed(2)}s, pickup ${pickupLabel} ${(
      measuredPickupMs / 1000
    ).toFixed(2)}s←${(targetPickupMs / 1000).toFixed(2)}s`
  };
}

function formatTimingAttempt(attempt: TimingAttempt, practiceTargetPaceMultiplier = 1): TimingStatusPill {
  const normalizedPracticeTargetPaceMultiplier = normalizePracticeTargetPaceMultiplier(practiceTargetPaceMultiplier);
  const targetDeliveryMs = attempt.targetDeliveryMs / normalizedPracticeTargetPaceMultiplier;
  const lineDeliveryLabel = deliveryLabel(attempt.deliveryMs, attempt.targetDeliveryMs, normalizedPracticeTargetPaceMultiplier);
  const displayDeliveryLabel = lineDeliveryLabel === "fast" ? "fast" : lineDeliveryLabel === "slow" ? "slow" : "good";
  const pickupLabel =
    attempt.hesitationLabel === "sharp" ? "fast" : attempt.hesitationLabel === "late" ? "slow" : "good";
  return {
    delivery: {
      label: displayDeliveryLabel,
      measuredMs: attempt.deliveryMs,
      targetMs: targetDeliveryMs
    },
    pickup: {
      label: pickupLabel,
      measuredMs: attempt.hesitationMs,
      targetMs: attempt.targetHesitationMs
    },
    details: `${displayDeliveryLabel} ${(attempt.deliveryMs / 1000).toFixed(2)}s←${(targetDeliveryMs / 1000).toFixed(
      2
    )}s, pickup ${pickupLabel} ${(attempt.hesitationMs / 1000).toFixed(2)}s←${(attempt.targetHesitationMs / 1000).toFixed(
      2
    )}s`
  };
}

function deliveryPillForLabel(label: TimingLabel): string {
  if (label === "fast") {
    return "🐇";
  }
  if (label === "slow") {
    return "🐢";
  }
  return "🎯";
}

function pickupPillForLabel(label: TimingLabel): string {
  if (label === "fast") {
    return "🐇";
  }
  if (label === "slow") {
    return "🐢";
  }
  return "🎯";
}

function timingDeltaText(measuredMs: number, targetMs: number): string {
  if (targetMs <= 0) {
    return `${(measuredMs / 1000).toFixed(2)}s (target unavailable)`;
  }
  const deltaMs = measuredMs - targetMs;
  const deltaSec = Math.abs(deltaMs) / 1000;
  const percent = ((Math.abs(deltaMs) / targetMs) * 100).toFixed(2);
  if (deltaMs === 0) {
    return `on target at ${(measuredMs / 1000).toFixed(2)}s`;
  }
  if (deltaMs > 0) {
    return `${(measuredMs / 1000).toFixed(2)}s vs ${(targetMs / 1000).toFixed(2)}s (+${deltaSec.toFixed(2)}s, +${percent}% over)`;
  }
  return `${(measuredMs / 1000).toFixed(2)}s vs ${(targetMs / 1000).toFixed(2)}s (${deltaSec.toFixed(2)}s under, -${percent}%)`;
}

function formatDurationMs(durationMs: number): string {
  return `${(Math.max(0, durationMs) / 1000).toFixed(2)}s`;
}

const minPlaybackRate = 0.4;
const maxPlaybackRate = 1.3;
const minPracticeTargetPaceMultiplier = 0.4;
const maxPracticeTargetPaceMultiplier = 1.3;
const practicePaceMultiplierOptions = [
  0.4,
  0.5,
  0.6,
  0.7,
  0.8,
  0.9,
  1.0,
  1.1,
  1.2,
  1.3
];
const REHEARSAL_COMPACT_MEDIA_QUERY = "(max-width: 760px), (orientation: landscape) and (max-height: 540px)";
const playbackRates = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];
const practiceTimingOptionsMs = [250, 500, 750, 1000, 1250, 1500, 2000];

function isCompactRehearsalViewport() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia(REHEARSAL_COMPACT_MEDIA_QUERY).matches;
}

function formatTimingOption(optionMs: number): string {
  return `${(optionMs / 1000).toFixed(optionMs % 1000 === 0 ? 0 : 2)}s`;
}

export function clampPlaybackRate(playbackRate: number): number {
  const roundedPlaybackRate = Math.round(playbackRate * 10) / 10;
  return Math.min(maxPlaybackRate, Math.max(minPlaybackRate, roundedPlaybackRate));
}

export function normalizePracticeTargetPaceMultiplier(value: number | undefined): number {
  const parsedValue = value ?? 1;
  if (!Number.isFinite(parsedValue)) {
    return 1;
  }
  return Math.min(maxPracticeTargetPaceMultiplier, Math.max(minPracticeTargetPaceMultiplier, parsedValue));
}

export function visibleCuesForDisplay(
  cues: Cue[],
  includeDirections: boolean,
  context: ContextBlock[] = [],
  playbook?: Playbook,
  currentLine?: Line
): Cue[] {
  if (includeDirections) {
    return cues;
  }
  const contextKindByCueKey = new Map(
    context
      .filter((block) => block.audioPath)
      .map((block) => [cueKey(block.speaker, block.text, block.audioPath ?? ""), block.kind])
  );
  return cues.map((cue) => {
    const kind = cue.kind ?? contextKindByCueKey.get(cueKey(cue.speaker, cue.text, cue.audioPath));
    if (kind === "description" || kind === "direction") {
      return precedingSpeechCue(playbook, currentLine) ?? cue;
    }
    return cue;
  });
}

export function resolveCurrentLineFromEngine(
  roleLines: Line[],
  positionIndex: number,
  fallbackLine: Line | null
): Line | null {
  return roleLines[positionIndex] ?? fallbackLine;
}

function cueKey(speaker: string, text: string, audioPath: string) {
  return `${speaker}\u0000${text}\u0000${audioPath}`;
}

function precedingSpeechCue(playbook: Playbook | undefined, currentLine: Line | undefined): Cue | null {
  if (!playbook || !currentLine) {
    return null;
  }
  const priorLine = playbook.roles
    .flatMap((role) => role.lines)
    .filter((line) => line.responseSegments.length > 0)
    .filter((line) => blockOrder(line.blockId) < blockOrder(currentLine.blockId))
    .sort((left, right) => blockOrder(right.blockId) - blockOrder(left.blockId))[0];
  if (!priorLine) {
    return null;
  }
  return {
    speaker: priorLine.speaker,
    text: priorLine.responseText,
    audioPath: priorLine.responseSegments[0].audioPath,
    durationMs: priorLine.responseSegments.reduce((totalMs, segment) => totalMs + segment.durationMs, 0),
    kind: "speech"
  };
}

function blockOrder(blockId: string): number {
  return blockId
    .split(".")
    .reduce((total, part, index) => total + Number(part) * 1000 ** (3 - index), 0);
}
