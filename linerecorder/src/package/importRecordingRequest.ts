import JSZip from "jszip";
import { validateRecordingRequestManifest } from "../specs/validateRecordingRequestManifest";
import type { RecordingRequest } from "../domain/recordingRequest";

export class RecordingRequestImportError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "RecordingRequestImportError";
  }
}

export async function importRecordingRequest(file: File): Promise<RecordingRequest> {
  const archive = await JSZip.loadAsync(file);
  const manifestFile = archive.file("manifest.json");
  if (!manifestFile) {
    throw new RecordingRequestImportError("Recording Request is missing manifest.json.");
  }

  try {
    const manifest = JSON.parse(await manifestFile.async("string"));
    return validateRecordingRequestManifest(manifest);
  } catch (error) {
    if (error instanceof RecordingRequestImportError) {
      throw error;
    }
    throw new RecordingRequestImportError("Recording Request manifest is invalid.", { cause: error });
  }
}
