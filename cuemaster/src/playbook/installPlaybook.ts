import { indexedDbStorage } from "../storage/indexedDbStorage";
import type { ExtractedAudioAsset } from "./extractedPlaybookZip";
import { extractPlaybookZip } from "./extractPlaybookZip";
import { normalizePlaybook } from "./normalizePlaybook";

function newBuildId(): string {
  const randomPart = (globalThis.crypto as Crypto | undefined)?.randomUUID
    ? globalThis.crypto.randomUUID()
    : `${Math.floor(Math.random() * Number.MAX_SAFE_INTEGER)}-${Date.now()}`;
  return randomPart;
}

export type PlaybookImportProgress =
  | { phase: "extracting" }
  | { phase: "storing-audio"; completed: number; total: number }
  | { phase: "saving-playbook" };

export type PlaybookImportOptions = {
  onProgress?: (progress: PlaybookImportProgress) => void;
};

export async function installPlaybook(file: File, options: PlaybookImportOptions = {}) {
  options.onProgress?.({ phase: "extracting" });
  const extracted = await extractPlaybookZip(file);
  const playbook = normalizePlaybook(extracted.manifest);
  playbook.importMetadata = {
    filename: file.name,
    sizeBytes: file.size,
    importedAt: Date.now(),
    buildId: newBuildId()
  };
  await indexedDbStorage.playbooks.delete(playbook.id);
  await storeRequiredAudioAssets(playbook.id, extracted.audioAssets, options);
  options.onProgress?.({ phase: "saving-playbook" });
  await indexedDbStorage.playbooks.save(playbook);
  return playbook;
}

async function storeRequiredAudioAssets(
  playbookId: string,
  audioAssets: ExtractedAudioAsset[],
  options: PlaybookImportOptions
): Promise<void> {
  for (const [index, audioAsset] of audioAssets.entries()) {
    await indexedDbStorage.audioAssets.save({
      playbookId,
      path: audioAsset.path,
      blob: audioAsset.blob
    });
    options.onProgress?.({ phase: "storing-audio", completed: index + 1, total: audioAssets.length });
  }
}
