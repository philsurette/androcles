import type JSZip from "jszip";
import type { ManifestAudioAsset, PlaybookManifest } from "../specs/playbookManifest";
import { PlaybookImportError } from "./playbookImportError";

export class PlaybookAssetIndex {
  private readonly entries: Set<string>;

  constructor(entries: Iterable<string>) {
    this.entries = new Set(Array.from(entries, normalizeAssetPath));
  }

  static fromZip(zip: JSZip): PlaybookAssetIndex {
    return new PlaybookAssetIndex(
      Object.values(zip.files)
        .filter((entry) => !entry.dir)
        .map((entry) => entry.name)
    );
  }

  has(path: string): boolean {
    return this.entries.has(normalizeAssetPath(path));
  }
}

export function collectRequiredAudioAssetPaths(manifest: PlaybookManifest): string[] {
  const paths = new Set<string>();

  for (const asset of manifest.assets) {
    addRequiredAudioPath(paths, asset);
  }

  for (const contextBlock of manifest.context) {
    if (contextBlock.audio) {
      addRequiredAudioPath(paths, contextBlock.audio);
    }
  }

  for (const role of manifest.roles) {
    for (const line of role.lines) {
      addRequiredAudioPath(paths, line.cue.audio);
      for (const segment of line.response.segments) {
        addRequiredAudioPath(paths, segment.audio);
      }
    }
  }

  return Array.from(paths).sort();
}

export function assertRequiredAudioAssetsPresent(
  manifest: PlaybookManifest,
  assetIndex: PlaybookAssetIndex
): void {
  const missingPaths = collectRequiredAudioAssetPaths(manifest).filter((path) => !assetIndex.has(path));

  if (missingPaths.length === 0) {
    return;
  }

  if (missingPaths.length === 1) {
    throw new PlaybookImportError(`Playbook zip is missing required audio asset: ${missingPaths[0]}`);
  }

  throw new PlaybookImportError(
    `Playbook zip is missing ${missingPaths.length} required audio assets: ${missingPaths.join(", ")}`
  );
}

function addRequiredAudioPath(paths: Set<string>, asset: ManifestAudioAsset): void {
  if (asset.required) {
    paths.add(normalizeAssetPath(asset.path));
  }
}

function normalizeAssetPath(path: string): string {
  return path.replace(/^\/+/, "");
}
