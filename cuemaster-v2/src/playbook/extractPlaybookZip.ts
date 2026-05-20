import JSZip from "jszip";
import type { LoadedPlaybook } from "../domain/playbook";
import type { PlaybookManifest } from "../specs/playbookManifest";
import { PlaybookNormalizer } from "./normalizePlaybook";

export class PlaybookZipImporter {
  async import(file: Blob): Promise<LoadedPlaybook> {
    const zip = await JSZip.loadAsync(file);
    const manifestFile = zip.file("manifest.json");
    if (manifestFile === null) {
      throw new Error("Playbook zip does not contain manifest.json.");
    }

    const manifest = JSON.parse(await manifestFile.async("string")) as PlaybookManifest;
    const playbook = new PlaybookNormalizer().normalize(manifest);
    const audioAssets = new Map<string, Blob>();

    for (const asset of manifest.assets) {
      const entry = zip.file(asset.path);
      if (entry === null) {
        if (asset.required) {
          throw new Error(`Playbook is missing required audio asset: ${asset.path}`);
        }
        continue;
      }
      audioAssets.set(asset.path, await entry.async("blob"));
    }

    return { playbook, audioAssets };
  }
}
