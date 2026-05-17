import { useEffect, useRef, useState } from "react";
import type { Line } from "../../domain/line";
import type { TimingAttempt } from "../../domain/timingAttempt";
import { tempoFeedbackFor, type TempoFeedback } from "../../rehearsal/tempoFeedback";
import { formatTimingResult, type TimingStatusPill } from "../../rehearsal/timingPresentation";
import type { VoiceActivityResult } from "../../rehearsal/voiceActivityTracker";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";
import type { AutoAdvanceMode, AutoPlayLineMode } from "./useRehearsalSettings";

export type TimingFeedbackTone = "auto-advance" | "retry";
export type TempoTimingDetector = {
  start(): Promise<void>;
  stop(): void;
  beginAttempt(): void;
};

type UseTempoTimingProps = {
  playbookId: string;
  roleId: string;
  onStorageStatus: (message: string) => void;
};

type TempoTimingEvaluationOptions = {
  result: VoiceActivityResult;
  line: Line;
  tempoTargetHesitationMs: number;
  practiceTargetPaceMultiplier: number;
  absoluteTempoForgivenessMs: number;
  tempoTolerancePercent: number;
  absolutePickupForgivenessMs: number;
  autoAdvanceMode: AutoAdvanceMode;
  autoPlayLineMode: AutoPlayLineMode;
  tempoTimingEnabled: boolean;
  atEnd: boolean;
};

export type TempoTimingEvaluation =
  | {
      kind: "speech-started";
      playbackStatus: string;
    }
  | {
      kind: "delivery-ended";
      feedback: TempoFeedback;
      timingStatus: TimingStatusPill;
      playbackStatus: string;
      shouldAutoAdvance: boolean;
      shouldAutoPlayLine: boolean;
      shouldRepeatCue: boolean;
    };

export function useTempoTiming(props?: UseTempoTimingProps) {
  const timingToneAudioContextRef = useRef<AudioContext | null>(null);
  const voiceActivityDetectorRef = useRef<TempoTimingDetector | null>(null);
  const [reviewAttempts, setReviewAttempts] = useState<TimingAttempt[]>([]);

  useEffect(() => {
    return () => {
      const toneContext = timingToneAudioContextRef.current;
      if (!toneContext) {
        return;
      }
      void toneContext.close();
      timingToneAudioContextRef.current = null;
    };
  }, []);

  useEffect(() => {
    return () => {
      voiceActivityDetectorRef.current?.stop();
      voiceActivityDetectorRef.current = null;
    };
  }, []);

  async function startVoiceActivityDetector(createDetector: () => TempoTimingDetector): Promise<TempoTimingDetector | null> {
    const detector = createDetector();
    try {
      await detector.start();
      voiceActivityDetectorRef.current?.stop();
      voiceActivityDetectorRef.current = detector;
      return detector;
    } catch (error) {
      detector.stop();
      props?.onStorageStatus(userFacingErrorMessage(error));
      return null;
    }
  }

  function stopVoiceActivityDetector() {
    voiceActivityDetectorRef.current?.stop();
    voiceActivityDetectorRef.current = null;
  }

  function getTimingToneAudioContext(): AudioContext | null {
    if (typeof window === "undefined") {
      return null;
    }

    const audioContextConstructor =
      window.AudioContext ??
      (window as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext ??
      null;
    if (!audioContextConstructor) {
      return null;
    }

    if (!timingToneAudioContextRef.current) {
      timingToneAudioContextRef.current = new audioContextConstructor();
    }

    return timingToneAudioContextRef.current;
  }

  async function playTimingFeedbackTone(kind: TimingFeedbackTone): Promise<void> {
    const context = getTimingToneAudioContext();
    if (!context) {
      return;
    }

    if (context.state === "suspended") {
      try {
        await context.resume();
      } catch (_error) {
        return;
      }
    }

    const now = context.currentTime;
    const pattern =
      kind === "auto-advance"
        ? [
            { frequency: 640, durationMs: 120, gapMs: 35, volume: 0.06 },
            { frequency: 860, durationMs: 120, gapMs: 0, volume: 0.06 }
          ]
        : [{ frequency: 260, durationMs: 210, gapMs: 0, volume: 0.06 }];
    let cursor = now;

    for (const tone of pattern) {
      if (context.state !== "running") {
        break;
      }

      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const start = cursor;
      const end = start + tone.durationMs / 1000;

      oscillator.type = "triangle";
      oscillator.frequency.setValueAtTime(tone.frequency, start);
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(tone.volume, start + 0.015);
      gain.gain.linearRampToValueAtTime(0, end);

      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(start);
      oscillator.stop(end + 0.03);

      cursor = end + tone.gapMs / 1000;
    }

    await new Promise((resolve) => setTimeout(resolve, cursor - now + 40));
  }

  async function saveTimingAttempt(lineId: string, feedback: TempoFeedback) {
    if (!feedback.delivery || !props) {
      return;
    }
    const attempt: TimingAttempt = {
      id: crypto.randomUUID(),
      playbookId: props.playbookId,
      roleId: props.roleId,
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
      props.onStorageStatus("");
      await loadReviewAttempts();
    } catch (error) {
      props.onStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadReviewAttempts() {
    if (!props) {
      setReviewAttempts([]);
      return;
    }
    try {
      setReviewAttempts(await indexedDbStorage.timingAttempts.latestForRole(props.playbookId, props.roleId));
    } catch (error) {
      setReviewAttempts([]);
      props.onStorageStatus(userFacingErrorMessage(error));
    }
  }

  return {
    reviewAttempts,
    startVoiceActivityDetector,
    stopVoiceActivityDetector,
    loadReviewAttempts,
    saveTimingAttempt,
    playTimingFeedbackTone
  };
}

export function evaluateTempoTimingResult({
  result,
  line,
  tempoTargetHesitationMs,
  practiceTargetPaceMultiplier,
  absoluteTempoForgivenessMs,
  tempoTolerancePercent,
  absolutePickupForgivenessMs,
  autoAdvanceMode,
  autoPlayLineMode,
  tempoTimingEnabled,
  atEnd
}: TempoTimingEvaluationOptions): TempoTimingEvaluation {
  if (result.event === "speech-started") {
    const hesitationMs = Math.round(result.hesitationMs ?? 0);
    return {
      kind: "speech-started",
      playbackStatus: `Speech detected${hesitationMs > 0 ? ` (${hesitationMs}ms pause)` : ""}.`
    };
  }

  const hesitationMs = Math.round(result.hesitationMs ?? 0);
  const deliveryMs = Math.max(0, Math.round(result.deliveryMs ?? 0));
  const feedback = tempoFeedbackFor(
    line,
    { hesitationMs, deliveryMs },
    tempoTargetHesitationMs,
    practiceTargetPaceMultiplier,
    absoluteTempoForgivenessMs,
    tempoTolerancePercent,
    absolutePickupForgivenessMs
  );
  const timingStatus = formatTimingResult(
    feedback,
    practiceTargetPaceMultiplier,
    absoluteTempoForgivenessMs,
    tempoTolerancePercent,
    absolutePickupForgivenessMs
  );
  const shouldAutoAdvance =
    autoAdvanceMode === "always" ||
    (autoAdvanceMode === "on-target" && timingStatus.delivery.label === "good") ||
    (autoAdvanceMode === "when-not-slow" && timingStatus.delivery.label !== "slow");
  const shouldAutoPlayLine =
    autoPlayLineMode !== "disabled" &&
    autoAdvanceMode !== "disabled" &&
    (autoPlayLineMode === "always" || !shouldAutoAdvance);
  const shouldRepeatCue =
    autoAdvanceMode !== "disabled" &&
    tempoTimingEnabled &&
    !atEnd &&
    (autoAdvanceMode === "on-target" || autoAdvanceMode === "when-not-slow") &&
    !shouldAutoAdvance;

  return {
    kind: "delivery-ended",
    feedback,
    timingStatus,
    playbackStatus: timingStatus.details,
    shouldAutoAdvance: autoAdvanceMode !== "disabled" && tempoTimingEnabled && !atEnd && shouldAutoAdvance,
    shouldAutoPlayLine,
    shouldRepeatCue
  };
}
