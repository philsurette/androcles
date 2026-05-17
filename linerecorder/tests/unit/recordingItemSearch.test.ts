import { describe, expect, it } from "vitest";
import {
  isUsableFloorNoise,
  levelLabel,
  levelStatus,
  reasonLabel,
  recordingItemSearchText,
  requestKindLabel,
  sameContext
} from "../../src/ui/recordingItemPresentation";

describe("recordingItemSearchText", () => {
  it("includes ids, cue text, line text, and blocking", () => {
    const text = recordingItemSearchText({
      id: "2-3:s1",
      lineId: "2-3",
      blockId: "2.3",
      segmentId: "2_3_1",
      lineContentHash: lineHash,
      segmentContentHash: segmentHash,
      sequence: 1,
      displayText: "Please do.",
      segmentText: "Please do.",
      outputPath: "recordings/LILLIAN/2_3_1.wav",
      cueSpeaker: "CHRISTINE",
      cueText: "Do you mind if I record?",
      previousSpeaker: "NARRATOR",
      previousText: "Lillian settles beside the recorder.",
      nextSpeaker: "LILLIAN",
      nextText: "I'm Lillian Barnes.",
      sectionTitle: "Prologue",
      sceneHeading: "Scene Five",
      stageDirections: ["softly"],
      blocking: [
        {
          id: "2-3:b1",
          targets: ["LILLIAN"],
          text: "settles beside the recorder",
          placement: "before"
        }
      ]
    });

    expect(text).toContain("2-3:s1");
    expect(text).toContain("Do you mind if I record?");
    expect(text).toContain("Please do.");
    expect(text).toContain("settles beside the recorder");
  });
});

describe("recording item presentation helpers", () => {
  it("formats labels used by the recording UI", () => {
    expect(requestKindLabel("selected_segments")).toBe("Selected Segments");
    expect(reasonLabel(undefined)).toBe("recording");
    expect(reasonLabel("pickup_fix")).toBe("pickup fix");
    expect(levelLabel("too-quiet")).toBe("Too quiet");
    expect(levelStatus("clipping")).toBe("Input is clipping. Move back or reduce gain.");
  });

  it("compares context only when speaker and trimmed text match", () => {
    expect(sameContext("A", "same text ", "A", "same text")).toBe(true);
    expect(sameContext("A", "same text", "B", "same text")).toBe(false);
    expect(sameContext("A", undefined, "A", "same text")).toBe(false);
  });

  it("accepts floor noise only when it is not clipped or speech-heavy", () => {
    expect(isUsableFloorNoise(recordedWithLevelCounts({ "no-signal": 5, "too-quiet": 5, good: 1, clipping: 0 }))).toBe(true);
    expect(isUsableFloorNoise(recordedWithLevelCounts({ "no-signal": 1, "too-quiet": 1, good: 8, clipping: 0 }))).toBe(false);
    expect(isUsableFloorNoise(recordedWithLevelCounts({ "no-signal": 5, "too-quiet": 5, good: 0, clipping: 1 }))).toBe(false);
  });
});

const lineHash = "sha256:0000000000000000000000000000000000000000000000000000000000000001";
const segmentHash = "sha256:0000000000000000000000000000000000000000000000000000000000000002";

function recordedWithLevelCounts(levelCounts: Record<"no-signal" | "too-quiet" | "good" | "clipping", number>) {
  return {
    blob: new Blob(),
    durationMs: 1000,
    sampleRateHz: 44100,
    channels: 1,
    inputQuality: {
      peakEnergy: 0.1,
      levelCounts
    }
  };
}
