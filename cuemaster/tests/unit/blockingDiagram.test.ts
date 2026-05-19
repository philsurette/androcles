import { describe, expect, it } from "vitest";
import { applyDiagramDelta } from "../../src/staging/diagramDelta";
import { resolveDiagramTarget } from "../../src/staging/diagramResolver";
import type { DiagramBundleManifest, DiagramDelta, DiagramState } from "../../src/staging/diagramTypes";

describe("blocking diagram resolution", () => {
  it("maps a line-level blocking note to the packaged production anchor delta", () => {
    const manifest: DiagramBundleManifest = {
      format: "quince.blocking.diagram_bundle",
      format_version: "1.0.0",
      checkpoints: [{ id: "scene:5:start", scene_id: "5", path: "staging/checkpoints/5-start.json" }],
      deltas: [
        {
          id: "scene:5@b3",
          scene_id: "5",
          beat_id: "b3",
          production_anchor: "5-39",
          from_checkpoint: "scene:5:start",
          path: "staging/deltas/5-b3.json"
        }
      ]
    };

    expect(resolveDiagramTarget(manifest, "5-39", "5-39:b2")).toMatchObject({
      kind: "delta",
      targetId: "scene:5@b3"
    });
  });

  it("falls back to the scene checkpoint when a blocking note has no beat delta", () => {
    const manifest: DiagramBundleManifest = {
      format: "quince.blocking.diagram_bundle",
      format_version: "1.0.0",
      checkpoints: [{ id: "scene:P:start", scene_id: "P", path: "staging/checkpoints/P-start.json" }],
      deltas: []
    };

    expect(resolveDiagramTarget(manifest, "P-3", "P-3:b1")).toMatchObject({
      kind: "checkpoint",
      checkpoint: { id: "scene:P:start" }
    });
  });
});

describe("blocking diagram deltas", () => {
  it("applies entity and diagnostic operations to a checkpoint state", () => {
    const checkpoint: DiagramState = {
      format: "quince.blocking.diagram_state",
      format_version: "1.0",
      diagram_id: "scene:5:start",
      stage: { width: 30, depth: 20 },
      set_pieces: [{ id: "set_piece:table", kind: "set_piece", point: { x: 0, y: 10 } }],
      entities: [{ id: "actor:HAM", kind: "actor", label: "HAM", point: { x: 0, y: 3 } }],
      offstage: []
    };
    const delta: DiagramDelta = {
      format: "quince.blocking.diagram_delta",
      format_version: "1.0.0",
      from_checkpoint: "scene:5:start",
      targets: [
        {
          target_id: "scene:5@b3",
          scene_id: "5",
          beat_id: "b3",
          ops: [
            { op: "upsert_entity", entity: { id: "actor:HAM", kind: "actor", label: "HAM", point: { x: 4, y: 2 } } },
            { op: "remove_entity", id: "set_piece:table" },
            { op: "replace_diagnostics", diagnostics: ["moved HAM"] }
          ]
        }
      ]
    };

    const state = applyDiagramDelta(checkpoint, delta, "scene:5@b3");

    expect(state.beat_id).toBe("b3");
    expect(state.entities?.[0].point).toEqual({ x: 4, y: 2 });
    expect(state.set_pieces).toEqual([]);
    expect(state.diagnostics).toEqual(["moved HAM"]);
  });
});
