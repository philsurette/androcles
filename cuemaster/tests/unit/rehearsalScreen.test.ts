import { describe, expect, it } from "vitest";
import { clampCueDepth, clampPlaybackRate } from "../../src/ui/screens/RehearsalScreen";

describe("clampPlaybackRate", () => {
  it("clamps response playback speed to the supported range", () => {
    expect(clampPlaybackRate(0.1)).toBe(0.4);
    expect(clampPlaybackRate(1.8)).toBe(1.3);
  });

  it("rounds response playback speed to one decimal place", () => {
    expect(clampPlaybackRate(0.94)).toBe(0.9);
    expect(clampPlaybackRate(0.95)).toBe(1);
  });
});

describe("clampCueDepth", () => {
  it("clamps cue depth to the supported range", () => {
    expect(clampCueDepth(0)).toBe(1);
    expect(clampCueDepth(9)).toBe(3);
  });

  it("rounds cue depth to a whole number", () => {
    expect(clampCueDepth(1.4)).toBe(1);
    expect(clampCueDepth(1.5)).toBe(2);
  });
});
