import { z } from "zod";
import { validatePackageFormatVersion } from "./packageFormatVersion";
import type { RoleRecordingsManifest } from "./recordingPackageManifest";

const productionIdSchema = z
  .string()
  .regex(
    /^[A-Z0-9]+(?:\.[A-Z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?(?::[sdm][0-9]+)?$/,
    "Expected a production id such as I-3 or I-3:s1"
  );

const recordingSchema = z.object({
  id: productionIdSchema,
  line_id: productionIdSchema,
  block_id: z.string().min(1),
  segment_id: z.string().min(1),
  line_content_hash: z.string().regex(/^sha256:[0-9a-f]{64}$/),
  segment_content_hash: z.string().regex(/^sha256:[0-9a-f]{64}$/),
  audio_path: z.string().min(1),
  recorded_at: z.string().min(1),
  floor_noise_id: z.string().min(1).optional(),
  duration_ms: z.number().int().nonnegative(),
  sample_rate_hz: z.number().int().positive(),
  channels: z.number().int().positive(),
  input_quality: z
    .object({
      peak_energy: z.number().nonnegative(),
      level_counts: z.object({
        no_signal: z.number().int().nonnegative(),
        too_quiet: z.number().int().nonnegative(),
        good: z.number().int().nonnegative(),
        clipping: z.number().int().nonnegative()
      })
    })
    .optional(),
  status: z.literal("accepted")
});

const floorNoiseRecordingSchema = z.object({
  id: z.string().min(1),
  audio_path: z.string().min(1),
  recorded_at: z.string().min(1),
  duration_ms: z.number().int().nonnegative(),
  sample_rate_hz: z.number().int().positive(),
  channels: z.number().int().positive(),
  device_label: z.string().min(1),
  mode: z.string().min(1)
});

const roleRecordingsSchema = z.object({
  schema_version: z.literal(1),
  format_version: z.string().regex(/^\d+\.\d+\.\d+$/),
  package_type: z.literal("role_recordings"),
  complete: z.boolean(),
  play: z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    version: z.string().optional()
  }),
  role: z.object({
    id: z.string().min(1),
    display_name: z.string().min(1)
  }),
  floor_noise_recordings: z.array(floorNoiseRecordingSchema).optional(),
  recordings: z.array(recordingSchema),
  missing_segment_ids: z.array(productionIdSchema)
});

export function validateRoleRecordingsManifest(value: unknown): RoleRecordingsManifest {
  validatePackageFormatVersion(value, "role_recordings", "1.0.0");
  return roleRecordingsSchema.parse(value) satisfies RoleRecordingsManifest;
}
