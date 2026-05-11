import type JSZip from "jszip";
import { audioAssetRepository } from "../storage/audioAssetRepository";
import { playbookRepository } from "../storage/playbookRepository";
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
  await playbookRepository.delete(playbook.id);
  await storeRequiredAudioAssets(playbook.id, extracted.zip, collectRequiredAudioAssetPaths(extracted.manifest));
  await playbookRepository.save(playbook);
  return playbook;
}

async function storeRequiredAudioAssets(playbookId: string, zip: JSZip, assetPaths: string[]): Promise<void> {
  for (const assetPath of assetPaths) {
    const entry = zip.file(assetPath);
    if (!entry) {
      throw new PlaybookImportError(`Playbook zip is missing required audio asset: ${assetPath}`);
    }
    await audioAssetRepository.save({
      playbookId,
      path: assetPath,
      blob: await entry.async("blob")
    });
  }
}
