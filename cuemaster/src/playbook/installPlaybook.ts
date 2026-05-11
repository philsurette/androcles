import type JSZip from "jszip";
import { indexedDbStorage } from "../storage/indexedDbStorage";
import { extractPlaybookZip } from "./extractPlaybookZip";
import { collectRequiredAudioAssetPaths } from "./playbookAssetIndex";
import { PlaybookImportError } from "./playbookImportError";
import { normalizePlaybook } from "./normalizePlaybook";

export async function installPlaybook(file: File) {
  const extracted = await extractPlaybookZip(file);
  const playbook = normalizePlaybook(extracted.manifest);
  playbook.importMetadata = {
    filename: file.name,
    sizeBytes: file.size,
    importedAt: Date.now()
  };
  await indexedDbStorage.playbooks.delete(playbook.id);
  await storeRequiredAudioAssets(playbook.id, extracted.zip, collectRequiredAudioAssetPaths(extracted.manifest));
  await indexedDbStorage.playbooks.save(playbook);
  return playbook;
}

async function storeRequiredAudioAssets(playbookId: string, zip: JSZip, assetPaths: string[]): Promise<void> {
  for (const assetPath of assetPaths) {
    const entry = zip.file(assetPath);
    if (!entry) {
      throw new PlaybookImportError(`Playbook zip is missing required audio asset: ${assetPath}`);
    }
    await indexedDbStorage.audioAssets.save({
      playbookId,
      path: assetPath,
      blob: await entry.async("blob")
    });
  }
}
