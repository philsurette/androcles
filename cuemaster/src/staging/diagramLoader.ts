import { indexedDbStorage } from "../storage/indexedDbStorage";
import { applyDiagramDelta } from "./diagramDelta";
import { resolveDiagramTarget } from "./diagramResolver";
import type { DiagramBundleManifest, DiagramDelta, DiagramState } from "./diagramTypes";
import { sanitizeSvgIconLibrary } from "./svgIconLibrary";

export async function loadDiagramBundleManifest(playbookId: string, path: string): Promise<DiagramBundleManifest> {
  return parseJsonAsset<DiagramBundleManifest>(playbookId, path);
}

export async function loadDiagramIconLibrary(
  playbookId: string,
  manifest: DiagramBundleManifest
): Promise<string | null> {
  const path = manifest.icon_library?.path;
  if (!path) {
    return null;
  }
  const asset = await indexedDbStorage.jsonAssets.get(playbookId, path);
  if (!asset) {
    throw new Error(`Playbook staging asset is missing: ${path}`);
  }
  return sanitizeSvgIconLibrary(asset.text);
}

export async function loadDiagramStateForBlocking(
  playbookId: string,
  manifest: DiagramBundleManifest,
  lineId: string,
  blockingId?: string
): Promise<DiagramState> {
  const resolution = resolveDiagramTarget(manifest, lineId, blockingId);
  if (!resolution) {
    throw new Error("No blocking diagram target is available for this line");
  }

  const checkpoint = await parseJsonAsset<DiagramState>(playbookId, resolution.checkpoint.path);
  if (resolution.kind === "checkpoint") {
    return checkpoint;
  }

  const delta = await parseJsonAsset<DiagramDelta>(playbookId, resolution.delta.path);
  return applyDiagramDelta(checkpoint, delta, resolution.targetId);
}

async function parseJsonAsset<T>(playbookId: string, path: string): Promise<T> {
  const asset = await indexedDbStorage.jsonAssets.get(playbookId, path);
  if (!asset) {
    throw new Error(`Playbook staging asset is missing: ${path}`);
  }
  return JSON.parse(asset.text) as T;
}
