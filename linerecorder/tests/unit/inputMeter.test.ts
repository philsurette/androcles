import { describe, expect, it } from "vitest";
import { classifyInputLevel, meterFillPercent, rootMeanSquareEnergy } from "../../src/audio/inputMeter";

describe("inputMeter", () => {
  it("calculates root mean square energy from byte samples", () => {
    expect(rootMeanSquareEnergy(new Uint8Array([128, 128, 128]))).toBe(0);
    expect(rootMeanSquareEnergy(new Uint8Array([255]))).toBeCloseTo(0.992, 3);
  });

  it("classifies signal levels", () => {
    expect(classifyInputLevel(0)).toBe("no-signal");
    expect(classifyInputLevel(0.02)).toBe("too-quiet");
    expect(classifyInputLevel(0.1)).toBe("good");
    expect(classifyInputLevel(0.95)).toBe("clipping");
  });

  it("keeps quiet room noise visually low", () => {
    expect(meterFillPercent(0)).toBe(0);
    expect(meterFillPercent(0.02)).toBeCloseTo(12.5);
    expect(meterFillPercent(0.08)).toBeCloseTo(50);
    expect(meterFillPercent(0.2)).toBe(100);
  });
});
