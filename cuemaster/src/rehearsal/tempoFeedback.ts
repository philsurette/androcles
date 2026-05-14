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

export function hesitationLabel(
  measuredMs: number,
  targetMs: number,
  absolutePickupForgivenessMs = 250
): TempoFeedback["hesitation"]["label"] {
  const normalizedPickupForgivenessMs = Number.isFinite(absolutePickupForgivenessMs)
    ? Math.max(0, absolutePickupForgivenessMs)
    : 250;
  const fastPickupMs = Math.round(normalizedPickupForgivenessMs * 0.8);
  const slowPickupMs = Math.max(0, normalizedPickupForgivenessMs);

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
  targetPaceMultiplier = 1,
  absoluteTempoForgivenessMs = 0,
  tempoTolerancePercent = 0.2
): NonNullable<TempoFeedback["delivery"]>["label"] {
  const normalizedMultiplier = Number.isFinite(targetPaceMultiplier) && targetPaceMultiplier > 0 ? targetPaceMultiplier : 1;
  const adjustedTargetMs = targetMs / normalizedMultiplier;
  const normalizedAbsoluteForgivenessMs = Math.max(0, Number.isFinite(absoluteTempoForgivenessMs) ? absoluteTempoForgivenessMs : 0);
  const normalizedTolerancePercent = Number.isFinite(tempoTolerancePercent) ? Math.min(0.3, Math.max(0.05, tempoTolerancePercent)) : 0.2;
  const slowThresholdMs = 500;
  const toleranceMs = adjustedTargetMs * normalizedTolerancePercent;
  const forgivenessThresholdMs = Math.max(normalizedAbsoluteForgivenessMs, toleranceMs);
  if (adjustedTargetMs <= 0) {
    return "close";
  }
  if (Math.abs(adjustedTargetMs - measuredMs) <= forgivenessThresholdMs) {
    return "close";
  }
  const fastBoundaryMs = adjustedTargetMs * (1 - normalizedTolerancePercent);
  const slowBoundaryMs = adjustedTargetMs * (1 + normalizedTolerancePercent);
  if (measuredMs < fastBoundaryMs && adjustedTargetMs - measuredMs >= slowThresholdMs) {
    return "fast";
  }
  if (measuredMs > slowBoundaryMs && measuredMs - adjustedTargetMs >= slowThresholdMs) {
    return "slow";
  }
  return "close";
}

export function tempoFeedbackFor(
  line: Line,
  measured: { hesitationMs: number; deliveryMs?: number },
  targetHesitationMs?: number,
  targetPaceMultiplier = 1,
  absoluteTempoForgivenessMs = 0,
  tempoTolerancePercent = 0.2,
  absolutePickupForgivenessMs = 250
): TempoFeedback {
  const targets = timingTargetsForLine(line, targetHesitationMs);
  const normalizedMultiplier = Number.isFinite(targetPaceMultiplier) && targetPaceMultiplier > 0 ? targetPaceMultiplier : 1;
  return {
    hesitation: {
      measuredMs: measured.hesitationMs,
      targetMs: targets.targetHesitationMs,
      label: hesitationLabel(
        measured.hesitationMs,
        targets.targetHesitationMs,
        absolutePickupForgivenessMs
      )
    },
    delivery:
      measured.deliveryMs === undefined
      ? undefined
      : {
          measuredMs: measured.deliveryMs,
          targetMs: targets.targetDeliveryMs,
          label: deliveryLabel(
            measured.deliveryMs,
            targets.targetDeliveryMs,
            normalizedMultiplier,
            absoluteTempoForgivenessMs,
            tempoTolerancePercent
          )
        }
  };
}
