import JSZip from "jszip";
import { ZodError } from "zod";
import { validatePlaybookManifest } from "../specs/validatePlaybookManifest";
import type { ExtractedAudioAsset, ExtractedPlaybookZipData } from "./extractedPlaybookZip";
import {
  PlaybookAssetIndex,
  assertRequiredAudioAssetsPresent,
  collectRequiredAudioAssetPaths
} from "./playbookAssetIndex";
import { PlaybookImportError } from "./playbookImportError";

export async function extractPlaybookZipData(file: Blob): Promise<ExtractedPlaybookZipData> {
  const zip = await loadZip(file);
  const manifestEntry = zip.file("manifest.json");
  if (!manifestEntry) {
    throw new PlaybookImportError("Playbook zip is missing manifest.json");
  }

  const manifest = validateManifestJson(await manifestEntry.async("text"));
  const assetPaths = Object.values(zip.files)
    .filter((entry) => !entry.dir)
    .map((entry) => entry.name);
  const assetIndex = new PlaybookAssetIndex(assetPaths);
  assertRequiredAudioAssetsPresent(manifest, assetIndex);

  return {
    manifest,
    assetPaths,
    audioAssets: await extractRequiredAudioAssets(zip, collectRequiredAudioAssetPaths(manifest))
  };
}

async function loadZip(file: Blob): Promise<JSZip> {
  try {
    return await JSZip.loadAsync(file);
  } catch (error) {
    throw new PlaybookImportError("Invalid Playbook zip", { cause: error });
  }
}

function validateManifestJson(manifestJson: string) {
  let parsedManifest: unknown;

  try {
    parsedManifest = JSON.parse(manifestJson);
  } catch (error) {
    throw new PlaybookImportError("Playbook manifest is not valid JSON", { cause: error });
  }

  try {
    return validatePlaybookManifest(parsedManifest);
  } catch (error) {
    if (error instanceof ZodError) {
      throw new PlaybookImportError(`Playbook manifest is invalid: ${error.issues[0]?.message ?? "unknown error"}`, {
        cause: error
      });
    }
    throw error;
  }
}

async function extractRequiredAudioAssets(zip: JSZip, assetPaths: string[]): Promise<ExtractedAudioAsset[]> {
  const audioAssets: ExtractedAudioAsset[] = [];

  for (const assetPath of assetPaths) {
    const entry = zip.file(assetPath);
    if (!entry) {
      throw new PlaybookImportError(`Playbook zip is missing required audio asset: ${assetPath}`);
    }
    audioAssets.push({
      path: assetPath,
      blob: withAudioMimeType(assetPath, await entry.async("blob"))
    });
  }

  return audioAssets;
}

function withAudioMimeType(assetPath: string, blob: Blob): Blob {
  const mimeType = audioMimeType(assetPath);
  if (!mimeType || blob.type === mimeType) {
    return blob;
  }
  return new Blob([blob], { type: mimeType });
}

function audioMimeType(assetPath: string): string | undefined {
  const extension = assetPath.toLowerCase().split(".").pop();
  switch (extension) {
    case "mp3":
      return "audio/mpeg";
    case "wav":
      return "audio/wav";
    default:
      return undefined;
  }
}
