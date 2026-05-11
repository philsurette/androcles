import { z } from "zod";
import type { RecordingRequest } from "../domain/recordingRequest";
import type { RecordingRequestManifest } from "./recordingPackageManifest";

const itemSchema = z.object({
  line_id: z.string().min(1),
  block_id: z.string().min(1),
  segment_id: z.string().min(1),
  sequence: z.number().int().positive(),
  display_text: z.string(),
  segment_text: z.string(),
  output_path: z.string().min(1),
  cue_text: z.string().optional(),
  cue_speaker: z.string().optional(),
  previous_text: z.string().optional(),
  previous_speaker: z.string().optional(),
  next_text: z.string().optional(),
  next_speaker: z.string().optional(),
  section_id: z.string().optional(),
  section_title: z.string().optional(),
  scene_heading: z.string().optional(),
  stage_directions: z.array(z.string()).optional(),
  reason: z.string().optional(),
  notes: z.string().optional(),
  previous_recording: z.string().optional(),
  cue_audio: z.string().optional(),
  changed: z.boolean().optional(),
  target_duration_ms: z.number().int().nonnegative().optional(),
  target_hesitation_ms: z.number().int().nonnegative().optional(),
  simultaneous: z.boolean().optional()
});

const manifestSchema = z.object({
  schema_version: z.literal(1),
  package_type: z.literal("recording_request"),
  request: z.object({
    id: z.string().min(1),
    kind: z.enum(["full_role", "selected_segments", "rerecord"]),
    created_at: z.string().min(1),
    created_by: z.string().min(1),
    notes: z.string().optional()
  }),
  play: z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    version: z.string().optional()
  }),
  role: z.object({
    id: z.string().min(1),
    display_name: z.string().min(1)
  }),
  recording: z.object({
    preferred_sample_rate_hz: z.number().int().positive(),
    preferred_channels: z.number().int().positive(),
    source_format: z.literal("wav")
  }),
  items: z.array(itemSchema)
});

export function validateRecordingRequestManifest(value: unknown): RecordingRequest {
  const manifest = manifestSchema.parse(value) satisfies RecordingRequestManifest;
  return {
    schemaVersion: manifest.schema_version,
    packageType: manifest.package_type,
    request: {
      id: manifest.request.id,
      kind: manifest.request.kind,
      createdAt: manifest.request.created_at,
      createdBy: manifest.request.created_by,
      notes: manifest.request.notes
    },
    play: {
      id: manifest.play.id,
      title: manifest.play.title,
      version: manifest.play.version
    },
    role: {
      id: manifest.role.id,
      displayName: manifest.role.display_name
    },
    recording: {
      preferredSampleRateHz: manifest.recording.preferred_sample_rate_hz,
      preferredChannels: manifest.recording.preferred_channels,
      sourceFormat: manifest.recording.source_format
    },
    items: manifest.items.map((item) => ({
      lineId: item.line_id,
      blockId: item.block_id,
      segmentId: item.segment_id,
      sequence: item.sequence,
      displayText: item.display_text,
      segmentText: item.segment_text,
      outputPath: item.output_path,
      cueText: item.cue_text,
      cueSpeaker: item.cue_speaker,
      previousText: item.previous_text,
      previousSpeaker: item.previous_speaker,
      nextText: item.next_text,
      nextSpeaker: item.next_speaker,
      sectionId: item.section_id,
      sectionTitle: item.section_title,
      sceneHeading: item.scene_heading,
      stageDirections: item.stage_directions ?? [],
      reason: item.reason,
      notes: item.notes,
      cueAudio: item.cue_audio,
      previousRecording: item.previous_recording,
      changed: item.changed,
      targetDurationMs: item.target_duration_ms,
      targetHesitationMs: item.target_hesitation_ms,
      simultaneous: item.simultaneous
    }))
  };
}
