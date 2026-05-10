import JSZip from "jszip";
import { validatePlaybookManifest } from "../specs/validatePlaybookManifest";
import { PlaybookAssetIndex, assertRequiredAudioAssetsPresent } from "./playbookAssetIndex";
import { PlaybookImportError } from "./playbookImportError";
import { ZodError } from "zod";

export async function extractPlaybookZip(file: Blob) {
  const zip = await loadZip(file);
  const manifestEntry = zip.file("manifest.json");
  if (!manifestEntry) {
    throw new PlaybookImportError("Playbook zip is missing manifest.json");
  }
  const manifest = validateManifestJson(await manifestEntry.async("text"));
  const assetIndex = PlaybookAssetIndex.fromZip(zip);
  assertRequiredAudioAssetsPresent(manifest, assetIndex);
  return { manifest, zip, assetIndex };
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
