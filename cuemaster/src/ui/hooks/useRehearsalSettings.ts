import { useState } from "react";
import type { RehearsalSession } from "../../domain/session";
import { cueWindowPresetForId } from "../../rehearsal/cueWindowPreset";
import { defaultTargetHesitationMs, endOfLineSilenceMs } from "../../rehearsal/tempoTimingConfig";
import {
  clampPlaybackRate,
  normalizeAbsolutePickupForgivenessMs,
  normalizeAbsoluteTempoForgivenessMs,
  normalizePracticeTargetPaceMultiplier,
  normalizeRehearsalTextSize,
  normalizeTempoEndOfLineSilenceMs,
  normalizeTempoTolerancePercent
} from "../../rehearsal/timingPresentation";
import type { BlockingScope } from "../components/LineCard";

export type AutoAdvanceMode = "disabled" | "always" | "on-target" | "when-not-slow";
export type AutoPlayLineMode = "disabled" | "always" | "off-target";

export function useRehearsalSettings(initialSession: RehearsalSession | null, initialIncludeDirections: boolean) {
  const initialAutoAdvanceMode = initialSession?.autoAdvanceMode ??
    (initialSession?.autoAdvanceOnGoodTempo ? "on-target" : "disabled");
  const [playbackRate, setPlaybackRate] = useState(clampPlaybackRate(initialSession?.playbackRate ?? 1));
  const [cueWindowPresetId, setCueWindowPresetId] = useState(
    cueWindowPresetForId(initialSession?.cueWindowPresetId).id
  );
  const [showLinesByDefault, setShowLinesByDefault] = useState(
    initialSession?.showLinesByDefault ?? initialSession?.revealLine ?? false
  );
  const [isLineRevealed, setIsLineRevealed] = useState(
    initialSession?.showLinesByDefault ?? initialSession?.revealLine ?? false
  );
  const [includeDirections, setIncludeDirections] = useState(initialIncludeDirections);
  const [includeBlocking, setIncludeBlocking] = useState(initialSession?.includeBlocking ?? true);
  const [blockingScope, setBlockingScope] = useState<BlockingScope>(initialSession?.blockingScope ?? "role");
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
  const [syncSpeakAlongSpeed, setSyncSpeakAlongSpeed] = useState(initialSession?.syncSpeakAlongSpeed ?? true);
  const [rehearsalTextSize, setRehearsalTextSize] = useState(normalizeRehearsalTextSize(initialSession?.rehearsalTextSize));
  const [absoluteTempoForgivenessMs, setAbsoluteTempoForgivenessMs] = useState(
    normalizeAbsoluteTempoForgivenessMs(initialSession?.absoluteTempoForgivenessMs)
  );
  const [absolutePickupForgivenessMs, setAbsolutePickupForgivenessMs] = useState(
    normalizeAbsolutePickupForgivenessMs(initialSession?.absolutePickupForgivenessMs)
  );
  const [autoAdvanceMode, setAutoAdvanceMode] = useState<AutoAdvanceMode>(
    initialAutoAdvanceMode
  );
  const [autoPlayLineMode, setAutoPlayLineMode] = useState<AutoPlayLineMode>(
    initialAutoAdvanceMode === "disabled" ? "disabled" : (initialSession?.autoPlayLineMode ?? "disabled")
  );
  const [tempoTolerancePercent, setTempoTolerancePercent] = useState(
    normalizeTempoTolerancePercent(initialSession?.tempoTolerancePercent)
  );
  const [tempoEndOfLineSilenceMs, setTempoEndOfLineSilenceMs] = useState(
    normalizeTempoEndOfLineSilenceMs(initialSession?.tempoEndOfLineSilenceMs ?? endOfLineSilenceMs)
  );
  const [tempoTimingEnabled, setTempoTimingEnabled] = useState(initialSession?.tempoTimingPreferred ?? false);
  const [tempoTimingPreferred, setTempoTimingPreferred] = useState(initialSession?.tempoTimingPreferred ?? false);

  return {
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
  };
}
