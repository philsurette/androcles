import { extractPlaybookZip } from "./extractPlaybookZip";
import { normalizePlaybook } from "./normalizePlaybook";

export async function importPlaybook(file: File) {
  const extracted = await extractPlaybookZip(file);
  return normalizePlaybook(extracted.manifest);
}
