import type { Playbook } from "../domain/playbook";
import type { PlaybookManifest } from "../specs/playbookManifest";

export function normalizePlaybook(manifest: PlaybookManifest): Playbook {
  return {
    id: manifest.play.id,
    title: manifest.play.title,
    authors: manifest.play.authors,
    source: manifest.play.source,
    schemaVersion: manifest.schema_version,
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
      contentHash: block.content_hash,
      audioPath: block.audio?.path,
      durationMs: block.audio?.duration_ms,
      targets: block.targets
    })),
    roles: manifest.roles.map((role) => ({
      id: role.id,
      displayName: role.display_name,
      reader: role.reader,
      parts: role.parts,
      lines: role.lines.map((line) => ({
        id: line.id,
        partId: line.part_id,
        blockId: line.block_id,
        role: line.role,
        speaker: line.speaker,
        contentHash: line.content_hash,
        cue: {
          speaker: line.cue.speaker,
          text: line.cue.text,
          audioPath: line.cue.audio.path,
          durationMs: line.cue.audio.duration_ms,
          cueStartOffsets: line.cue.audio.cue_start_offsets?.map((offset) => ({
            requestedWindowMs: offset.requested_window_ms,
            startMs: offset.start_ms,
            confidence: offset.confidence
          }))
        },
        responseText: line.response.text,
        responseSegments: line.response.segments.map((segment) => ({
          id: segment.id,
          segmentId: segment.segment_id,
          contentHash: segment.content_hash,
          owners: segment.owners,
          text: segment.text,
          audioPath: segment.audio.path,
          durationMs: segment.audio.duration_ms,
          simultaneous: segment.simultaneous ?? false
        })),
        directions: line.directions.map((direction) => ({
          id: direction.id,
          segmentId: direction.segment_id,
          contentHash: direction.content_hash,
          text: direction.text,
          placement: direction.placement
        })),
        blocking: (line.blocking ?? []).map((blocking) => ({
          id: blocking.id,
          segmentId: blocking.segment_id,
          contentHash: blocking.content_hash,
          targets: blocking.targets,
          text: blocking.text,
          placement: blocking.placement
        })),
        previousRoles: line.previous_roles,
        timing:
          line.timing?.target_hesitation_ms === undefined
            ? undefined
            : { targetHesitationMs: line.timing.target_hesitation_ms }
      }))
    }))
  };
}
