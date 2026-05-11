import { describe, expect, it } from "vitest";
import { deliveryLabel, hesitationLabel, tempoFeedbackFor, timingTargetsForLine } from "../../src/rehearsal/tempoFeedback";
import type { Line } from "../../src/domain/line";

const line: Line = {
  id: "line",
  partId: 0,
  blockId: "0.1",
  role: "MEGAERA",
  speaker: "MEGAERA",
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
      owners: ["MEGAERA"],
      text: "I won't go",
      audioPath: "audio/one.wav",
      durationMs: 1000,
      simultaneous: false
    },
    {
      id: "two",
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
    expect(hesitationLabel(500, 500)).toBe("close");
    expect(hesitationLabel(900, 500)).toBe("late");
  });

  it("labels delivery timing", () => {
    expect(deliveryLabel(1500, 2200)).toBe("fast");
    expect(deliveryLabel(2200, 2200)).toBe("close");
    expect(deliveryLabel(2800, 2200)).toBe("slow");
  });

  it("builds nonjudgmental feedback for measured attempts", () => {
    expect(tempoFeedbackFor(line, { hesitationMs: 600, deliveryMs: 2400 })).toEqual({
      hesitation: { measuredMs: 600, targetMs: 750, label: "close" },
      delivery: { measuredMs: 2400, targetMs: 2200, label: "close" }
    });
  });
});
