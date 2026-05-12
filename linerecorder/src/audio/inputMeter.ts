export type InputLevel = "no-signal" | "too-quiet" | "good" | "clipping";

export function rootMeanSquareEnergy(samples: Uint8Array<ArrayBufferLike>): number {
  let sum = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sum += normalized * normalized;
  }
  return Math.sqrt(sum / samples.length);
}

export function rootMeanSquareFloatEnergy(samples: Float32Array): number {
  let sum = 0;
  for (const sample of samples) {
    sum += sample * sample;
  }
  return Math.sqrt(sum / samples.length);
}

export function classifyInputLevel(energy: number): InputLevel {
  if (energy < 0.005) {
    return "no-signal";
  }
  if (energy < 0.025) {
    return "too-quiet";
  }
  if (energy > 0.92) {
    return "clipping";
  }
  return "good";
}

export function meterFillPercent(energy: number): number {
  const noiseFloorEnergy = 0.005;
  const speechReferenceEnergy = 0.16;
  const normalized = Math.max(0, (energy - noiseFloorEnergy) / (speechReferenceEnergy - noiseFloorEnergy));
  return Math.max(0, Math.min(100, Math.sqrt(normalized) * 100));
}

export function meterFillPercentForLevel(energy: number, level: InputLevel): number {
  const fill = meterFillPercent(energy);
  switch (level) {
    case "no-signal":
      return fill;
    case "too-quiet":
      return Math.max(18, fill);
    case "good":
      return Math.max(46, fill);
    case "clipping":
      return 100;
  }
}

export function smoothMeterEnergy(previousEnergy: number, nextEnergy: number): number {
  const attack = 0.65;
  const release = 0.18;
  const factor = nextEnergy > previousEnergy ? attack : release;
  return previousEnergy + (nextEnergy - previousEnergy) * factor;
}
