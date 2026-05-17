import JSZip from "jszip";
import type { FloorNoiseRecording } from "../domain/floorNoiseRecording";
import type { RecordingTake } from "../domain/take";
import type { RoleRecordingsManifest } from "../specs/recordingPackageManifest";
import type { RecordingProjectRecord } from "../storage/db";

export type RoleRecordingsExport = {
  blob: Blob;
  manifest: RoleRecordingsManifest;
  fileName: string;
};

export class RoleRecordingsExportError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "RoleRecordingsExportError";
  }
}

export type RoleRecordingsZipGenerator = {
  file(path: string, data: Blob | string): void;
  generate(): Promise<Blob>;
};

export async function exportRoleRecordings(
  project: RecordingProjectRecord,
  acceptedTakes: RecordingTake[],
  floorNoiseRecordings: FloorNoiseRecording[] = [],
  zipGenerator: RoleRecordingsZipGenerator = new JsZipRoleRecordingsZipGenerator()
): Promise<RoleRecordingsExport> {
  const acceptedByItemId = new Map(acceptedTakes.map((take) => [take.segmentId, take]));
  const sortedFloorNoiseRecordings = [...floorNoiseRecordings].sort((a, b) =>
    a.recordedAt.localeCompare(b.recordedAt)
  );
  const recordings = [];
  const missingSegmentIds = [];

  for (const floorNoise of sortedFloorNoiseRecordings) {
    zipGenerator.file(floorNoisePath(floorNoise), floorNoise.blob);
  }

  for (const item of project.request.items) {
    const take = acceptedByItemId.get(item.id);
    if (!take) {
      missingSegmentIds.push(item.id);
      continue;
    }

    zipGenerator.file(item.outputPath, take.blob);
    const floorNoise = floorNoiseForTake(sortedFloorNoiseRecordings, take);
    recordings.push({
      id: item.id,
      line_id: item.lineId,
      block_id: item.blockId,
      segment_id: item.segmentId,
      line_content_hash: item.lineContentHash,
      segment_content_hash: item.segmentContentHash,
      audio_path: item.outputPath,
      recorded_at: take.recordedAt,
      floor_noise_id: floorNoise?.id,
      duration_ms: Math.round(take.durationMs),
      sample_rate_hz: take.sampleRateHz,
      channels: take.channels,
      input_quality: take.inputQuality
        ? {
            peak_energy: take.inputQuality.peakEnergy,
            level_counts: {
              no_signal: take.inputQuality.levelCounts.noSignal,
              too_quiet: take.inputQuality.levelCounts.tooQuiet,
              good: take.inputQuality.levelCounts.good,
              clipping: take.inputQuality.levelCounts.clipping
            }
          }
        : undefined,
      status: "accepted" as const
    });
  }

  const manifest: RoleRecordingsManifest = {
    schema_version: 1,
    format_version: "1.0.0",
    package_type: "role_recordings",
    complete: missingSegmentIds.length === 0,
    play: {
      id: project.request.play.id,
      title: project.request.play.title,
      version: project.request.play.version
    },
    role: {
      id: project.request.role.id,
      display_name: project.request.role.displayName
    },
    floor_noise_recordings: sortedFloorNoiseRecordings.map((floorNoise) => ({
      id: floorNoise.id,
      audio_path: floorNoisePath(floorNoise),
      recorded_at: floorNoise.recordedAt,
      duration_ms: Math.round(floorNoise.durationMs),
      sample_rate_hz: floorNoise.sampleRateHz,
      channels: floorNoise.channels,
      device_label: floorNoise.deviceLabel,
      mode: floorNoise.mode
    })),
    recordings,
    missing_segment_ids: missingSegmentIds
  };

  zipGenerator.file("manifest.json", `${JSON.stringify(manifest, null, 2)}\n`);
  let blob: Blob;
  try {
    blob = await zipGenerator.generate();
  } catch (error) {
    throw new RoleRecordingsExportError(
      "Unable to create the recordings package. Browser storage may be full; remove old takes or export fewer recordings.",
      { cause: error }
    );
  }

  return {
    blob,
    manifest,
    fileName: roleRecordingsFileName(project)
  };
}

export function roleRecordingsFileName(project: RecordingProjectRecord): string {
  return safeFileName(
    `${project.request.play.id}-${project.request.role.id}-role-recordings-${compactTimestamp(
      project.request.request.createdAt
    )}.zip`
  );
}

function floorNoisePath(floorNoise: FloorNoiseRecording): string {
  return `noise/${floorNoise.id}.wav`;
}

function floorNoiseForTake(
  floorNoiseRecordings: FloorNoiseRecording[],
  take: RecordingTake
): FloorNoiseRecording | undefined {
  return floorNoiseRecordings
    .filter((floorNoise) => floorNoise.recordedAt <= take.recordedAt)
    .at(-1);
}

function compactTimestamp(value: string): string {
  const compacted = value.replace(/\.\d+Z$/, "Z").replace(/[^A-Za-z0-9]/g, "");
  return compacted || "unknown-time";
}

function safeFileName(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]+/g, "-");
}

class JsZipRoleRecordingsZipGenerator implements RoleRecordingsZipGenerator {
  private readonly zip = new JSZip();

  file(path: string, data: Blob | string): void {
    this.zip.file(path, data);
  }

  generate(): Promise<Blob> {
    return this.zip.generateAsync({ type: "blob", mimeType: "application/zip" });
  }
}
