import { describe, expect, it } from "vitest";
import { recordingItemSearchText } from "../../src/ui/App";

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

const lineHash = "sha256:0000000000000000000000000000000000000000000000000000000000000001";
const segmentHash = "sha256:0000000000000000000000000000000000000000000000000000000000000002";
