import { z } from "zod";
import type { PlaybookManifest } from "./playbookManifest";

const audioAssetSchema = z.object({
  path: z.string().min(1),
  duration_ms: z.number().int().nonnegative(),
  required: z.boolean(),
  cue_start_offsets: z
    .array(
      z.object({
        requested_window_ms: z.number().int().nonnegative(),
        start_ms: z.number().int().nonnegative(),
        confidence: z.enum(["exact", "boundary", "fallback"])
      })
    )
    .optional()
});

const contentHashSchema = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const productionIdSchema = z
  .string()
  .regex(
    /^[A-Z0-9]+(?:\.[A-Z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?(?::[sdmb][0-9]+)?$/,
    "Expected a production id such as I-3 or I-3:s1"
  );

const directionSchema = z.object({
  id: productionIdSchema,
  segment_id: z.string().min(1),
  content_hash: contentHashSchema,
  text: z.string(),
  placement: z.enum(["top_level", "inline", "description"])
});

const blockingSchema = directionSchema.extend({
  targets: z.array(z.string().min(1)).min(1)
});

const sectionSchema = z.object({
  id: z.string().min(1),
  part_id: z.number().int().nullable(),
  block_id: z.string().min(1).nullable(),
  title: z.string().min(1),
  ordinal: z.number().int().nonnegative()
});

const responseSegmentSchema = z.object({
  id: productionIdSchema,
  segment_id: z.string().min(1),
  content_hash: contentHashSchema,
  owners: z.array(z.string().min(1)).min(1),
  text: z.string(),
  audio: audioAssetSchema,
  simultaneous: z.boolean().optional()
});

const lineSchema = z.object({
  id: productionIdSchema,
  part_id: z.number().int().nullable(),
  block_id: z.string().min(1),
  role: z.string().min(1),
  speaker: z.string().min(1),
  content_hash: contentHashSchema,
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
  blocking: z.array(blockingSchema).optional(),
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
  build: z.object({
    buildId: z.string().min(1),
    buildTimestamp: z.string().min(1),
  }),
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
  sections: z.array(sectionSchema),
  context: z.array(
    z.object({
      id: productionIdSchema,
      part_id: z.number().int().nullable(),
      block_id: z.string().min(1),
      kind: z.enum(["heading", "description", "direction", "blocking"]),
      speaker: z.literal("_NARRATOR"),
      text: z.string(),
      audio: audioAssetSchema.optional(),
      content_hash: contentHashSchema,
      targets: z.array(z.string().min(1)).optional(),
      placement: z.enum(["before", "after"]).optional()
    })
  ),
  roles: z.array(roleSchema),
  assets: z.array(audioAssetSchema)
});

export function validatePlaybookManifest(input: unknown): PlaybookManifest {
  return manifestSchema.parse(input) as PlaybookManifest;
}
