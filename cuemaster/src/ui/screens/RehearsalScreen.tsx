import { useEffect, useMemo, useRef, useState } from "react";
import type { Cue } from "../../domain/cue";
import type { Line } from "../../domain/line";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import type { QueueItem } from "../../rehearsal/audioQueue";
import { cueWindowPresetForId } from "../../rehearsal/cueWindowPreset";
import { shortcutForKey } from "../../rehearsal/keyboardShortcuts";
import { buildCalloutResolverForSpeaker } from "../../rehearsal/calloutLookup";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../rehearsal/playbackItems";
import type { RehearsalCommand, RehearsalShortcut } from "../../rehearsal/rehearsalCommand";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import {
  resolveCurrentLineFromEngine,
  visibleCuesForDisplay
} from "../../rehearsal/rehearsalPresentation";
import { deliveryLabel } from "../../rehearsal/tempoFeedback";
import { defaultTargetHesitationMs, endOfLineSilenceMs, defaultTempoTimingConfig } from "../../rehearsal/tempoTimingConfig";
import {
  clampPlaybackRate,
  formatTimingAttempt,
  normalizeAbsolutePickupForgivenessMs,
  normalizeAbsoluteTempoForgivenessMs,
  normalizePracticeTargetPaceMultiplier,
  normalizeRehearsalTextSize,
  normalizeTempoEndOfLineSilenceMs,
  normalizeTempoTolerancePercent,
  type RehearsalTextSize,
  type TimingLabel,
  type TimingStatusPill
} from "../../rehearsal/timingPresentation";
import { VoiceActivityDetector } from "../../rehearsal/voiceActivityDetector";
import type { VoiceActivityResult } from "../../rehearsal/voiceActivityTracker";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import type { BlockingScope } from "../components/LineCard";
import { RehearsalBottomBar } from "../components/RehearsalBottomBar";
import { RehearsalHeader } from "../components/RehearsalHeader";
import { RehearsalLineWorkspace } from "../components/RehearsalLineWorkspace";
import { RehearsalOptionsScreen } from "../components/RehearsalOptionsScreen";
import { RehearsalOutline, type TimingLineStatus } from "../components/RehearsalOutline";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";
import { useBookmarks } from "../hooks/useBookmarks";
import { useRehearsalPlayback } from "../hooks/useRehearsalPlayback";
import { useRehearsalSettings, type AutoAdvanceMode, type AutoPlayLineMode } from "../hooks/useRehearsalSettings";
import { evaluateTempoTimingResult, useTempoTiming } from "../hooks/useTempoTiming";

type RehearsalScreenProps = {
  playbook: Playbook;
  role: Role;
  initialSession: RehearsalSession | null;
  initialStorageStatus?: string;
  onBack: () => void;
  onSelectRole: () => void;
};

type TimingPill = "delivery" | "pickup";

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
  const [position, setPosition] = useState(() => engine.position());
  const {
    playbackRate,
    setPlaybackRate,
    cueWindowPresetId,
    setCueWindowPresetId,
    showLinesByDefault,
    setShowLinesByDefault,
    isLineRevealed,
    setIsLineRevealed,
    includeDirections,
    setIncludeDirections,
    includeBlocking,
    setIncludeBlocking,
    blockingScope,
    setBlockingScope,
    speakAlongEnabled,
    setSpeakAlongEnabled,
    speakAlongPauseMs,
    setSpeakAlongPauseMs,
    practiceTargetPaceMultiplier,
    setPracticeTargetPaceMultiplier,
    tempoTargetHesitationMs,
    setTempoTargetHesitationMs,
    syncPracticeTiming,
    setSyncPracticeTiming,
    syncSpeakAlongSpeed,
    setSyncSpeakAlongSpeed,
    rehearsalTextSize,
    setRehearsalTextSize,
    absoluteTempoForgivenessMs,
    setAbsoluteTempoForgivenessMs,
    absolutePickupForgivenessMs,
    setAbsolutePickupForgivenessMs,
    autoAdvanceMode,
    setAutoAdvanceMode,
    autoPlayLineMode,
    setAutoPlayLineMode,
    tempoTolerancePercent,
    setTempoTolerancePercent,
    tempoEndOfLineSilenceMs,
    setTempoEndOfLineSilenceMs,
    tempoTimingEnabled,
    setTempoTimingEnabled,
    tempoTimingPreferred,
    setTempoTimingPreferred
  } = useRehearsalSettings(initialSession, engine.includeDirections());
  const {
    playbackState,
    playbackSource,
    playbackStatus,
    setPlaybackStatus,
    playItems,
    pausePlayback,
    resumePlayback,
    stopPlayback: stopPlaybackQueue
  } = useRehearsalPlayback(playbook.id);
  const [timingStatusMessage, setTimingStatusMessage] = useState<TimingStatusPill | null>(null);
  const [expandedTimingPill, setExpandedTimingPill] = useState<TimingPill | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isCalloutEnabled, setIsCalloutEnabled] = useState(false);
  const [storageStatus, setStorageStatus] = useState(initialStorageStatus);
  const [showLineInfo, setShowLineInfo] = useState(false);
  const [isOptionsPageVisible, setIsOptionsPageVisible] = useState(false);
  const [isCompactViewport, setIsCompactViewport] = useState(() => isCompactRehearsalViewport());
  const [isOutlineOpen, setIsOutlineOpen] = useState(() => !isCompactRehearsalViewport());
  const {
    reviewAttempts,
    startVoiceActivityDetector,
    stopVoiceActivityDetector,
    loadReviewAttempts,
    saveTimingAttempt,
    playTimingFeedbackTone
  } = useTempoTiming({
    playbookId: playbook.id,
    roleId: role.id,
    onStorageStatus: setStorageStatus
  });
  const calloutPlaybackSeq = useRef(0);
  const rehearsalLayoutClass = isCompactViewport ? "rehearsal-no-outline" : isOutlineOpen ? "rehearsal-outline-open" : "rehearsal-outline-collapsed";
  const activeTimingLineIdRef = useRef<string | null>(null);
  const tempoTimingRestoreStartedRef = useRef(false);
  const line = useMemo(
    () => role.lines.find((candidate) => candidate.id === activeLineId) ?? null,
    [activeLineId, role.lines]
  );
  const resolveCallout = useMemo(() => buildCalloutResolverForSpeaker(playbook), [playbook]);

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
  const currentCueCallout = useMemo(() => {
    const currentCue = cues.length > 0 ? cues[cues.length - 1] : null;
    return resolveCallout(currentCue?.speaker ?? null);
  }, [cues, resolveCallout]);
  const hasCurrentLineCallout = currentCueCallout !== null;
  function buildCalloutPlaybackItemsForCues(targetCues: Cue[]): QueueItem[] {
    const calloutItems: QueueItem[] = [];
    for (const cue of targetCues) {
      const cueCallout = isCalloutEnabled ? resolveCallout(cue.speaker) : null;
      if (!cueCallout) {
        continue;
      }
      calloutItems.push({ kind: "audio", path: cueCallout.audioPath, playbackRate: 1 });
      calloutItems.push({ kind: "delay", durationMs: 250 });
    }
    return calloutItems;
  }
  const visibleCues = useMemo(
    () => visibleCuesForDisplay(cues, includeDirections, playbook.context, playbook, line ?? undefined),
    [cues, includeDirections, playbook, line]
  );
  const {
    bookmarkedLineIds,
    isCurrentLineBookmarked,
    bookmarkNeighbors,
    toggleBookmark
  } = useBookmarks({
    playbookId: playbook.id,
    roleId: role.id,
    roleLines: role.lines,
    currentLine: line,
    onStorageStatus: setStorageStatus
  });
  const lineTimingStatusByLineId = useMemo(() => {
    const statusByLine = new Map<string, TimingLineStatus>(
      role.lines.map((roleLine) => [roleLine.id, "untimed" as const])
    );
    for (const attempt of reviewAttempts) {
      const attemptDeliveryLabel = deliveryLabel(
        attempt.deliveryMs,
        attempt.targetDeliveryMs,
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent
      );
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
  }, [practiceTargetPaceMultiplier, absoluteTempoForgivenessMs, tempoTolerancePercent, reviewAttempts, role.lines]);
  const displayedPlaybackStatus = useMemo(() => {
    if (timingStatusMessage) {
      return timingStatusMessage;
    }
    if (!playbackStatus) {
      return null;
    }
    if (/^Line Timed\.?$/i.test(playbackStatus) && latestLineTimingAttempt) {
      return formatTimingAttempt(
        latestLineTimingAttempt,
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent,
        absolutePickupForgivenessMs
      );
    }
    return playbackStatus;
  }, [
    playbackStatus,
    latestLineTimingAttempt,
    practiceTargetPaceMultiplier,
    absoluteTempoForgivenessMs,
    tempoTolerancePercent,
    absolutePickupForgivenessMs,
    timingStatusMessage
  ]);

  useEffect(() => {
    void saveSession(engine.position().index);
  }, []);

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
    const nextTimingStatusMessage = formatTimingAttempt(
      latestLineTimingAttempt,
      practiceTargetPaceMultiplier,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      absolutePickupForgivenessMs
    );
    setTimingStatusMessage((current) => {
      if (current && current.details === nextTimingStatusMessage.details) {
        return current;
      }
      return nextTimingStatusMessage;
    });
  }, [
    line?.id,
    latestLineTimingAttempt,
    practiceTargetPaceMultiplier,
    absoluteTempoForgivenessMs,
    tempoTolerancePercent,
    absolutePickupForgivenessMs,
    timingStatusMessage
  ]);

  useEffect(() => {
    setShowLineInfo(false);
  }, [line?.id]);

  useEffect(() => {
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
    layoutQuery.addListener(handleViewportChange);
    return () => {
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
        await playResponse(currentLineFromEngine());
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

  async function goNext(playNextCue = false, autoPlayLine = false, options: { preserveTimingStatus?: boolean } = {}) {
    const { preserveTimingStatus = false } = options;
    activeTimingLineIdRef.current = null;
    if (!preserveTimingStatus) {
      setTimingStatusMessage(null);
    }
    engine.next();
    updatePosition({ revealLine: showLinesByDefault });
    setIsLineRevealed(showLinesByDefault);
    if (playNextCue || hasStarted) {
      await playCue({ preserveTimingStatus });
      if (autoPlayLine && !speakAlongEnabled) {
        await playResponse(currentLineFromEngine());
      }
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
    nextPracticeTargetPaceMultiplier = practiceTargetPaceMultiplier,
    nextSyncSpeakAlongSpeed = syncSpeakAlongSpeed,
    nextAbsoluteTempoForgivenessMs = absoluteTempoForgivenessMs,
    nextTempoTolerancePercent = tempoTolerancePercent,
    nextAbsolutePickupForgivenessMs = absolutePickupForgivenessMs,
    nextAutoAdvanceMode = autoAdvanceMode,
    nextAutoPlayLineMode = autoPlayLineMode,
    nextRehearsalTextSize = rehearsalTextSize,
    nextTempoEndOfLineSilenceMs = tempoEndOfLineSilenceMs
  ) {
    const normalizedAutoPlayLineMode: AutoPlayLineMode = nextAutoAdvanceMode === "disabled" ? "disabled" : nextAutoPlayLineMode;
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
        absoluteTempoForgivenessMs: nextAbsoluteTempoForgivenessMs,
        tempoTolerancePercent: nextTempoTolerancePercent,
        absolutePickupForgivenessMs: nextAbsolutePickupForgivenessMs,
        tempoEndOfLineSilenceMs: nextTempoEndOfLineSilenceMs,
        autoAdvanceMode: nextAutoAdvanceMode,
        autoPlayLineMode: normalizedAutoPlayLineMode,
        syncSpeakAlongSpeed: nextSyncSpeakAlongSpeed,
        syncPracticeTiming: nextSyncPracticeTiming,
        rehearsalTextSize: nextRehearsalTextSize,
        tempoTimingPreferred: nextTempoTimingPreferred,
        updatedAt: Date.now()
      });
      setStorageStatus("");
    } catch (error) {
      setStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function playCue(options: { preserveTimingStatus?: boolean } = {}) {
    const { preserveTimingStatus = false } = options;
    const currentLine = currentLineFromEngine();
    setHasStarted(true);
    const calloutLineItems = buildCalloutPlaybackItemsForCues(cues);
    const didComplete = speakAlongEnabled && currentLine
      ? await playItems(
        [
          ...calloutLineItems,
          ...speakAlongPlaybackItems(
            engine.cuePayloads(cueWindowPresetId),
            currentLine,
            playbackRate,
            cueWindowPresetId,
            speakAlongPauseMs
          )
        ],
        { source: "cue" }
      )
      : await playItems(
        [...calloutLineItems, ...cuePlaybackItems(engine.cuePayloads(cueWindowPresetId), cueWindowPresetId)],
        { source: "cue" }
      );

    if (didComplete && !speakAlongEnabled) {
      beginTimedAttempt(preserveTimingStatus);
    }
  }

  async function playResponse(responseLine: Line | null) {
    if (!responseLine) {
      return;
    }
    await playItems(responsePlaybackItems(responseLine, playbackRate), {
      source: "line",
      startStatus: "Playing your line...",
      completeStatus: "Line complete."
    });
  }

  async function playCurrentCallout() {
    if (!currentCueCallout) {
      return;
    }
    stopPlayback();
    const callout = currentCueCallout;
    const calloutLineId = line?.id;
    const thisCalloutPlaybackSeq = ++calloutPlaybackSeq.current;
    setTimingStatusMessage(null);
    const didComplete = await playItems([{ kind: "audio", path: callout.audioPath, playbackRate: 1 }], {
      source: "cue",
      startStatus: `Playing callout (${callout.speaker})...`
    });
    if (!didComplete || thisCalloutPlaybackSeq !== calloutPlaybackSeq.current) {
      return;
    }
    setPlaybackStatus(line?.id === calloutLineId ? "Callout complete." : "Playback complete.");
  }

  function stopPlayback() {
    activeTimingLineIdRef.current = null;
    setTimingStatusMessage(null);
    stopPlaybackQueue();
  }

  function makeTempoTimingDetector(): VoiceActivityDetector {
    return new VoiceActivityDetector(handleVoiceActivity, {
      ...defaultTempoTimingConfig,
      endOfLineSilenceMs: tempoEndOfLineSilenceMs
    });
  }

  function changePlaybackRate(nextPlaybackRate: number) {
    const clampedPlaybackRate = clampPlaybackRate(nextPlaybackRate);
    const nextPracticeTarget = syncSpeakAlongSpeed
      ? normalizePracticeTargetPaceMultiplier(clampedPlaybackRate)
      : practiceTargetPaceMultiplier;
    setPlaybackRate(clampedPlaybackRate);
    if (syncSpeakAlongSpeed) {
      setPracticeTargetPaceMultiplier(nextPracticeTarget);
      if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
        setTimingStatusMessage(
        formatTimingAttempt(
          latestLineTimingAttempt,
          nextPracticeTarget,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent,
          absolutePickupForgivenessMs
        )
      );
      }
    }
    void saveSession(
      position.index,
      clampedPlaybackRate,
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
      nextPracticeTarget,
      syncSpeakAlongSpeed
    );
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
    const nextPlaybackRate = syncSpeakAlongSpeed ? clampPlaybackRate(normalizedMultiplier) : playbackRate;
    setPlaybackRate(nextPlaybackRate);
    setPracticeTargetPaceMultiplier(normalizedMultiplier);
    if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
      setTimingStatusMessage(
        formatTimingAttempt(
          latestLineTimingAttempt,
          normalizedMultiplier,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent,
          absolutePickupForgivenessMs
        )
      );
    }
    void saveSession(
      position.index,
      nextPlaybackRate,
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
      normalizedMultiplier,
      syncSpeakAlongSpeed
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
      nextSyncPracticeTiming,
      includeBlocking,
      blockingScope,
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed
    );
  }

  function changeSyncSpeakAlongSpeed(nextSyncSpeakAlongSpeed: boolean) {
    const nextPracticeTargetPaceMultiplier = nextSyncSpeakAlongSpeed
      ? normalizePracticeTargetPaceMultiplier(playbackRate)
      : practiceTargetPaceMultiplier;
    const nextPlaybackRate = syncSpeakAlongSpeed ? clampPlaybackRate(playbackRate) : playbackRate;
    setSyncSpeakAlongSpeed(nextSyncSpeakAlongSpeed);
    if (nextSyncSpeakAlongSpeed) {
      setPlaybackRate(nextPlaybackRate);
      setPracticeTargetPaceMultiplier(nextPracticeTargetPaceMultiplier);
      if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
        setTimingStatusMessage(
          formatTimingAttempt(
          latestLineTimingAttempt,
          nextPracticeTargetPaceMultiplier,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent,
          absolutePickupForgivenessMs
        )
      );
      }
    }
    void saveSession(
      position.index,
      nextPlaybackRate,
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
      nextPracticeTargetPaceMultiplier,
      nextSyncSpeakAlongSpeed
    );
  }

  function changeRehearsalTextSize(nextSize: RehearsalTextSize) {
    const nextRehearsalTextSize = normalizeRehearsalTextSize(nextSize);
    setRehearsalTextSize(nextRehearsalTextSize);
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      absolutePickupForgivenessMs,
      autoAdvanceMode,
      autoPlayLineMode,
      nextRehearsalTextSize,
      tempoEndOfLineSilenceMs
    );
  }

  function changeAbsoluteTempoForgiveness(nextToleranceMs: number) {
    const normalizedToleranceMs = normalizeAbsoluteTempoForgivenessMs(nextToleranceMs);
    setAbsoluteTempoForgivenessMs(normalizedToleranceMs);
    if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
      setTimingStatusMessage(
        formatTimingAttempt(
          latestLineTimingAttempt,
          practiceTargetPaceMultiplier,
          normalizedToleranceMs,
          tempoTolerancePercent,
          absolutePickupForgivenessMs
        )
      );
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      normalizedToleranceMs
    );
  }

  function changeTempoTolerancePercent(nextTempoTolerancePercent: number) {
    const normalizedTolerancePercent = normalizeTempoTolerancePercent(nextTempoTolerancePercent);
    setTempoTolerancePercent(normalizedTolerancePercent);
    if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
      setTimingStatusMessage(
        formatTimingAttempt(
          latestLineTimingAttempt,
          practiceTargetPaceMultiplier,
          absoluteTempoForgivenessMs,
          normalizedTolerancePercent,
          absolutePickupForgivenessMs
        )
      );
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      normalizedTolerancePercent
    );
  }

  function changeTempoEndOfLineSilenceMs(nextTempoEndOfLineSilenceMs: number) {
    const normalizedTempoEndOfLineSilenceMs = normalizeTempoEndOfLineSilenceMs(nextTempoEndOfLineSilenceMs);
    setTempoEndOfLineSilenceMs(normalizedTempoEndOfLineSilenceMs);
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      absolutePickupForgivenessMs,
      autoAdvanceMode,
      autoPlayLineMode,
      rehearsalTextSize,
      normalizedTempoEndOfLineSilenceMs
    );
  }

  function changeAbsolutePickupForgiveness(nextToleranceMs: number) {
    const normalizedToleranceMs = normalizeAbsolutePickupForgivenessMs(nextToleranceMs);
    setAbsolutePickupForgivenessMs(normalizedToleranceMs);
    if (line && latestLineTimingAttempt && latestLineTimingAttempt.lineId === line.id) {
      setTimingStatusMessage(
        formatTimingAttempt(
          latestLineTimingAttempt,
          practiceTargetPaceMultiplier,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent,
          normalizedToleranceMs
        )
      );
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      normalizedToleranceMs
    );
  }

  function changeAutoAdvanceMode(nextAutoAdvanceMode: AutoAdvanceMode) {
    const nextAutoPlayLineMode: AutoPlayLineMode =
      nextAutoAdvanceMode === "disabled" ? "disabled" : autoPlayLineMode;
    setAutoAdvanceMode(nextAutoAdvanceMode);
    setAutoPlayLineMode(nextAutoPlayLineMode);
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      absolutePickupForgivenessMs,
      nextAutoAdvanceMode,
      nextAutoPlayLineMode,
      rehearsalTextSize,
      tempoEndOfLineSilenceMs
    );
  }

  function changeAutoPlayLineMode(nextAutoPlayLineMode: AutoPlayLineMode) {
    const normalizedMode = autoAdvanceMode === "disabled" ? "disabled" : nextAutoPlayLineMode;
    setAutoPlayLineMode(normalizedMode);
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
      practiceTargetPaceMultiplier,
      syncSpeakAlongSpeed,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent,
      absolutePickupForgivenessMs,
      autoAdvanceMode,
      normalizedMode,
      rehearsalTextSize,
      tempoEndOfLineSilenceMs
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
    const detector = await startVoiceActivityDetector(makeTempoTimingDetector);
    if (!detector) {
      setTempoTimingEnabled(false);
      return;
    }
    activeTimingLineIdRef.current = null;
    setTempoTimingEnabled(true);
    setTempoTimingPreferred(true);
    setSpeakAlongEnabled(false);
    await saveSession(position.index, playbackRate, false, true);
  }

  async function disableTempoTiming(): Promise<void> {
    stopVoiceActivityDetector();
    activeTimingLineIdRef.current = null;
    setTempoTimingEnabled(false);
    setTempoTimingPreferred(false);
    await saveSession(position.index, playbackRate, speakAlongEnabled, false);
  }

  async function beginTimedAttempt(preserveTimingStatus = false) {
    const timingLine = currentLineFromEngine();
    if (!timingLine) {
      return;
    }
    if (!tempoTimingEnabled) {
      setPlaybackStatus("Enable Tempo timing to start timing capture.");
      setTimingStatusMessage(null);
      return;
    }
    const detector = await startVoiceActivityDetector(makeTempoTimingDetector);
    if (!detector) {
      return;
    }
    // Keep capture running for the remainder of the timing session.
    void saveSession(position.index, playbackRate, speakAlongEnabled, true, isLineRevealed);
    activeTimingLineIdRef.current = timingLine.id;
    if (!preserveTimingStatus) {
      setTimingStatusMessage(null);
    }
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
      const timingEvaluation = evaluateTempoTimingResult({
        result,
        line: timingLine,
        tempoTargetHesitationMs,
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent,
        absolutePickupForgivenessMs,
        autoAdvanceMode,
        autoPlayLineMode,
        tempoTimingEnabled,
        atEnd: engine.position().atEnd
      });
      setTimingStatusMessage(null);
      setPlaybackStatus(timingEvaluation.playbackStatus);
    } else if (result.event === "delivery-ended") {
      const timingEvaluation = evaluateTempoTimingResult({
        result,
        line: timingLine,
        tempoTargetHesitationMs,
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent,
        absolutePickupForgivenessMs,
        autoAdvanceMode,
        autoPlayLineMode,
        tempoTimingEnabled,
        atEnd: engine.position().atEnd
      });
      if (timingEvaluation.kind !== "delivery-ended") {
        return;
      }
      setTimingStatusMessage(timingEvaluation.timingStatus);
      setPlaybackStatus(timingEvaluation.playbackStatus);
      void saveTimingAttempt(timingLine.id, timingEvaluation.feedback);
      if (timingEvaluation.shouldAutoAdvance) {
        void (async () => {
          await playTimingFeedbackTone("auto-advance");
          await goNext(true, timingEvaluation.shouldAutoPlayLine, { preserveTimingStatus: true });
        })();
      } else if (timingEvaluation.shouldRepeatCue) {
        void (async () => {
          await playTimingFeedbackTone("retry");
          if (timingEvaluation.shouldAutoPlayLine) {
            await playResponse(currentLineFromEngine());
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
          await playCue({ preserveTimingStatus: true });
        })();
      }
      activeTimingLineIdRef.current = null;
    } else {
      return;
    }
  }

  function openOptionsPage() {
    void loadReviewAttempts();
    setIsOptionsPageVisible(true);
  }

  function closeOptionsPage() {
    setIsOptionsPageVisible(false);
  }

  if (isOptionsPageVisible) {
    return (
      <RehearsalOptionsScreen
        playTitle={playbook.title}
        storageStatus={storageStatus}
        onBackToRehearsal={closeOptionsPage}
        options={{
          cueWindowPresetId,
          blockingScope,
          rehearsalTextSize,
          playbackRate,
          practiceTargetPaceMultiplier,
          syncSpeakAlongSpeed,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent,
          speakAlongPauseMs,
          tempoTargetHesitationMs,
          syncPracticeTiming,
          absolutePickupForgivenessMs,
          tempoEndOfLineSilenceMs,
          autoAdvanceMode,
          autoPlayLineMode,
          onCueWindowPresetChange: changeCueWindowPreset,
          onBlockingScopeChange: changeBlockingScope,
          onRehearsalTextSizeChange: changeRehearsalTextSize,
          onPlaybackRateChange: changePlaybackRate,
          onPracticeTargetPaceMultiplierChange: changePracticeTargetPaceMultiplier,
          onSyncSpeakAlongSpeedChange: changeSyncSpeakAlongSpeed,
          onAbsoluteTempoForgivenessChange: changeAbsoluteTempoForgiveness,
          onTempoTolerancePercentChange: changeTempoTolerancePercent,
          onSpeakAlongPauseMsChange: changeSpeakAlongPauseMs,
          onTempoTargetHesitationMsChange: changeTempoTargetHesitationMs,
          onSyncPracticeTimingChange: changeSyncPracticeTiming,
          onAbsolutePickupForgivenessChange: changeAbsolutePickupForgiveness,
          onTempoEndOfLineSilenceMsChange: changeTempoEndOfLineSilenceMs,
          onAutoAdvanceModeChange: changeAutoAdvanceMode,
          onAutoPlayLineModeChange: changeAutoPlayLineMode
        }}
      />
    );
  }

  return (
    <main className="shell">
      <section className={`hero rehearsal ${rehearsalLayoutClass}`}>
        <RehearsalHeader
          playTitle={playbook.title}
          roleTitle={role.displayName}
          backLabel="Back to library."
          backTitle="Back to library."
          onBack={onBack}
          lineId={line?.id ?? null}
          isOutlineOpen={isOutlineOpen}
          onOpenOutline={() => setIsOutlineOpen(true)}
        />
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
            <RehearsalOutline
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
            <RehearsalLineWorkspace
              line={line}
              roleDisplayName={role.displayName}
              rehearsalTextSize={rehearsalTextSize}
              visibleCues={visibleCues}
              playbackSource={playbackSource}
              playbackState={playbackState}
              hasStarted={hasStarted}
              atBeginning={position.atBeginning}
              atEnd={position.atEnd}
              bookmarkNeighbors={bookmarkNeighbors}
              isCurrentLineBookmarked={isCurrentLineBookmarked}
              includeBlocking={includeBlocking}
              includeDirections={includeDirections}
              isLineRevealed={isLineRevealed}
              blockingScope={blockingScope}
              onCommand={(command) => void runCommand(command)}
              onJumpToLine={jumpToLine}
            />
          </div>
        </div>

        <RehearsalBottomBar
          playbackSource={playbackSource}
          playbackState={playbackState}
          line={line}
          playbookId={playbook.id}
          lineLengthMs={lineLengthMs}
          latestTimingTargetDeliveryMs={latestLineTimingAttempt?.targetDeliveryMs ?? null}
          tempoTimingEnabled={tempoTimingEnabled}
          speakAlongEnabled={speakAlongEnabled}
          showLinesByDefault={showLinesByDefault}
          includeBlocking={includeBlocking}
          includeDirections={includeDirections}
          isCalloutEnabled={isCalloutEnabled}
          hasCurrentLineCallout={hasCurrentLineCallout}
          currentCueCalloutSpeaker={currentCueCallout?.speaker ?? null}
          showLineInfo={showLineInfo}
          displayedPlaybackStatus={displayedPlaybackStatus}
          expandedTimingPill={expandedTimingPill}
          absoluteTempoForgivenessMs={absoluteTempoForgivenessMs}
          tempoTolerancePercent={tempoTolerancePercent}
          absolutePickupForgivenessMs={absolutePickupForgivenessMs}
          onCommand={(command) => void runCommand(command)}
          onToggleTempoTiming={() => void (tempoTimingEnabled ? disableTempoTiming() : enableTempoTiming())}
          onToggleSpeakAlong={() => changeSpeakAlongEnabled(!speakAlongEnabled)}
          onToggleShowLinesByDefault={() => changeShowLinesByDefault(!showLinesByDefault)}
          onToggleIncludeBlocking={() => changeIncludeBlocking(!includeBlocking)}
          onToggleIncludeDirections={() => changeIncludeDirections(!includeDirections)}
          onToggleCallout={() => setIsCalloutEnabled((current) => !current)}
          onToggleLineInfo={() => setShowLineInfo((current) => !current)}
          onSelectRole={onSelectRole}
          onOpenOptions={openOptionsPage}
          onToggleTimingPill={(pill) => setExpandedTimingPill((current) => (current === pill ? null : pill))}
        />
      </div>
      </section>
    </main>
  );
}

const REHEARSAL_COMPACT_MEDIA_QUERY = "(max-width: 760px), (orientation: landscape) and (max-height: 540px)";

function isCompactRehearsalViewport() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia(REHEARSAL_COMPACT_MEDIA_QUERY).matches;
}
