import type { Playbook } from "../domain/playbook";
import type { PlaybookManifest } from "../specs/playbookManifest";

export function normalizePlaybook(manifest: PlaybookManifest): Playbook {
  return {
    id: manifest.play.id,
    title: manifest.play.title,
    authors: manifest.play.authors,
    source: manifest.play.source,
    schemaVersion: manifest.schema_version,
    context: manifest.context.map((block) => ({
      id: block.id,
      partId: block.part_id,
      blockId: block.block_id,
      kind: block.kind,
      speaker: block.speaker,
      text: block.text,
      audioPath: block.audio.path,
      durationMs: block.audio.duration_ms
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
        cue: {
          speaker: line.cue.speaker,
          text: line.cue.text,
          audioPath: line.cue.audio.path,
          durationMs: line.cue.audio.duration_ms
        },
        responseText: line.response.text,
        responseSegments: line.response.segments.map((segment) => ({
          id: segment.id,
          owners: segment.owners,
          text: segment.text,
          audioPath: segment.audio.path,
          durationMs: segment.audio.duration_ms,
          simultaneous: segment.simultaneous ?? false
        })),
        previousRoles: line.previous_roles
      }))
    }))
  };
}
