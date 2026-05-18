import { indexedDbStorage } from "../storage/indexedDbStorage";
import type { Playbook } from "../domain/playbook";
import type { ExtractedAudioAsset } from "./extractedPlaybookZip";
import { extractPlaybookZip } from "./extractPlaybookZip";
import { normalizePlaybook } from "./normalizePlaybook";

export type PlaybookImportProgress =
  | { phase: "extracting" }
  | { phase: "storing-audio"; completed: number; total: number }
  | { phase: "saving-playbook" };

export type PlaybookImportOptions = {
  onProgress?: (progress: PlaybookImportProgress) => void;
  onReplacementDecision?: (decision: PlaybookReplacementDecision) => void;
  confirmReplacement?: (decision: PlaybookReplacementDecision) => boolean | Promise<boolean>;
};

export type PlaybookReplacementRisk = "same-version" | "newer-version" | "older-version" | "fork" | "working-source" | "unknown";

export type PlaybookReplacementDecision = {
  existing: Playbook;
  incoming: Playbook;
  risk: PlaybookReplacementRisk;
  requiresConfirmation: boolean;
  message: string;
};

export class PlaybookReplacementDeclinedError extends Error {
  constructor(message = "Playbook replacement was cancelled.") {
    super(message);
    this.name = "PlaybookReplacementDeclinedError";
  }
}

export async function installPlaybook(file: File, options: PlaybookImportOptions = {}) {
  options.onProgress?.({ phase: "extracting" });
  const extracted = await extractPlaybookZip(file);
  const playbook = normalizePlaybook(extracted.manifest);
  const existing = await indexedDbStorage.playbooks.get(playbook.id);
  playbook.manifestText = JSON.stringify(extracted.manifest);
  playbook.importMetadata = {
    filename: file.name,
    sizeBytes: file.size,
    importedAt: Date.now(),
  };
  if (existing) {
    const decision = playbookReplacementDecision(existing, playbook);
    options.onReplacementDecision?.(decision);
    if (decision.requiresConfirmation) {
      const confirmed = await options.confirmReplacement?.(decision);
      if (!confirmed) {
        throw new PlaybookReplacementDeclinedError();
      }
    }
  }
  await indexedDbStorage.audioAssets.deleteForPlaybook(playbook.id);
  await storeRequiredAudioAssets(playbook.id, extracted.audioAssets, options);
  options.onProgress?.({ phase: "saving-playbook" });
  await indexedDbStorage.playbooks.save(playbook);
  return playbook;
}

export function playbookReplacementDecision(existing: Playbook, incoming: Playbook): PlaybookReplacementDecision {
  const existingVersion = parseProductionVersion(existing.production.version);
  const incomingVersion = parseProductionVersion(incoming.production.version);
  const risk = replacementRisk(existing, incoming, existingVersion, incomingVersion);
  return {
    existing,
    incoming,
    risk,
    requiresConfirmation: risk === "older-version" || risk === "fork" || risk === "working-source" || risk === "unknown",
    message: replacementMessage(existing, incoming, risk)
  };
}

function replacementRisk(
  existing: Playbook,
  incoming: Playbook,
  existingVersion: ParsedProductionVersion | null,
  incomingVersion: ParsedProductionVersion | null
): PlaybookReplacementRisk {
  if (incoming.production.source === "working") {
    return "working-source";
  }
  if (!existingVersion || !incomingVersion) {
    return "unknown";
  }
  if (incomingVersion.sequence === existingVersion.sequence && incomingVersion.publicationId !== existingVersion.publicationId) {
    return "fork";
  }
  if (incomingVersion.sequence < existingVersion.sequence) {
    return "older-version";
  }
  if (incomingVersion.sequence > existingVersion.sequence) {
    return "newer-version";
  }
  return "same-version";
}

function replacementMessage(existing: Playbook, incoming: Playbook, risk: PlaybookReplacementRisk): string {
  const existingLabel = productionLabel(existing);
  const incomingLabel = productionLabel(incoming);
  if (risk === "older-version") {
    return `This Playbook is older than the installed copy (${incomingLabel} replaces ${existingLabel}).`;
  }
  if (risk === "fork") {
    return `This Playbook has the same production sequence as the installed copy but a different publication id (${incomingLabel} replaces ${existingLabel}).`;
  }
  if (risk === "working-source") {
    return `This Playbook was built from a working production source and will replace ${existingLabel}.`;
  }
  if (risk === "unknown") {
    return `This Playbook has incomplete production version metadata and will replace ${existingLabel}.`;
  }
  return `Replacing ${existingLabel} with ${incomingLabel}.`;
}

function productionLabel(playbook: Playbook): string {
  if (playbook.production.source === "working") {
    return playbook.production.version ? `working ${playbook.production.version}` : "working source";
  }
  return playbook.production.version ? `published ${playbook.production.version}` : "published version unknown";
}

type ParsedProductionVersion = {
  sequence: number;
  publicationId: string;
};

function parseProductionVersion(value: string | undefined): ParsedProductionVersion | null {
  if (!value) {
    return null;
  }
  const [sequenceText, publicationId] = value.split("@");
  const sequence = Number(sequenceText);
  if (!Number.isInteger(sequence) || sequence <= 0 || !publicationId) {
    return null;
  }
  return { sequence, publicationId };
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
