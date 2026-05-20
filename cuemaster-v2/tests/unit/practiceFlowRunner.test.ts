import { describe, expect, it } from "vitest";
import { buildPracticeFlowSteps, silentResponseDurationMs } from "../../src/practice/practiceFlowRunner";

describe("buildPracticeFlowSteps", () => {
  it("builds manual cue-only steps", () => {
    expect(
      buildPracticeFlowSteps({
        flow: "manual",
        lineId: "P-3",
        responseDurationMs: 3000,
        linePace: 1,
        responsePaddingMs: 750
      })
    ).toEqual([{ kind: "cue", lineId: "P-3" }]);
  });

  it("builds listen flow steps", () => {
    expect(
      buildPracticeFlowSteps({
        flow: "listen",
        lineId: "P-3",
        responseDurationMs: 3000,
        linePace: 1,
        responsePaddingMs: 750
      }).map((step) => step.kind)
    ).toEqual(["cue", "reference", "advance"]);
  });

  it("builds try then check flow steps", () => {
    expect(
      buildPracticeFlowSteps({
        flow: "try_then_check",
        lineId: "P-3",
        responseDurationMs: 3000,
        linePace: 1,
        responsePaddingMs: 750
      }).map((step) => step.kind)
    ).toEqual(["cue", "silent-response", "reference", "advance"]);
  });
});

describe("silentResponseDurationMs", () => {
  it("uses line pace to derive the response window", () => {
    expect(silentResponseDurationMs(3000, 0.75, 750)).toBe(4750);
  });

  it("rejects invalid line pace", () => {
    expect(() => silentResponseDurationMs(3000, 0, 750)).toThrow("Line pace must be greater than zero.");
  });
});
