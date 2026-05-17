import { useEffect, useRef, useState } from "react";
import type { TimingAttempt } from "../../domain/timingAttempt";
import type { TempoFeedback } from "../../rehearsal/tempoFeedback";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

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
