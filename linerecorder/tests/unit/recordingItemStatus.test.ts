import { describe, expect, it } from "vitest";
import type { RecordingItem } from "../../src/domain/recordingItem";
import { recordingItemProgress } from "../../src/domain/recordingItemStatus";

describe("recordingItemProgress", () => {
  it("marks items accepted when their segment has an accepted take", () => {
    expect(recordingItemProgress([itemFixture("0_1_1"), itemFixture("0_2_1")], new Set(["0_2_1"]))).toEqual([
      {
        item: itemFixture("0_1_1"),
        status: "missing"
      },
      {
        item: itemFixture("0_2_1"),
        status: "accepted"
      }
    ]);
  });
});

function itemFixture(segmentId: string): RecordingItem {
  return {
    id: segmentId,
    lineId: `${segmentId}_CENTURION`,
    blockId: "0.1",
    segmentId,
    sequence: 1,
    displayText: "Halt!",
    segmentText: "Halt!",
    outputPath: `audio/segments/CENTURION/${segmentId}.wav`,
    stageDirections: []
  };
}
