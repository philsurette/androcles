import { describe, expect, it } from "vitest";
import { clampPlaybackRate } from "../../src/ui/screens/RehearsalScreen";

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
