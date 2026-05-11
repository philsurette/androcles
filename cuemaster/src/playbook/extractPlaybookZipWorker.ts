import { extractPlaybookZipData } from "./extractPlaybookZipData";

self.addEventListener("message", async (event: MessageEvent<Blob>) => {
  try {
    self.postMessage({ type: "success", payload: await extractPlaybookZipData(event.data) });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : String(error)
    });
  }
});

