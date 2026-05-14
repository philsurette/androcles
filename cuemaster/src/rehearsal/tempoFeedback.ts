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
  const fastPickupMs = 200;
  const slowPickupMs = 250;

  if (targetMs <= 0) {
    return "close";
  }
  if (targetMs - measuredMs > fastPickupMs) {
    return "sharp";
  }
  if (measuredMs - targetMs > slowPickupMs) {
    return "late";
  }
  return "close";
}

export function deliveryLabel(
  measuredMs: number,
  targetMs: number,
  targetPaceMultiplier = 1
): NonNullable<TempoFeedback["delivery"]>["label"] {
  const normalizedMultiplier = Number.isFinite(targetPaceMultiplier) && targetPaceMultiplier > 0 ? targetPaceMultiplier : 1;
  const adjustedTargetMs = targetMs / normalizedMultiplier;
  const slowThresholdMs = 500;
  if (adjustedTargetMs <= 0) {
    return "close";
  }
  if (measuredMs < adjustedTargetMs * 0.8 && adjustedTargetMs - measuredMs >= slowThresholdMs) {
    return "fast";
  }
  if (measuredMs > adjustedTargetMs * 1.25 && measuredMs - adjustedTargetMs >= slowThresholdMs) {
    return "slow";
  }
  return "close";
}

export function tempoFeedbackFor(
  line: Line,
  measured: { hesitationMs: number; deliveryMs?: number },
  targetHesitationMs?: number,
  targetPaceMultiplier = 1
): TempoFeedback {
  const targets = timingTargetsForLine(line, targetHesitationMs);
  const normalizedMultiplier = Number.isFinite(targetPaceMultiplier) && targetPaceMultiplier > 0 ? targetPaceMultiplier : 1;
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
            label: deliveryLabel(measured.deliveryMs, targets.targetDeliveryMs, normalizedMultiplier)
          }
  };
}
