import { describe, expect, it } from "vitest";
import { rootMeanSquareEnergy } from "../../src/rehearsal/voiceActivityDetector";
import { VoiceActivityTracker } from "../../src/rehearsal/voiceActivityTracker";

describe("VoiceActivityTracker", () => {
  it("detects first speech and reports hesitation", () => {
    const tracker = new VoiceActivityTracker({
      speechEnergyThreshold: 0.1,
      internalPauseGraceMs: 750,
      endOfLineSilenceMs: 1500
    });

    tracker.start(1000);

    expect(tracker.observe(0.01, 1200)).toBeNull();
    expect(tracker.observe(0.2, 1450)).toEqual({
      event: "speech-started",
      atMs: 1450,
      hesitationMs: 450
    });
  });

  it("ignores short internal pauses and ends delivery after long silence", () => {
    const tracker = new VoiceActivityTracker({
      speechEnergyThreshold: 0.1,
      internalPauseGraceMs: 750,
      endOfLineSilenceMs: 1500
    });

    tracker.start(0);
    tracker.observe(0.2, 100);
    tracker.observe(0.2, 900);

    expect(tracker.observe(0.01, 1600)).toBeNull();
    expect(tracker.observe(0.01, 2400)).toEqual({
      event: "delivery-ended",
      atMs: 2400,
      hesitationMs: 100,
      deliveryMs: 800
    });
  });
});

describe("rootMeanSquareEnergy", () => {
  it("returns zero for silence centered at 128", () => {
    expect(rootMeanSquareEnergy(new Uint8Array([128, 128, 128]))).toBe(0);
  });

  it("returns positive energy for non-silent samples", () => {
    expect(rootMeanSquareEnergy(new Uint8Array([0, 128, 255]))).toBeGreaterThan(0);
  });
});
