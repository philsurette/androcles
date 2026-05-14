import { describe, expect, it } from "vitest";
import { deliveryLabel, hesitationLabel, tempoFeedbackFor, timingTargetsForLine } from "../../src/rehearsal/tempoFeedback";
import type { Line } from "../../src/domain/line";

const line: Line = {
  id: "line",
  partId: 0,
  blockId: "0.1",
  role: "MEGAERA",
  speaker: "MEGAERA",
  contentHash: "sha256:0000000000000000000000000000000000000000000000000000000000000001",
  cue: {
    speaker: "_NARRATOR",
    text: "A forest.",
    audioPath: "audio/cue.wav",
    durationMs: 1000
  },
  responseText: "I won't go another step.",
  responseSegments: [
    {
      id: "one",
      segmentId: "0_1_1",
      contentHash: "sha256:0000000000000000000000000000000000000000000000000000000000000002",
      owners: ["MEGAERA"],
      text: "I won't go",
      audioPath: "audio/one.wav",
      durationMs: 1000,
      simultaneous: false
    },
    {
      id: "two",
      segmentId: "0_1_2",
      contentHash: "sha256:0000000000000000000000000000000000000000000000000000000000000003",
      owners: ["MEGAERA"],
      text: "another step.",
      audioPath: "audio/two.wav",
      durationMs: 1200,
      simultaneous: false
    }
  ],
  directions: [],
  previousRoles: ["_NARRATOR"]
};

describe("tempoFeedback", () => {
  it("uses line-specific target hesitation and sums response segment durations", () => {
    const targets = timingTargetsForLine({
      ...line,
      timing: { targetHesitationMs: 750 }
    });

    expect(targets).toEqual({ targetHesitationMs: 750, targetDeliveryMs: 2200 });
  });

  it("falls back to default target hesitation", () => {
    expect(timingTargetsForLine(line).targetHesitationMs).toBe(750);
  });

  it("labels pickup timing", () => {
    expect(hesitationLabel(200, 500)).toBe("sharp");
    expect(hesitationLabel(300, 500)).toBe("close");
    expect(hesitationLabel(500, 500)).toBe("close");
    expect(hesitationLabel(751, 500)).toBe("late");
    expect(hesitationLabel(750, 500)).toBe("close");
  });

  it("labels delivery timing", () => {
    expect(deliveryLabel(1700, 2200)).toBe("fast");
    expect(deliveryLabel(2200, 2200)).toBe("close");
    expect(deliveryLabel(3000, 2200)).toBe("slow");
  });

  it("applies practice pace multiplier to delivery label", () => {
    expect(deliveryLabel(1900, 2200, 1)).toBe("close");
    expect(deliveryLabel(1900, 2200, 0.5)).toBe("fast");
    expect(deliveryLabel(1900, 2200, 1.3)).toBe("close");
  });

  it("requires both percentage and 500ms thresholds for delivery extremes", () => {
    expect(deliveryLabel(1750, 2200)).toBe("close");
    expect(deliveryLabel(3000, 2800)).toBe("close");
  });

  it("builds nonjudgmental feedback for measured attempts", () => {
    expect(tempoFeedbackFor(line, { hesitationMs: 600, deliveryMs: 2400 })).toEqual({
      hesitation: { measuredMs: 600, targetMs: 750, label: "close" },
      delivery: { measuredMs: 2400, targetMs: 2200, label: "close" }
    });
  });

  it("uses explicit tempo pickup target when supplied", () => {
    expect(tempoFeedbackFor(line, { hesitationMs: 600, deliveryMs: 2400 }, 500)).toEqual({
      hesitation: { measuredMs: 600, targetMs: 500, label: "close" },
      delivery: { measuredMs: 2400, targetMs: 2200, label: "close" }
    });
  });

  it("uses practice pace multiplier when supplied", () => {
    expect(tempoFeedbackFor(line, { hesitationMs: 600, deliveryMs: 1900 }, 750, 0.5)).toEqual({
      hesitation: { measuredMs: 600, targetMs: 750, label: "close" },
      delivery: { measuredMs: 1900, targetMs: 2200, label: "fast" }
    });
  });
});
