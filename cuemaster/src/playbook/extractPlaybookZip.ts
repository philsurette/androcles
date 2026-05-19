import type { ExtractedPlaybookZipData } from "./extractedPlaybookZip";
import { extractPlaybookZipData } from "./extractPlaybookZipData";
import { PlaybookAssetIndex } from "./playbookAssetIndex";
import { PlaybookImportError } from "./playbookImportError";

export async function extractPlaybookZip(file: Blob) {
  const extracted = shouldUseWorker() ? await extractInWorker(file) : await extractPlaybookZipData(file);

  return {
    manifest: extracted.manifest,
    assetIndex: new PlaybookAssetIndex(extracted.assetPaths),
    audioAssets: extracted.audioAssets,
    jsonAssets: extracted.jsonAssets
  };
}

function shouldUseWorker(): boolean {
  return typeof Worker !== "undefined" && typeof import.meta.url === "string";
}

function extractInWorker(file: Blob): Promise<ExtractedPlaybookZipData> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./extractPlaybookZipWorker.ts", import.meta.url), { type: "module" });

    worker.addEventListener("message", (event: MessageEvent<WorkerExtractionMessage>) => {
      worker.terminate();
      if (event.data.type === "success") {
        resolve(event.data.payload);
      } else {
        reject(new PlaybookImportError(event.data.message));
      }
    });

    worker.addEventListener("error", (event) => {
      worker.terminate();
      reject(new PlaybookImportError(`Playbook import worker failed: ${event.message}`));
    });

    worker.postMessage(file);
  });
}

type WorkerExtractionMessage =
  | { type: "success"; payload: ExtractedPlaybookZipData }
  | { type: "error"; message: string };
