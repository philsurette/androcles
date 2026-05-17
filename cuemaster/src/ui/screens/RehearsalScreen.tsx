import { useEffect, useMemo, useRef, useState } from "react";
import type { Cue } from "../../domain/cue";
import type { Line } from "../../domain/line";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import type { QueueItem } from "../../rehearsal/audioQueue";
import { cueWindowPresetForId, cueWindowPresets } from "../../rehearsal/cueWindowPreset";
import { shortcutForKey } from "../../rehearsal/keyboardShortcuts";
import { buildCalloutResolverForSpeaker } from "../../rehearsal/calloutLookup";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../rehearsal/playbackItems";
import type { RehearsalCommand, RehearsalShortcut } from "../../rehearsal/rehearsalCommand";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import {
  resolveCurrentLineFromEngine,
  visibleBlockingForLine,
  visibleCuesForDisplay
} from "../../rehearsal/rehearsalPresentation";
import { deliveryLabel, tempoFeedbackFor } from "../../rehearsal/tempoFeedback";
import { defaultTargetHesitationMs, endOfLineSilenceMs, defaultTempoTimingConfig } from "../../rehearsal/tempoTimingConfig";
import {
  absolutePickupForgivenessOptionsMs,
  absoluteTempoForgivenessOptionsMs,
  clampPlaybackRate,
  deliveryPillForLabel,
  formatAbsoluteTempoForgiveness,
  formatDeliveryTimingDetails,
  formatDurationMs,
  formatPickupTimingDetails,
  formatTempoEndOfLineSilence,
  formatTempoTolerancePercent,
  formatTimingAttempt,
  formatTimingOption,
  formatTimingResult,
  normalizeAbsolutePickupForgivenessMs,
  normalizeAbsoluteTempoForgivenessMs,
  normalizePracticeTargetPaceMultiplier,
  normalizeRehearsalTextSize,
  normalizeTempoEndOfLineSilenceMs,
  normalizeTempoTolerancePercent,
  pickupPillForLabel,
  playbackRates,
  practicePaceMultiplierOptions,
  practiceTimingOptionsMs,
  rehearsalTextSizeOptions,
  tempoEndOfLineSilenceOptionsMs,
  tempoToleranceOptionsPercent,
  type RehearsalTextSize,
  type TimingLabel,
  type TimingStatusPill
} from "../../rehearsal/timingPresentation";
import { VoiceActivityDetector } from "../../rehearsal/voiceActivityDetector";
import type { VoiceActivityResult } from "../../rehearsal/voiceActivityTracker";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { CueCard } from "../components/CueCard";
import { LineCard, type BlockingScope } from "../components/LineCard";
import { PracticeSelect } from "../components/PracticeSelect";
import { RehearsalOutline, type TimingLineStatus } from "../components/RehearsalOutline";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";
import { useBookmarks } from "../hooks/useBookmarks";
import { useRehearsalPlayback } from "../hooks/useRehearsalPlayback";
import { useRehearsalSettings, type AutoAdvanceMode, type AutoPlayLineMode } from "../hooks/useRehearsalSettings";
import { useTempoTiming } from "../hooks/useTempoTiming";

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
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent,
        absolutePickupForgivenessMs
      );
      const timingResult = formatTimingResult(
        feedback,
        practiceTargetPaceMultiplier,
        absoluteTempoForgivenessMs,
        tempoTolerancePercent,
        absolutePickupForgivenessMs
      );
      setTimingStatusMessage(timingResult);
      setPlaybackStatus(timingResult.details);
      void saveTimingAttempt(timingLine.id, feedback);
      const shouldAutoAdvance =
        autoAdvanceMode === "always" ||
        (autoAdvanceMode === "on-target" && timingResult.delivery.label === "good") ||
        (autoAdvanceMode === "when-not-slow" && timingResult.delivery.label !== "slow");
      const shouldAutoPlayLine =
        autoPlayLineMode !== "disabled" &&
        autoAdvanceMode !== "disabled" &&
        (autoPlayLineMode === "always" || !shouldAutoAdvance);
      if (autoAdvanceMode !== "disabled" && tempoTimingEnabled && !engine.position().atEnd) {
        const shouldRepeatCue = (autoAdvanceMode === "on-target" || autoAdvanceMode === "when-not-slow") && !shouldAutoAdvance;
        if (shouldAutoAdvance) {
        void (async () => {
          await playTimingFeedbackTone("auto-advance");
          await goNext(true, shouldAutoPlayLine, { preserveTimingStatus: true });
        })();
        } else if (shouldRepeatCue) {
          void (async () => {
            await playTimingFeedbackTone("retry");
            if (shouldAutoPlayLine) {
              await playResponse(currentLineFromEngine());
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
            await playCue({ preserveTimingStatus: true });
          })();
        }
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

  const practiceOptionsPanel = (
      <div className="practice-options-page">
      <div className="practice-options-panel">
        <div className="practice-options-inline-row">
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Cue length
            <PracticeSelect
              label="Cue length"
              value={cueWindowPresetId}
              options={cueWindowPresets.map((preset) => ({ value: preset.id, label: preset.label }))}
              onSelect={changeCueWindowPreset}
            />
          </label>
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Blocking scope
            <PracticeSelect
              label="Blocking scope"
              value={blockingScope}
              options={[
                { value: "role", label: "My role" },
                { value: "all", label: "All roles" }
              ]}
              onSelect={(next) => changeBlockingScope(next as BlockingScope)}
            />
          </label>
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Text size
            <PracticeSelect
              label="Text size"
              value={rehearsalTextSize}
              options={rehearsalTextSizeOptions.map((option) => ({
                value: option,
                label: option
              }))}
              onSelect={(next) => changeRehearsalTextSize(next as RehearsalTextSize)}
            />
          </label>
        </div>
        <details className="timing-options timing-options-collapsible">
          <summary className="timing-options-summary">Tempo</summary>
          <div className="timing-options-controls">
            <div className="timing-targets-row">
              <div className="timing-targets-controls">
                <label className="timing-setting">
                  Speakalong
                  <PracticeSelect
                    label="Speakalong"
                    value={String(playbackRate)}
                    options={playbackRates.map((rate) => ({ value: String(rate), label: `${rate.toFixed(1)}x` }))}
                    onSelect={(next) => changePlaybackRate(Number(next))}
                  />
                </label>
                <label className="timing-setting">
                  Target adj.
                  <PracticeSelect
                    label="Target adj."
                    value={String(practiceTargetPaceMultiplier)}
                    options={practicePaceMultiplierOptions.map((optionMultiplier) => ({
                      value: String(optionMultiplier),
                      label: `${optionMultiplier.toFixed(1)}x`
                    }))}
                    onSelect={(next) => changePracticeTargetPaceMultiplier(Number(next))}
                    disabled={syncSpeakAlongSpeed}
                  />
                </label>
              </div>
              <button
                type="button"
                className={`timing-sync-toggle ${syncSpeakAlongSpeed ? "linked" : ""}`}
                aria-label={syncSpeakAlongSpeed ? "Disable speed control sync." : "Keep speed controls in sync."}
                aria-pressed={syncSpeakAlongSpeed}
                title={syncSpeakAlongSpeed ? "Unlock speed controls" : "Lock speed controls"}
                onClick={() => changeSyncSpeakAlongSpeed(!syncSpeakAlongSpeed)}
              >
                <span aria-hidden="true">{syncSpeakAlongSpeed ? "🔒" : "🔓"}</span>
              </button>
            </div>
            <label className="timing-setting">
              Forgiveness(abs)
              <PracticeSelect
                label="Forgiveness(abs)"
                value={String(absoluteTempoForgivenessMs)}
                options={absoluteTempoForgivenessOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatAbsoluteTempoForgiveness(optionMs)
                }))}
                onSelect={(next) => changeAbsoluteTempoForgiveness(Number(next))}
              />
            </label>
            <label className="timing-setting">
              Forgiveness(%)
              <PracticeSelect
                label="Forgiveness(%)"
                value={String(tempoTolerancePercent)}
                options={tempoToleranceOptionsPercent.map((optionPercent) => ({
                  value: String(optionPercent),
                  label: formatTempoTolerancePercent(optionPercent)
                }))}
                onSelect={(next) => changeTempoTolerancePercent(Number(next))}
              />
            </label>
          </div>
        </details>
        <details className="timing-options timing-options-collapsible">
          <summary className="timing-options-summary">Cue Pickup</summary>
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
                  Pickup target
                  <PracticeSelect
                    label="Pickup target"
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
                title={syncPracticeTiming ? "Unlock timing targets" : "Lock timing targets"}
                onClick={() => changeSyncPracticeTiming(!syncPracticeTiming)}
              >
                <span aria-hidden="true">{syncPracticeTiming ? "🔒" : "🔓"}</span>
              </button>
            </div>
            <label className="timing-setting">
              Forgiveness
              <PracticeSelect
                label="Forgiveness"
                value={String(absolutePickupForgivenessMs)}
                options={absolutePickupForgivenessOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatAbsoluteTempoForgiveness(optionMs)
                }))}
                onSelect={(next) => changeAbsolutePickupForgiveness(Number(next))}
              />
            </label>
            <label className="timing-setting">
              Line silence
              <PracticeSelect
                label="Line silence"
                value={String(tempoEndOfLineSilenceMs)}
                options={tempoEndOfLineSilenceOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatTempoEndOfLineSilence(optionMs)
                }))}
                onSelect={(next) => changeTempoEndOfLineSilenceMs(Number(next))}
              />
            </label>
            </div>
          </details>
          <details className="timing-options timing-options-collapsible">
            <summary className="timing-options-summary">Autoadvance</summary>
            <div className="timing-options-controls">
              <label className="timing-setting timing-setting-2x">
                Advance
                <PracticeSelect
                  label="Advance"
                  value={autoAdvanceMode}
                  options={[
                    { value: "disabled", label: "Disabled" },
                    { value: "always", label: "Always" },
                    { value: "on-target", label: "When on target" },
                    { value: "when-not-slow", label: "When not slow" }
                  ]}
                  onSelect={(next) => changeAutoAdvanceMode(next as AutoAdvanceMode)}
                />
              </label>
              <label className="timing-setting timing-setting-2x">
                Replay line
                <PracticeSelect
                  label="Replay line"
                  value={autoPlayLineMode}
                  options={[
                    { value: "disabled", label: "Disabled" },
                    { value: "always", label: "Always" },
                    { value: "off-target", label: "When off target" }
                  ]}
                  onSelect={(next) => changeAutoPlayLineMode(next as AutoPlayLineMode)}
                  disabled={autoAdvanceMode === "disabled"}
                />
              </label>
            </div>
          </details>
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
                title="Back to rehearsal"
                onClick={closeOptionsPage}
              >
                <span aria-hidden="true">←</span>
              </button>
              <div className="rehearsal-title-stack">
                <p className="rehearsal-play-title">{playbook.title}</p>
                <p className="rehearsal-role-title">Rehearse options</p>
              </div>
            </div>
          </header>
          {storageStatus ? (
            <p className="error" role="alert">
              {storageStatus}
            </p>
          ) : null}
          <div className="rehearsal-workspace no-outline options-workspace options-workspace-shell">
            <div className="practice-options-scroll">
              {practiceOptionsPanel}
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className={`hero rehearsal ${rehearsalLayoutClass}`}>
        <header className="rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary"
              aria-label="Back to library."
              title="Back to library."
              onClick={onBack}
            >
              <span aria-hidden="true">←</span>
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
                title={isOutlineOpen ? "Browse cues" : "Open cues"}
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
            {line ? (
              <div className={`rehearsal-line-layout rehearsal-text-size rehearsal-text-size-${rehearsalTextSize}`}>
                <fieldset className="cue-section-panel" aria-label={`Cue: ${visibleCues[0]?.speaker ?? role.displayName}`}>
                  <legend className="cue-section-title">{`Cue: ${visibleCues[0]?.speaker ?? role.displayName}`}</legend>
                  <section className="cue-strip" aria-label="Cue">
                    <section className="control-strip cue-control-strip" aria-label="Cue controls">
                      <div className="transport">
                        <div className="control-group transport-group cue-play-group">
                          {playbackSource === "cue" && playbackState === "playing" ? (
                            <button
                              type="button"
                              className="transport-button secondary"
                              aria-label="Pause cue playback. Shortcut: Space."
                              title="Pause cue"
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
                              title="Resume cue"
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
                              title={hasStarted ? "Replay cue" : "Play cue"}
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
                            title="Stop"
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
                            title="Previous line"
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
                            title="Next line"
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
                            title="Previous bookmark"
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
                            title={isCurrentLineBookmarked ? "Bookmarked" : "Bookmark"}
                            onClick={() => void runCommand("bookmark")}
                          >
                            <span aria-hidden="true">{isCurrentLineBookmarked ? "★" : "☆"}</span>
                          </button>
                          <button
                            type="button"
                            className="quick-toggle"
                            aria-label="Go to next bookmark."
                            title="Next bookmark"
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
                </fieldset>

                  <section className="stack" aria-label="Current cue and line">
                    <div className="rehearsal-line-content">
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
                  </div>
                </section>
              </div>
            ) : (
              <p className="empty">This role has no rehearsable lines.</p>
            )}
          </div>
        </div>

        <div className="session-settings rehearsal-bottom-strip">
          <section className="control-strip line-control-strip rehearsal-bottom-line-controls" aria-label="Line controls">
            <div className="transport">
              <div className="control-group transport-group line-playback-group">
                {playbackSource === "line" && playbackState === "playing" ? (
                  <button
                    type="button"
                    className="transport-button secondary"
                    aria-label="Pause line playback. Shortcut: Space."
                    title="Pause line"
                    onClick={() => void runCommand("pause")}
                  >
                    <span aria-hidden="true" className="transport-icon">
                      ⏸
                    </span>
                  </button>
                ) : playbackSource === "line" && playbackState === "paused" ? (
                  <button
                    type="button"
                    className="transport-button secondary"
                    aria-label="Resume line playback. Shortcut: Space."
                    title="Resume line"
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
                    aria-label="Play your line. Shortcut: L."
                    title="Play your line"
                    onClick={() => void runCommand("hear-line")}
                    disabled={!line}
                  >
                    <span aria-hidden="true" className="transport-icon">
                      ▶
                    </span>
                  </button>
                )}
                <button
                  type="button"
                  className="transport-button secondary"
                  aria-label="Stop line playback. Shortcut: Escape."
                  title="Stop line"
                  onClick={() => void runCommand("stop")}
                >
                  <span aria-hidden="true" className="transport-icon">
                    ■
                  </span>
                </button>
              </div>
            </div>
          </section>
          <div className="rehearsal-practice-toggles-inline" aria-label="Quick practice toggles">
              <button
                type="button"
                className={tempoTimingEnabled ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={tempoTimingEnabled}
                aria-label={tempoTimingEnabled ? "Disable tempo timing." : "Enable tempo timing."}
                title={tempoTimingEnabled ? "Tempo timing on" : "Tempo timing off"}
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
                title={speakAlongEnabled ? "Speak-along on" : "Speak-along off"}
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
                title={showLinesByDefault ? "Show lines on" : "Show lines off"}
                onClick={() => changeShowLinesByDefault(!showLinesByDefault)}
              >
              <span aria-hidden="true">👁</span>
            </button>
              <button
                type="button"
                className={includeBlocking ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={includeBlocking}
                aria-label={includeBlocking ? "Hide blocking." : "Show blocking."}
                title={includeBlocking ? "Blocking on" : "Blocking off"}
                onClick={() => changeIncludeBlocking(!includeBlocking)}
              >
              <span aria-hidden="true">♿</span>
            </button>
              <button
                type="button"
                className={includeDirections ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={includeDirections}
                aria-label={includeDirections ? "Hide stage directions." : "Show stage directions."}
                title={includeDirections ? "Directions on" : "Directions off"}
                onClick={() => changeIncludeDirections(!includeDirections)}
              >
              <span aria-hidden="true">⌞⌝</span>
            </button>
              <button
                type="button"
                className={`quick-toggle${isCalloutEnabled ? " active" : ""}`}
                aria-pressed={isCalloutEnabled}
                aria-label={isCalloutEnabled ? "Disable cue callouts." : "Enable cue callouts."}
                title={hasCurrentLineCallout
                  ? (isCalloutEnabled ? `Callouts enabled (${currentCueCallout?.speaker})` : `Callouts disabled (${currentCueCallout?.speaker})`)
                  : "No callout for this cue"}
                onClick={() => {
                  setIsCalloutEnabled((current) => !current);
                }}
              >
                <span aria-hidden="true">📢</span>
              </button>
          </div>
          <div className="rehearsal-quick-actions">
              <button
                type="button"
                className="quick-toggle"
                aria-label={showLineInfo ? "Hide line info." : "Show line info."}
                aria-pressed={showLineInfo}
                title="Line info"
                onClick={() => setShowLineInfo((current) => !current)}
              >
              <span aria-hidden="true">ⓘ</span>
            </button>
              <button
                type="button"
                className="quick-toggle"
                aria-label="Choose role."
                title="Choose role."
                onClick={onSelectRole}
              >
              <span aria-hidden="true">🎭</span>
            </button>
              <button
                type="button"
                className="quick-toggle rehearsal-options-button"
                aria-label="Open options"
                title="Options"
                onClick={openOptionsPage}
              >
              <span aria-hidden="true">⚙</span>
            </button>
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
                      {formatDeliveryTimingDetails(
                        displayedPlaybackStatus.delivery.measuredMs,
                        displayedPlaybackStatus.delivery.targetMs,
                        absoluteTempoForgivenessMs,
                        tempoTolerancePercent
                      )}
                    </span>
                  ) : null}
                  {expandedTimingPill === "pickup" ? (
                    <span className="timing-status-details">
                      {formatPickupTimingDetails(
                        displayedPlaybackStatus.pickup.measuredMs,
                        displayedPlaybackStatus.pickup.targetMs,
                        absolutePickupForgivenessMs
                      )}
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

const REHEARSAL_COMPACT_MEDIA_QUERY = "(max-width: 760px), (orientation: landscape) and (max-height: 540px)";

function isCompactRehearsalViewport() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia(REHEARSAL_COMPACT_MEDIA_QUERY).matches;
}
