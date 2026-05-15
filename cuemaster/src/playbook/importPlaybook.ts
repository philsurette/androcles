import { extractPlaybookZip } from "./extractPlaybookZip";
import { normalizePlaybook } from "./normalizePlaybook";

export async function importPlaybook(file: File) {
  const extracted = await extractPlaybookZip(file);
  const playbook = normalizePlaybook(extracted.manifest);
  playbook.manifestText = extracted.manifestJson;
  return playbook;
}
