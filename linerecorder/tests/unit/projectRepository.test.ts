import { beforeEach, describe, expect, it } from "vitest";
import type { RecordingRequest } from "../../src/domain/recordingRequest";
import { db } from "../../src/storage/db";
import { projectRepository } from "../../src/storage/projectRepository";

describe("ProjectRepository", () => {
  beforeEach(async () => {
    await db.projects.clear();
    await db.takes.clear();
  });

  it("saves imported requests using play and role identity", async () => {
    const project = await projectRepository.saveImportedRequest(packFixture());

    expect(project.id).toBe("androcles:CENTURION");
    expect(project.currentSegmentId).toBe("0_12_1");
    expect(project.request.packageType).toBe("recording_request");
    await expect(projectRepository.list()).resolves.toHaveLength(1);
  });
});

function packFixture(): RecordingRequest {
  return {
    schemaVersion: 1,
    packageType: "recording_request",
    request: {
      id: "androcles-CENTURION-full-2026-05-10",
      kind: "full_role",
      createdAt: "2026-05-10T14:00:00Z",
      createdBy: "stager"
    },
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
