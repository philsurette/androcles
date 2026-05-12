import { beforeEach, describe, expect, it } from "vitest";
import type { RecordingRequest } from "../../src/domain/recordingRequest";
import { db } from "../../src/storage/db";
import { projectRepository } from "../../src/storage/projectRepository";
import { takeRepository } from "../../src/storage/takeRepository";

describe("ProjectRepository", () => {
  beforeEach(async () => {
    await db.projects.clear();
    await db.takes.clear();
    await db.floorNoiseRecordings.clear();
  });

  it("saves imported requests using request identity", async () => {
    const project = await projectRepository.saveImportedRequest(packFixture());

    expect(project.id).toBe("androcles-CENTURION-full-2026-05-10");
    expect(project.currentItemId).toBe("I-12:s1");
    expect(project.request.packageType).toBe("recording_request");
    await expect(projectRepository.list()).resolves.toHaveLength(1);
  });

  it("updates the current item", async () => {
    const project = await projectRepository.saveImportedRequest(packFixture());

    await projectRepository.setCurrentItem(project.id, "I-14:s1");

    await expect(projectRepository.get(project.id)).resolves.toMatchObject({
      currentItemId: "I-14:s1"
    });
  });

  it("deletes the project and its takes", async () => {
    const project = await projectRepository.saveImportedRequest(packFixture());
    await takeRepository.saveAccepted({
      id: "take-1",
      projectId: project.id,
      segmentId: "I-12:s1",
      status: "accepted",
      recordedAt: "2026-05-11T12:00:00Z",
      durationMs: 1000,
      sampleRateHz: 48000,
      channels: 1,
      blob: new Blob(["fake wav"], { type: "audio/wav" })
    });
    await db.floorNoiseRecordings.put({
      id: "floor-1",
      projectId: project.id,
      recordedAt: "2026-05-11T11:59:00Z",
      durationMs: 5000,
      sampleRateHz: 48000,
      channels: 1,
      deviceId: "default",
      deviceLabel: "Default microphone",
      mode: "clean",
      blob: new Blob(["floor wav"], { type: "audio/wav" })
    });

    await projectRepository.delete(project.id);

    await expect(projectRepository.list()).resolves.toEqual([]);
    await expect(takeRepository.acceptedForProject(project.id)).resolves.toEqual([]);
    await expect(db.floorNoiseRecordings.where("projectId").equals(project.id).toArray()).resolves.toEqual([]);
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
        id: "I-12:s1",
        lineId: "I-12",
        blockId: "0.12",
        segmentId: "0_12_1",
        lineContentHash: line12Hash,
        segmentContentHash: segment12Hash,
        sequence: 1,
        displayText: "Halt!",
        segmentText: "Halt!",
        outputPath: "audio/segments/CENTURION/0_12_1.wav",
        stageDirections: []
      }
    ]
  };
}

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
