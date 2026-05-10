import JSZip from "jszip";
import { validatePlaybookManifest } from "../specs/validatePlaybookManifest";

export async function extractPlaybookZip(file: Blob) {
  const zip = await JSZip.loadAsync(file);
  const manifestEntry = zip.file("manifest.json");
  if (!manifestEntry) {
    throw new Error("Playbook zip is missing manifest.json");
  }
  const manifest = validatePlaybookManifest(JSON.parse(await manifestEntry.async("text")));
  return { manifest, zip };
}
