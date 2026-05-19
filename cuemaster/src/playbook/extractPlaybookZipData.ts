import JSZip from "jszip";
import { ZodError } from "zod";
import { validatePlaybookManifest } from "../specs/validatePlaybookManifest";
import type { ExtractedAudioAsset, ExtractedJsonAsset, ExtractedPlaybookZipData } from "./extractedPlaybookZip";
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

  const manifestJson = await manifestEntry.async("text");
  const manifest = validateManifestJson(manifestJson);
  const assetPaths = Object.values(zip.files)
    .filter((entry) => !entry.dir)
    .map((entry) => entry.name);
  const assetIndex = new PlaybookAssetIndex(assetPaths);
  assertRequiredAudioAssetsPresent(manifest, assetIndex);

  return {
    manifest,
    manifestJson,
    assetPaths,
    audioAssets: await extractRequiredAudioAssets(zip, collectRequiredAudioAssetPaths(manifest)),
    jsonAssets: await extractStagingJsonAssets(zip, manifest)
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
      throw new PlaybookImportError(`Playbook manifest is invalid: ${formatZodIssue(error)}`, {
        cause: error
      });
    }
    throw error;
  }
}

function formatZodIssue(error: ZodError): string {
  const issue = error.issues[0];
  if (!issue) {
    return "unknown error";
  }
  const path = issue.path.length > 0 ? `${issue.path.join(".")}: ` : "";
  return `${path}${issue.message}`;
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

async function extractStagingJsonAssets(zip: JSZip, manifest: ReturnType<typeof validatePlaybookManifest>): Promise<ExtractedJsonAsset[]> {
  if (!manifest.staging) {
    return [];
  }

  const manifestPath = manifest.staging.manifest_path;
  const manifestEntry = zip.file(manifestPath);
  if (!manifestEntry) {
    throw new PlaybookImportError(`Playbook zip is missing staging manifest: ${manifestPath}`);
  }

  const stagingManifestText = await manifestEntry.async("text");
  const stagingManifest = parseStagingManifest(stagingManifestText, manifestPath);
  const paths = new Set<string>([manifestPath]);
  for (const checkpoint of stagingManifest.checkpoints ?? []) {
    if (typeof checkpoint.path === "string") {
      paths.add(checkpoint.path);
    }
  }
  for (const delta of stagingManifest.deltas ?? []) {
    if (typeof delta.path === "string") {
      paths.add(delta.path);
    }
  }

  const assets: ExtractedJsonAsset[] = [];
  for (const path of paths) {
    const entry = zip.file(path);
    if (!entry) {
      throw new PlaybookImportError(`Playbook zip is missing staging asset: ${path}`);
    }
    assets.push({ path, text: path === manifestPath ? stagingManifestText : await entry.async("text") });
  }
  return assets;
}

function parseStagingManifest(text: string, path: string): { checkpoints?: Array<{ path?: unknown }>; deltas?: Array<{ path?: unknown }> } {
  try {
    const parsed = JSON.parse(text) as { checkpoints?: Array<{ path?: unknown }>; deltas?: Array<{ path?: unknown }> };
    if (!parsed || typeof parsed !== "object") {
      throw new Error("Staging manifest is not a JSON object");
    }
    return parsed;
  } catch (error) {
    throw new PlaybookImportError(`Playbook staging manifest is not valid JSON: ${path}`, { cause: error });
  }
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
