import { describe, expect, it } from "vitest";
import type { RecordingItemProgress } from "../../src/domain/recordingItemStatus";
import { nextProgress, previousProgress, selectedProgressIndex } from "../../src/domain/recordingNavigation";

describe("recording navigation", () => {
  it("selects the first item by default", () => {
    expect(selectedProgressIndex(progressFixture(), undefined)).toBe(0);
  });

  it("falls back to the first item when the stored segment no longer exists", () => {
    expect(selectedProgressIndex(progressFixture(), "missing")).toBe(0);
  });

  it("finds previous and next items from the selected index", () => {
    const progress = progressFixture();

    expect(previousProgress(progress, 1)?.item.segmentId).toBe("0_1_1");
    expect(nextProgress(progress, 1)?.item.segmentId).toBe("0_3_1");
  });

  it("does not navigate beyond list edges", () => {
    const progress = progressFixture();

    expect(previousProgress(progress, 0)).toBeUndefined();
    expect(nextProgress(progress, 2)).toBeUndefined();
  });
});

function progressFixture(): RecordingItemProgress[] {
  return ["0_1_1", "0_2_1", "0_3_1"].map((segmentId, index) => ({
    item: {
      lineId: `${segmentId}_CENTURION`,
      blockId: `0.${index + 1}`,
      segmentId,
      sequence: index + 1,
      displayText: `Line ${index + 1}`,
      segmentText: `Line ${index + 1}`,
      outputPath: `audio/segments/CENTURION/${segmentId}.wav`,
      stageDirections: []
    },
    status: "missing"
  }));
}
