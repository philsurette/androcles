import JSZip from "jszip";
import type { RecordingTake } from "../domain/take";
import type { RoleRecordingsManifest } from "../specs/recordingPackageManifest";
import type { RecordingProjectRecord } from "../storage/db";

export type RoleRecordingsExport = {
  blob: Blob;
  manifest: RoleRecordingsManifest;
  fileName: string;
};

export async function exportRoleRecordings(
  project: RecordingProjectRecord,
  acceptedTakes: RecordingTake[]
): Promise<RoleRecordingsExport> {
  const zip = new JSZip();
  const acceptedBySegmentId = new Map(acceptedTakes.map((take) => [take.segmentId, take]));
  const recordings = [];
  const missingSegmentIds = [];

  for (const item of project.request.items) {
    const take = acceptedBySegmentId.get(item.segmentId);
    if (!take) {
      missingSegmentIds.push(item.segmentId);
      continue;
    }

    zip.file(item.outputPath, take.blob);
    recordings.push({
      line_id: item.lineId,
      block_id: item.blockId,
      segment_id: item.segmentId,
      audio_path: item.outputPath,
      recorded_at: take.recordedAt,
      duration_ms: Math.round(take.durationMs),
      sample_rate_hz: take.sampleRateHz,
      channels: take.channels,
      status: "accepted" as const
    });
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

  zip.file("manifest.json", `${JSON.stringify(manifest, null, 2)}\n`);
  const blob = await zip.generateAsync({ type: "blob", mimeType: "application/zip" });

  return {
    blob,
    manifest,
    fileName: `${project.request.role.id}.role-recordings.zip`
  };
}
