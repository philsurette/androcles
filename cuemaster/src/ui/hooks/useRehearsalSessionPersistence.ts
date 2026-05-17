import type { RehearsalTextSize } from "../../rehearsal/timingPresentation";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import type { BlockingScope } from "../components/LineCard";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";
import type { AutoAdvanceMode, AutoPlayLineMode } from "./useRehearsalSettings";

type UseRehearsalSessionPersistenceProps = {
  playbookId: string;
  roleId: string;
  playbackRate: number;
  speakAlongEnabled: boolean;
  tempoTimingPreferred: boolean;
  isLineRevealed: boolean;
  cueWindowPresetId: string;
  includeDirections: boolean;
  showLinesByDefault: boolean;
  speakAlongPauseMs: number;
  tempoTargetHesitationMs: number;
  syncPracticeTiming: boolean;
  includeBlocking: boolean;
  blockingScope: BlockingScope;
  practiceTargetPaceMultiplier: number;
  syncSpeakAlongSpeed: boolean;
  absoluteTempoForgivenessMs: number;
  tempoTolerancePercent: number;
  absolutePickupForgivenessMs: number;
  autoAdvanceMode: AutoAdvanceMode;
  autoPlayLineMode: AutoPlayLineMode;
  rehearsalTextSize: RehearsalTextSize;
  tempoEndOfLineSilenceMs: number;
  onStorageStatus: (message: string) => void;
};

export function useRehearsalSessionPersistence({
  playbookId,
  roleId,
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
  tempoEndOfLineSilenceMs,
  onStorageStatus
}: UseRehearsalSessionPersistenceProps) {
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
        playbookId,
        roleId,
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
      onStorageStatus("");
    } catch (error) {
      onStorageStatus(userFacingErrorMessage(error));
    }
  }

  return {
    saveSession
  };
}
