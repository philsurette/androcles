import { describe, expect, it } from "vitest";
import { classifyInputLevel, meterFillPercent, meterFillPercentForLevel, rootMeanSquareEnergy, rootMeanSquareFloatEnergy, smoothMeterEnergy } from "../../src/audio/inputMeter";

describe("inputMeter", () => {
  it("calculates root mean square energy from byte samples", () => {
    expect(rootMeanSquareEnergy(new Uint8Array([128, 128, 128]))).toBe(0);
    expect(rootMeanSquareEnergy(new Uint8Array([255]))).toBeCloseTo(0.992, 3);
  });

  it("calculates root mean square energy from float samples", () => {
    expect(rootMeanSquareFloatEnergy(new Float32Array([0, 0, 0]))).toBe(0);
    expect(rootMeanSquareFloatEnergy(new Float32Array([1, -1]))).toBe(1);
  });

  it("classifies signal levels", () => {
    expect(classifyInputLevel(0)).toBe("no-signal");
    expect(classifyInputLevel(0.02)).toBe("too-quiet");
    expect(classifyInputLevel(0.1)).toBe("good");
    expect(classifyInputLevel(0.95)).toBe("clipping");
  });

  it("keeps quiet room noise visually low", () => {
    expect(meterFillPercent(0)).toBe(0);
    expect(meterFillPercent(0.005)).toBe(0);
    expect(meterFillPercent(0.02)).toBeCloseTo(31.1, 1);
    expect(meterFillPercent(0.08)).toBeCloseTo(69.6, 1);
    expect(meterFillPercent(0.2)).toBe(100);
  });

  it("smooths visual meter energy with faster attack than release", () => {
    expect(smoothMeterEnergy(0, 1)).toBeCloseTo(0.65);
    expect(smoothMeterEnergy(1, 0)).toBeCloseTo(0.82);
  });

  it("keeps the meter visually aligned with classified levels", () => {
    expect(meterFillPercentForLevel(0, "no-signal")).toBe(0);
    expect(meterFillPercentForLevel(0.006, "too-quiet")).toBe(18);
    expect(meterFillPercentForLevel(0.006, "good")).toBe(46);
    expect(meterFillPercentForLevel(0.5, "clipping")).toBe(100);
  });
});
