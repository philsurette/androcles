import { z } from "zod";
import type { PlaybookManifest } from "./playbookManifest";

const audioAssetSchema = z.object({
  path: z.string().min(1),
  duration_ms: z.number().int().nonnegative(),
  required: z.boolean()
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
  roles: z.array(z.any()),
  assets: z.array(audioAssetSchema)
});

export function validatePlaybookManifest(input: unknown): PlaybookManifest {
  return manifestSchema.parse(input) as PlaybookManifest;
}
