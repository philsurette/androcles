import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { cueWindowPresets } from "../../src/rehearsal/cueWindowPreset";

describe("cueWindowPresets", () => {
  it("matches the shared planning spec used by Stager", () => {
    const spec = JSON.parse(
      readFileSync(resolve(__dirname, "../../../planning/specs/cue_window_presets.json"), "utf8")
    ) as {
      cue_window_presets: Array<{ id: string; label: string; window_ms: number | null }>;
    };

    expect(cueWindowPresets).toEqual(
      spec.cue_window_presets.map((preset) => ({
        id: preset.id,
        label: preset.label,
        windowMs: preset.window_ms
      }))
    );
  });
});
