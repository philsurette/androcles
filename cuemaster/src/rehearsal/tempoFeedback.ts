import type { Line } from "../domain/line";
import { defaultTargetHesitationMs } from "./tempoTimingConfig";

export type TempoTimingTargets = {
  targetHesitationMs: number;
  targetDeliveryMs: number;
};

export type TempoFeedback = {
  hesitation: {
    measuredMs: number;
    targetMs: number;
    label: "sharp" | "close" | "late";
  };
  delivery?: {
    measuredMs: number;
    targetMs: number;
    label: "fast" | "close" | "slow";
  };
};

export function timingTargetsForLine(line: Line, targetHesitationMs = line.timing?.targetHesitationMs ?? defaultTargetHesitationMs): TempoTimingTargets {
  return {
    targetHesitationMs,
    targetDeliveryMs: line.responseSegments.reduce((total, segment) => total + segment.durationMs, 0)
  };
}

export function hesitationLabel(measuredMs: number, targetMs: number): TempoFeedback["hesitation"]["label"] {
  if (measuredMs < targetMs * 0.6) {
    return "sharp";
  }
  if (measuredMs > targetMs * 1.4) {
    return "late";
  }
  return "close";
}

export function deliveryLabel(measuredMs: number, targetMs: number): NonNullable<TempoFeedback["delivery"]>["label"] {
  if (targetMs <= 0) {
    return "close";
  }
  if (measuredMs < targetMs * 0.8) {
    return "fast";
  }
  if (measuredMs > targetMs * 1.2) {
    return "slow";
  }
  return "close";
}

export function tempoFeedbackFor(
  line: Line,
  measured: { hesitationMs: number; deliveryMs?: number },
  targetHesitationMs?: number
): TempoFeedback {
  const targets = timingTargetsForLine(line, targetHesitationMs);
  return {
    hesitation: {
      measuredMs: measured.hesitationMs,
      targetMs: targets.targetHesitationMs,
      label: hesitationLabel(measured.hesitationMs, targets.targetHesitationMs)
    },
    delivery:
      measured.deliveryMs === undefined
        ? undefined
        : {
            measuredMs: measured.deliveryMs,
            targetMs: targets.targetDeliveryMs,
            label: deliveryLabel(measured.deliveryMs, targets.targetDeliveryMs)
          }
  };
}
