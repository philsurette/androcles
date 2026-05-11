import { beforeEach, describe, expect, it } from "vitest";
import type { RecordingPack } from "../../src/domain/recordingPack";
import { db } from "../../src/storage/db";
import { projectRepository } from "../../src/storage/projectRepository";

describe("ProjectRepository", () => {
  beforeEach(async () => {
    await db.projects.clear();
    await db.takes.clear();
  });

  it("saves imported packs using play and role identity", async () => {
    const project = await projectRepository.saveImportedPack(packFixture());

    expect(project.id).toBe("androcles:CENTURION");
    expect(project.currentSegmentId).toBe("0_12_1");
    await expect(projectRepository.list()).resolves.toHaveLength(1);
  });
});

function packFixture(): RecordingPack {
  return {
    schemaVersion: 1,
    packageType: "role_recording_pack",
    play: {
      id: "androcles",
      title: "Androcles and the Lion"
    },
    role: {
      id: "CENTURION",
      displayName: "Centurion"
    },
    recording: {
      preferredSampleRateHz: 48000,
      preferredChannels: 1,
      sourceFormat: "wav"
    },
    items: [
      {
        lineId: "0_12_CENTURION",
        blockId: "0.12",
        segmentId: "0_12_1",
        sequence: 1,
        displayText: "Halt!",
        segmentText: "Halt!",
        outputPath: "audio/segments/CENTURION/0_12_1.wav",
        stageDirections: []
      }
    ]
  };
}
