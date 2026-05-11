export const defaultTargetHesitationMs = 750;
export const internalPauseGraceMs = 750;
export const endOfLineSilenceMs = 1500;
export const speechEnergyThreshold = 0.04;

export type TempoTimingConfig = {
  speechEnergyThreshold: number;
  internalPauseGraceMs: number;
  endOfLineSilenceMs: number;
};

export const defaultTempoTimingConfig: TempoTimingConfig = {
  speechEnergyThreshold,
  internalPauseGraceMs,
  endOfLineSilenceMs
};
