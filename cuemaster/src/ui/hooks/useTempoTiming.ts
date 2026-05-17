import { useEffect, useRef } from "react";

export type TimingFeedbackTone = "auto-advance" | "retry";

export function useTempoTiming() {
  const timingToneAudioContextRef = useRef<AudioContext | null>(null);

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

  return {
    playTimingFeedbackTone
  };
}
