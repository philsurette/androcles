import type { DiagramBundleManifest, DiagramCheckpointRecord, DiagramDeltaRecord } from "./diagramTypes";

export type DiagramTargetResolution =
  | {
      kind: "delta";
      checkpoint: DiagramCheckpointRecord;
      delta: DiagramDeltaRecord;
      targetId: string;
    }
  | {
      kind: "checkpoint";
      checkpoint: DiagramCheckpointRecord;
    };

export function resolveDiagramTarget(
  manifest: DiagramBundleManifest,
  lineId: string,
  blockingId?: string
): DiagramTargetResolution | null {
  const anchors = candidateAnchors(lineId, blockingId);
  for (const anchor of anchors) {
    const delta = lastMatchingDelta(manifest, anchor);
    if (!delta) {
      continue;
    }
    const checkpoint = manifest.checkpoints.find((candidate) => candidate.id === delta.from_checkpoint);
    if (!checkpoint) {
      throw new Error(`Blocking diagram checkpoint ${delta.from_checkpoint} is missing`);
    }
    return { kind: "delta", checkpoint, delta, targetId: delta.id };
  }

  const sceneId = sceneIdFromLineId(lineId);
  const checkpoint = manifest.checkpoints.find((candidate) => candidate.scene_id === sceneId) ?? manifest.checkpoints[0];
  return checkpoint ? { kind: "checkpoint", checkpoint } : null;
}

function candidateAnchors(lineId: string, blockingId?: string): string[] {
  const anchors = [lineId];
  if (blockingId) {
    anchors.unshift(blockingId.replace(/:b\d+$/, ""));
    anchors.unshift(blockingId);
  }
  return [...new Set(anchors)];
}

function lastMatchingDelta(manifest: DiagramBundleManifest, anchor: string): DiagramDeltaRecord | null {
  const matches = manifest.deltas.filter(
    (delta) => delta.id === anchor || delta.production_anchor === anchor || `${delta.production_anchor ?? ""}:${delta.beat_id ?? ""}` === anchor
  );
  return matches.at(-1) ?? null;
}

function sceneIdFromLineId(lineId: string): string {
  return lineId.split("-")[0] ?? lineId;
}
