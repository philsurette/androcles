export const defaultTargetHesitationMs = 750;
export const internalPauseGraceMs = 750;
export const endOfLineSilenceMs = 2000;
export const speechEnergyThreshold = 0.025;

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
