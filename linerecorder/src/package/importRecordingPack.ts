import JSZip from "jszip";
import { validateRecordingPackManifest } from "../specs/validateRecordingPackManifest";
import type { RecordingPack } from "../domain/recordingPack";

export class RecordingPackImportError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "RecordingPackImportError";
  }
}

export async function importRecordingPack(file: File): Promise<RecordingPack> {
  const archive = await JSZip.loadAsync(file);
  const manifestFile = archive.file("manifest.json");
  if (!manifestFile) {
    throw new RecordingPackImportError("Recording pack is missing manifest.json.");
  }

  try {
    const manifest = JSON.parse(await manifestFile.async("string"));
    return validateRecordingPackManifest(manifest);
  } catch (error) {
    if (error instanceof RecordingPackImportError) {
      throw error;
    }
    throw new RecordingPackImportError("Recording pack manifest is invalid.", { cause: error });
  }
}
