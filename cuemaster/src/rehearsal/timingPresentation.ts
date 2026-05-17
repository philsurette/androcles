import type { TimingAttempt } from "../domain/timingAttempt";
import { deliveryLabel, tempoFeedbackFor } from "./tempoFeedback";
import { endOfLineSilenceMs } from "./tempoTimingConfig";

export type TimingLabel = "fast" | "slow" | "good";

export type TimingStatusPill = {
  delivery: {
    label: TimingLabel;
    measuredMs: number;
    targetMs: number;
  };
  pickup: {
    label: TimingLabel;
    measuredMs: number;
    targetMs: number;
  };
  details: string;
};

export type RehearsalTextSize = "small" | "medium" | "large" | "x-large";

export function formatTimingResult(
  feedback: ReturnType<typeof tempoFeedbackFor>,
  practiceTargetPaceMultiplier = 1,
  absoluteTempoForgivenessMs = 500,
  tempoTolerancePercent = 0.2,
  absolutePickupForgivenessMs = 250
): TimingStatusPill {
  const normalizedPracticeTargetPaceMultiplier = normalizePracticeTargetPaceMultiplier(practiceTargetPaceMultiplier);
  const displayedDeliveryLabel =
    feedback.delivery === undefined
      ? "good"
      : deliveryLabel(
          feedback.delivery.measuredMs,
          feedback.delivery.targetMs,
          normalizedPracticeTargetPaceMultiplier,
          absoluteTempoForgivenessMs,
          tempoTolerancePercent
        ) === "fast"
        ? "fast"
        : feedback.delivery.label === "slow"
          ? "slow"
          : "good";
  const pickupLabel = feedback.hesitation.label === "sharp" ? "fast" : feedback.hesitation.label === "late" ? "slow" : "good";
  const measuredDeliveryMs = feedback.delivery?.measuredMs ?? 0;
  const baseTargetDeliveryMs = feedback.delivery?.targetMs ?? 0;
  const targetDeliveryMs = baseTargetDeliveryMs / normalizedPracticeTargetPaceMultiplier;
  const measuredPickupMs = feedback.hesitation.measuredMs;
  const targetPickupMs = feedback.hesitation.targetMs;
  return {
    delivery: {
      label: displayedDeliveryLabel,
      measuredMs: measuredDeliveryMs,
      targetMs: targetDeliveryMs
    },
    pickup: {
      label: pickupLabel,
      measuredMs: measuredPickupMs,
      targetMs: targetPickupMs
    },
    details: `${formatDeliveryTimingDetails(
      measuredDeliveryMs,
      targetDeliveryMs,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent
    )}; ${formatPickupTimingDetails(
      measuredPickupMs,
      targetPickupMs,
      absolutePickupForgivenessMs
    )}`
  };
}

export function formatTimingAttempt(
  attempt: TimingAttempt,
  practiceTargetPaceMultiplier = 1,
  absoluteTempoForgivenessMs = 500,
  tempoTolerancePercent = 0.2,
  absolutePickupForgivenessMs = 250
): TimingStatusPill {
  const normalizedPracticeTargetPaceMultiplier = normalizePracticeTargetPaceMultiplier(practiceTargetPaceMultiplier);
  const targetDeliveryMs = attempt.targetDeliveryMs / normalizedPracticeTargetPaceMultiplier;
  const lineDeliveryLabel = deliveryLabel(
    attempt.deliveryMs,
    attempt.targetDeliveryMs,
    normalizedPracticeTargetPaceMultiplier,
    absoluteTempoForgivenessMs,
    tempoTolerancePercent
  );
  const displayDeliveryLabel = lineDeliveryLabel === "fast" ? "fast" : lineDeliveryLabel === "slow" ? "slow" : "good";
  const pickupLabel = pickupLabelForFeedback(
    attempt.hesitationMs,
    attempt.targetHesitationMs,
    absolutePickupForgivenessMs
  );
  return {
    delivery: {
      label: displayDeliveryLabel,
      measuredMs: attempt.deliveryMs,
      targetMs: targetDeliveryMs
    },
    pickup: {
      label: pickupLabel,
      measuredMs: attempt.hesitationMs,
      targetMs: attempt.targetHesitationMs
    },
    details: `${formatDeliveryTimingDetails(
      attempt.deliveryMs,
      targetDeliveryMs,
      absoluteTempoForgivenessMs,
      tempoTolerancePercent
    )}; ${formatPickupTimingDetails(attempt.hesitationMs, attempt.targetHesitationMs, absolutePickupForgivenessMs)}`
  };
}

export function deliveryPillForLabel(label: TimingLabel): string {
  if (label === "fast") {
    return "🐇";
  }
  if (label === "slow") {
    return "🐢";
  }
  return "🎯";
}

export function pickupPillForLabel(label: TimingLabel): string {
  if (label === "fast") {
    return "🐇";
  }
  if (label === "slow") {
    return "🐢";
  }
  return "🎯";
}

export function formatDurationMs(durationMs: number): string {
  return `${(Math.max(0, durationMs) / 1000).toFixed(2)}s`;
}

export function formatTimingOption(optionMs: number): string {
  return `${(optionMs / 1000).toFixed(optionMs % 1000 === 0 ? 0 : 2)}s`;
}

export function formatAbsoluteTempoForgiveness(optionMs: number): string {
  const seconds = (optionMs / 1000).toFixed(2).replace(/\.?0+$/, "");
  return `±${seconds}s`;
}

export function formatTempoTolerancePercent(optionPercent: number): string {
  return `±${(optionPercent * 100).toFixed(0)}%`;
}

export function formatTempoEndOfLineSilence(optionMs: number): string {
  return `${(optionMs / 1000).toFixed(1)}s`;
}

export function clampPlaybackRate(playbackRate: number): number {
  const roundedPlaybackRate = Math.round(playbackRate * 10) / 10;
  return Math.min(maxPlaybackRate, Math.max(minPlaybackRate, roundedPlaybackRate));
}

export function normalizePracticeTargetPaceMultiplier(value: number | undefined): number {
  const parsedValue = value ?? 1;
  if (!Number.isFinite(parsedValue)) {
    return 1;
  }
  return Math.min(maxPracticeTargetPaceMultiplier, Math.max(minPracticeTargetPaceMultiplier, parsedValue));
}

export function normalizeRehearsalTextSize(value: string | undefined): RehearsalTextSize {
  if (value === "small" || value === "large" || value === "x-large") {
    return value;
  }
  return "medium";
}

export function normalizeAbsoluteTempoForgivenessMs(value: number | undefined): number {
  const parsedValue = value ?? 500;
  if (!Number.isFinite(parsedValue)) {
    return 500;
  }
  return Math.min(maxAbsoluteTempoForgivenessMs, Math.max(minAbsoluteTempoForgivenessMs, parsedValue));
}

export function normalizeAbsolutePickupForgivenessMs(value: number | undefined): number {
  const parsedValue = value ?? 250;
  if (!Number.isFinite(parsedValue)) {
    return 250;
  }
  return Math.min(maxAbsolutePickupForgivenessMs, Math.max(minAbsolutePickupForgivenessMs, parsedValue));
}

export function normalizeTempoTolerancePercent(value: number | undefined): number {
  const parsedValue = value ?? 0.2;
  if (!Number.isFinite(parsedValue)) {
    return 0.2;
  }
  return Math.min(maxTempoTolerancePercent, Math.max(minTempoTolerancePercent, parsedValue));
}

export function normalizeTempoEndOfLineSilenceMs(value: number | undefined): number {
  const parsedValue = value ?? endOfLineSilenceMs;
  if (!Number.isFinite(parsedValue)) {
    return endOfLineSilenceMs;
  }
  const quantizedValue = Math.round(parsedValue / tempoEndOfLineSilenceStepMs) * tempoEndOfLineSilenceStepMs;
  return Math.min(maxTempoEndOfLineSilenceMs, Math.max(minTempoEndOfLineSilenceMs, quantizedValue));
}

export function formatDeliveryTimingDetails(
  measuredMs: number,
  targetMs: number,
  absoluteTempoForgivenessMs: number,
  tempoTolerancePercent: number
): string {
  if (targetMs <= 0) {
    return `${(measuredMs / 1000).toFixed(2)}s (target unavailable)`;
  }
  const normalizedTolerancePercent = Number.isFinite(tempoTolerancePercent)
    ? Math.min(maxTempoTolerancePercent, Math.max(minTempoTolerancePercent, tempoTolerancePercent))
    : 0.2;
  const absoluteForgivenessMs = Number.isFinite(absoluteTempoForgivenessMs) ? Math.max(0, absoluteTempoForgivenessMs) : 0;
  const toleranceMs = targetMs * normalizedTolerancePercent;
  const forgivenessMs = Math.max(absoluteForgivenessMs, toleranceMs);
  const minMs = Math.max(0, targetMs - forgivenessMs);
  const maxMs = targetMs + forgivenessMs;
  return `${(measuredMs / 1000).toFixed(2)}s (target: ${(minMs / 1000).toFixed(2)}s - ${(maxMs / 1000).toFixed(2)}s)`;
}

export function formatPickupTimingDetails(
  measuredMs: number,
  targetMs: number,
  absolutePickupForgivenessMs: number
): string {
  if (targetMs <= 0) {
    return `${(measuredMs / 1000).toFixed(2)}s (target unavailable)`;
  }
  const absoluteForgivenessMs = Number.isFinite(absolutePickupForgivenessMs)
    ? Math.max(0, absolutePickupForgivenessMs)
    : 250;
  const minMs = Math.max(0, targetMs - absoluteForgivenessMs);
  const maxMs = targetMs + absoluteForgivenessMs;
  return `${(measuredMs / 1000).toFixed(2)}s (target: ${(minMs / 1000).toFixed(2)}s - ${(maxMs / 1000).toFixed(2)}s)`;
}

function pickupLabelForFeedback(
  measuredMs: number,
  targetMs: number,
  absolutePickupForgivenessMs: number
): TimingLabel {
  const normalizedForgivenessMs = Number.isFinite(absolutePickupForgivenessMs)
    ? Math.max(0, absolutePickupForgivenessMs)
    : 250;
  const fastToleranceMs = Math.round(normalizedForgivenessMs * 0.8);
  if (targetMs <= 0) {
    return "good";
  }
  if (targetMs - measuredMs > fastToleranceMs) {
    return "fast";
  }
  if (measuredMs - targetMs > normalizedForgivenessMs) {
    return "slow";
  }
  return "good";
}

export const minPlaybackRate = 0.4;
export const maxPlaybackRate = 1.3;
export const minPracticeTargetPaceMultiplier = 0.4;
export const maxPracticeTargetPaceMultiplier = 1.3;
export const minAbsoluteTempoForgivenessMs = 100;
export const maxAbsoluteTempoForgivenessMs = 1000;
export const minAbsolutePickupForgivenessMs = 50;
export const maxAbsolutePickupForgivenessMs = 500;
export const minTempoTolerancePercent = 0.05;
export const maxTempoTolerancePercent = 0.3;
export const minTempoEndOfLineSilenceMs = 1000;
export const maxTempoEndOfLineSilenceMs = 3000;
const tempoEndOfLineSilenceStepMs = 500;
export const absoluteTempoForgivenessOptionsMs = [
  100,
  200,
  300,
  400,
  500,
  600,
  700,
  800,
  900,
  1000
];
export const absolutePickupForgivenessOptionsMs = [500, 450, 400, 350, 300, 250, 200, 150, 100, 50];
export const tempoToleranceOptionsPercent = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3];
export const rehearsalTextSizeOptions: RehearsalTextSize[] = ["small", "medium", "large", "x-large"];
export const practicePaceMultiplierOptions = [
  0.4,
  0.5,
  0.6,
  0.7,
  0.8,
  0.9,
  1.0,
  1.1,
  1.2,
  1.3
];
export const tempoEndOfLineSilenceOptionsMs = [1000, 1500, 2000, 2500, 3000];
export const playbackRates = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];
export const practiceTimingOptionsMs = [250, 500, 750, 1000, 1250, 1500, 2000];
