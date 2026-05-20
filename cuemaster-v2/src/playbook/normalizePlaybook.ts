import type { Playbook, PlaybookBlockingNote } from "../domain/playbook";
import type { ManifestBlockingNote, PlaybookManifest } from "../specs/playbookManifest";

export class PlaybookNormalizer {
  normalize(manifest: PlaybookManifest): Playbook {
    if (manifest.package_type !== "playbook") {
      throw new Error(`Expected playbook package. Received ${manifest.package_type}.`);
    }

    const standaloneBlocking = this.standaloneBlockingByLine(manifest);

    return {
      id: manifest.play.id,
      title: manifest.play.title,
      authors: manifest.play.authors,
      formatVersion: manifest.format_version,
      buildTimestamp: manifest.build.buildTimestamp,
      productionSource: manifest.production.source,
      staging:
        manifest.staging === undefined
          ? undefined
          : {
              format: manifest.staging.format,
              formatVersion: manifest.staging.format_version,
              manifestPath: manifest.staging.manifest_path
            },
      sections: manifest.sections.map((section) => ({
        id: section.id,
        partId: section.part_id,
        blockId: section.block_id,
        title: section.title,
        ordinal: section.ordinal
      })),
      context: manifest.context.map((block) => ({
        id: block.id,
        partId: block.part_id,
        blockId: block.block_id,
        kind: block.kind,
        speaker: block.speaker,
        text: block.text,
        audioPath: block.audio?.path,
        durationMs: block.audio?.duration_ms,
        targets: block.targets,
        placement: block.placement
      })),
      roles: manifest.roles
        .filter((role) => role.meta !== true)
        .map((role) => ({
          id: role.id,
          displayName: role.display_name ?? role.name ?? role.id,
          lineCount: role.lines.length,
          lines: role.lines.map((line) => ({
            id: line.id,
            partId: line.part_id,
            blockId: line.block_id,
            role: line.role,
            speaker: line.speaker,
            cue: {
              speaker: line.cue.speaker,
              text: line.cue.text,
              audioPath: line.cue.audio.path,
              durationMs: line.cue.audio.duration_ms
            },
            responseText: line.response.text,
            responseSegments: line.response.segments.map((segment) => ({
              id: segment.id,
              segmentId: segment.segment_id,
              owners: segment.owners,
              text: segment.text,
              audioPath: segment.audio.path,
              durationMs: segment.audio.duration_ms,
              simultaneous: segment.simultaneous ?? false
            })),
            directions: line.directions.map((direction) => ({
              id: direction.id,
              segmentId: direction.segment_id,
              text: direction.text,
              placement: direction.placement
            })),
            blocking: [
              ...(standaloneBlocking.get(line.id) ?? []),
              ...(line.blocking ?? []).map((blocking) => this.normalizeLineBlocking(blocking))
            ],
            previousRoles: line.previous_roles
          }))
        }))
    };
  }

  private standaloneBlockingByLine(manifest: PlaybookManifest): Map<string, PlaybookBlockingNote[]> {
    const byLine = new Map<string, PlaybookBlockingNote[]>();
    for (const block of manifest.context) {
      if (block.kind !== "blocking") {
        continue;
      }
      const lineId = this.lineIdForBlockingId(block.id);
      byLine.set(lineId, [
        ...(byLine.get(lineId) ?? []),
        {
          id: block.id,
          targets: block.targets ?? [],
          text: block.text,
          placement: block.placement ?? "before"
        }
      ]);
    }
    return byLine;
  }

  private normalizeLineBlocking(blocking: ManifestBlockingNote): PlaybookBlockingNote {
    return {
      id: blocking.id,
      segmentId: blocking.segment_id,
      targets: blocking.targets,
      text: blocking.text,
      placement: blocking.placement
    };
  }

  private lineIdForBlockingId(id: string): string {
    return id.split(":", 1)[0];
  }
}
