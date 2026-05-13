import { describe, expect, it } from "vitest";
import type { RecordingItem } from "../../src/domain/recordingItem";
import { recordingItemProgress } from "../../src/domain/recordingItemStatus";

describe("recordingItemProgress", () => {
  it("marks items accepted when their segment has an accepted take", () => {
    expect(recordingItemProgress([itemFixture("I-1:s1", "0_1_1"), itemFixture("I-2:s1", "0_2_1")], new Set(["I-2:s1"]))).toEqual([
      {
        item: itemFixture("I-1:s1", "0_1_1"),
        status: "missing"
      },
      {
        item: itemFixture("I-2:s1", "0_2_1"),
        status: "accepted"
      }
    ]);
  });
});

function itemFixture(id: string, segmentId: string): RecordingItem {
  return {
    id,
    lineId: `${segmentId}_CENTURION`,
    blockId: "0.1",
    segmentId,
    lineContentHash: lineHash,
    segmentContentHash: segmentHash,
    sequence: 1,
    displayText: "Halt!",
    segmentText: "Halt!",
    outputPath: `audio/segments/CENTURION/${segmentId}.wav`,
    stageDirections: [],
    blocking: []
  };
}

const lineHash = "sha256:0000000000000000000000000000000000000000000000000000000000000001";
const segmentHash = "sha256:0000000000000000000000000000000000000000000000000000000000000002";
