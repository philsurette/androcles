import { z } from "zod";
import type { PlaybookManifest } from "./playbookManifest";

const audioAssetSchema = z.object({
  path: z.string().min(1),
  duration_ms: z.number().int().nonnegative(),
  required: z.boolean()
});

const directionSchema = z.object({
  segment_id: z.string().min(1),
  text: z.string(),
  placement: z.enum(["top_level", "inline", "description"])
});

const responseSegmentSchema = z.object({
  id: z.string().min(1),
  owners: z.array(z.string().min(1)).min(1),
  text: z.string(),
  audio: audioAssetSchema,
  simultaneous: z.boolean().optional()
});

const lineSchema = z.object({
  id: z.string().min(1),
  part_id: z.number().int().nullable(),
  block_id: z.string().min(1),
  role: z.string().min(1),
  speaker: z.string().min(1),
  cue: z.object({
    speaker: z.string().min(1),
    text: z.string(),
    audio: audioAssetSchema
  }),
  response: z.object({
    text: z.string(),
    segments: z.array(responseSegmentSchema).min(1)
  }),
  directions: z.array(directionSchema),
  previous_roles: z.array(z.string()),
  simultaneous: z.boolean().optional(),
  timing: z
    .object({
      target_hesitation_ms: z.number().int().nonnegative().optional()
    })
    .optional()
});

const roleSchema = z.object({
  id: z.string().min(1),
  display_name: z.string().min(1),
  reader: z.string(),
  meta: z.boolean(),
  parts: z.array(z.number().int().nullable()),
  lines: z.array(lineSchema)
});

const manifestSchema = z.object({
  schema_version: z.literal(1),
  play: z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    authors: z.array(z.string()),
    source: z.string().optional()
  }),
  reading: z.object({
    type: z.string().min(1),
    build_type: z.string().min(1)
  }),
  context: z.array(
    z.object({
      id: z.string().min(1),
      part_id: z.number().int().nullable(),
      block_id: z.string().min(1),
      kind: z.enum(["heading", "description", "direction"]),
      speaker: z.literal("_NARRATOR"),
      text: z.string(),
      audio: audioAssetSchema
    })
  ),
  roles: z.array(roleSchema),
  assets: z.array(audioAssetSchema)
});

export function validatePlaybookManifest(input: unknown): PlaybookManifest {
  return manifestSchema.parse(input) as PlaybookManifest;
}
