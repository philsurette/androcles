export type InputLevel = "no-signal" | "too-quiet" | "good" | "clipping";

export function rootMeanSquareEnergy(samples: Uint8Array<ArrayBufferLike>): number {
  let sum = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sum += normalized * normalized;
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
