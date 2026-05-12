import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type { RecordingTake } from "../../src/domain/take";
import { exportRoleRecordings, RoleRecordingsExportError, type RoleRecordingsZipGenerator } from "../../src/package/exportRoleRecordings";
import type { RecordingProjectRecord } from "../../src/storage/db";

describe("exportRoleRecordings", () => {
  it("exports accepted recordings at their declared output paths", async () => {
    const result = await exportRoleRecordings(projectFixture(), [takeFixture("I-12:s1")]);
    const zip = await JSZip.loadAsync(result.blob);
    const manifest = JSON.parse(await zip.file("manifest.json")!.async("string"));

    expect(result.fileName).toBe("CENTURION.role-recordings.zip");
    expect(manifest).toMatchObject({
      package_type: "role_recordings",
      complete: false,
      recordings: [
        {
          id: "I-12:s1",
          line_id: "I-12",
          block_id: "0.12",
          segment_id: "0_12_1",
          line_content_hash: line12Hash,
          segment_content_hash: segment12Hash,
          audio_path: "audio/segments/CENTURION/0_12_1.wav",
          input_quality: {
            peak_energy: 0.14,
            level_counts: {
              no_signal: 1,
              too_quiet: 2,
              good: 24,
              clipping: 0
            }
          },
          status: "accepted"
        }
      ],
      missing_segment_ids: ["I-14:s1"]
    });
    await expect(zip.file("audio/segments/CENTURION/0_12_1.wav")!.async("string")).resolves.toBe("fake wav");
  });

  it("marks the export complete when every requested segment has an accepted take", async () => {
    const result = await exportRoleRecordings(projectFixture(), [takeFixture("I-12:s1"), takeFixture("I-14:s1")]);

    expect(result.manifest.complete).toBe(true);
    expect(result.manifest.missing_segment_ids).toEqual([]);
  });

  it("reports package generation failures with an export-specific error", async () => {
    await expect(exportRoleRecordings(projectFixture(), [takeFixture("I-12:s1")], failingZipGenerator())).rejects.toThrow(
      RoleRecordingsExportError
    );
  });
});

function failingZipGenerator(): RoleRecordingsZipGenerator {
  return {
    file: () => undefined,
    generate: () => Promise.reject(new DOMException("Quota exceeded", "QuotaExceededError"))
  };
}

function projectFixture(): RecordingProjectRecord {
  return {
    id: "androcles:CENTURION",
    importedAt: "2026-05-11T12:00:00Z",
    request: {
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
        },
        {
          id: "I-14:s1",
          lineId: "I-14",
          blockId: "0.14",
          segmentId: "0_14_1",
          lineContentHash: line14Hash,
          segmentContentHash: segment14Hash,
          sequence: 2,
          displayText: "Stand aside.",
          segmentText: "Stand aside.",
          outputPath: "audio/segments/CENTURION/0_14_1.wav",
          stageDirections: []
        }
      ]
    }
  };
}

function takeFixture(segmentId: string): RecordingTake {
  return {
    id: `take-${segmentId}`,
    projectId: "androcles:CENTURION",
    segmentId,
    status: "accepted",
    recordedAt: "2026-05-11T12:00:00Z",
    durationMs: 1000.4,
    sampleRateHz: 48000,
    channels: 1,
    inputQuality: {
      peakEnergy: 0.14,
      levelCounts: {
        noSignal: 1,
        tooQuiet: 2,
        good: 24,
        clipping: 0
      }
    },
    blob: new Blob(["fake wav"], { type: "audio/wav" })
  };
}

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
const line14Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000014";
const segment14Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001014";
