import { describe, expect, it } from "vitest";
import { validateRoleRecordingsManifest } from "../../src/specs/validateRoleRecordingsManifest";

describe("validateRoleRecordingsManifest", () => {
  it("accepts a valid role recordings manifest", () => {
    const manifest = validateRoleRecordingsManifest({
      schema_version: 1,
      package_type: "role_recordings",
      complete: false,
      play: {
        id: "androcles",
        title: "Androcles and the Lion",
        version: "2026-05-10"
      },
      role: {
        id: "CENTURION",
        display_name: "Centurion"
      },
      floor_noise_recordings: [
        {
          id: "floor-20260511T115900Z",
          audio_path: "noise/floor-20260511T115900Z.wav",
          recorded_at: "2026-05-11T11:59:00Z",
          duration_ms: 5000,
          sample_rate_hz: 48000,
          channels: 1,
          device_label: "USB Microphone",
          mode: "clean"
        }
      ],
      recordings: [
        {
          id: "I-12:s1",
          line_id: "I-12",
          block_id: "0.12",
          segment_id: "0_12_1",
          line_content_hash: line12Hash,
          segment_content_hash: segment12Hash,
          audio_path: "audio/segments/CENTURION/0_12_1.wav",
          recorded_at: "2026-05-11T12:00:00Z",
          floor_noise_id: "floor-20260511T115900Z",
          duration_ms: 1840,
          sample_rate_hz: 48000,
          channels: 1,
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

    expect(manifest.package_type).toBe("role_recordings");
    expect(manifest.recordings[0].id).toBe("I-12:s1");
    expect(manifest.recordings[0].segment_id).toBe("0_12_1");
    expect(manifest.recordings[0].floor_noise_id).toBe("floor-20260511T115900Z");
    expect(manifest.floor_noise_recordings?.[0].audio_path).toBe("noise/floor-20260511T115900Z.wav");
    expect(manifest.recordings[0].input_quality?.level_counts.good).toBe(24);
    expect(manifest.missing_segment_ids).toEqual(["I-14:s1"]);
  });

  it("rejects unsupported package types", () => {
    expect(() =>
      validateRoleRecordingsManifest({
        schema_version: 1,
        package_type: "recording_request",
        complete: true,
        play: { id: "androcles", title: "Androcles and the Lion" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recordings: [],
        missing_segment_ids: []
      })
    ).toThrow();
  });

  it("rejects parser-shaped ids", () => {
    expect(() =>
      validateRoleRecordingsManifest({
        schema_version: 1,
        package_type: "role_recordings",
        complete: true,
        play: { id: "androcles", title: "Androcles and the Lion" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recordings: [
          {
            id: "0_12_1",
            line_id: "0_12_CENTURION",
            block_id: "0.12",
            segment_id: "0_12_1",
            line_content_hash: line12Hash,
            segment_content_hash: segment12Hash,
            audio_path: "audio/segments/CENTURION/0_12_1.wav",
            recorded_at: "2026-05-11T12:00:00Z",
            duration_ms: 1840,
            sample_rate_hz: 48000,
            channels: 1,
            status: "accepted"
          }
        ],
        missing_segment_ids: []
      })
    ).toThrow("Expected a production id");
  });
});

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
