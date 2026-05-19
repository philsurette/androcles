import { describe, expect, it } from "vitest";
import type { Line } from "../../src/domain/line";
import { buildBlockingNavigationItems } from "../../src/rehearsal/blockingNavigation";
import type { DiagramBundleManifest } from "../../src/staging/diagramTypes";

describe("blocking navigation", () => {
  it("builds whole-play navigation in line order", () => {
    const items = buildBlockingNavigationItems([line("P-1", "LILLIAN"), line("P-2", "CHRISTINE")], { mode: "all" }, null);

    expect(items.map((item) => item.blocking.id)).toEqual(["P-1:b1", "P-2:b1"]);
  });

  it("filters role navigation by blocking targets", () => {
    const items = buildBlockingNavigationItems(
      [line("P-1", "LILLIAN"), line("P-2", "CHRISTINE"), line("P-3", "*")],
      { mode: "role", roleId: "LILLIAN" },
      null
    );

    expect(items.map((item) => item.blocking.id)).toEqual(["P-1:b1", "P-3:b1"]);
  });

  it("skips notes without a diagram target when no checkpoint is available", () => {
    const items = buildBlockingNavigationItems(
      [line("P-1", "LILLIAN"), line("P-2", "LILLIAN")],
      { mode: "all" },
      { ...manifest(), checkpoints: [], deltas: [] }
    );

    expect(items.map((item) => item.blocking.id)).toEqual([]);
  });
});

function line(id: string, target: string): Line {
  return {
    id,
    blockId: id.replace("-", "."),
    partId: null,
    role: "LILLIAN",
    speaker: "LILLIAN",
    contentHash: `sha256:${id}`,
    cue: { speaker: "CHRISTINE", text: "Cue", audioPath: "audio/cue.wav", durationMs: 1000 },
    responseText: "Line.",
    responseSegments: [],
    directions: [],
    previousRoles: [],
    blocking: [
      {
        id: `${id}:b1`,
        contentHash: `sha256:${id}:b1`,
        placement: "before",
        targets: [target],
        text: "cross"
      }
    ]
  };
}

function manifest(): DiagramBundleManifest {
  return {
    format: "quince.blocking.diagram_bundle",
    format_version: "1.0.0",
    checkpoints: [{ id: "scene:P:start", scene_id: "P", path: "staging/checkpoints/P-start.json" }],
    deltas: [
      {
        id: "scene:P@b1",
        scene_id: "P",
        beat_id: "b1",
        production_anchor: "P-1",
        from_checkpoint: "scene:P:start",
        path: "staging/deltas/P-b1.json"
      }
    ]
  };
}
