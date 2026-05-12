import JSZip from "jszip";
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
  zipGenerator: RoleRecordingsZipGenerator = new JsZipRoleRecordingsZipGenerator()
): Promise<RoleRecordingsExport> {
  const acceptedBySegmentId = new Map(acceptedTakes.map((take) => [take.segmentId, take]));
  const recordings = [];
  const missingSegmentIds = [];

  for (const item of project.request.items) {
    const take = acceptedBySegmentId.get(item.segmentId);
    if (!take) {
      missingSegmentIds.push(item.id);
      continue;
    }

    zipGenerator.file(item.outputPath, take.blob);
    const recording = {
      id: item.id,
      line_id: item.lineId,
      block_id: item.blockId,
      segment_id: item.segmentId,
      audio_path: item.outputPath,
      recorded_at: take.recordedAt,
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
    };
    if (item.lineContentHash !== undefined) {
      Object.assign(recording, { line_content_hash: item.lineContentHash });
    }
    if (item.segmentContentHash !== undefined) {
      Object.assign(recording, { segment_content_hash: item.segmentContentHash });
    }
    recordings.push(recording);
  }

  const manifest: RoleRecordingsManifest = {
    schema_version: 1,
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
    fileName: `${project.request.role.id}.role-recordings.zip`
  };
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
