import type { Playbook } from "../domain/playbook";
import { formatBytes } from "../platform/storageEstimate";
import { playbookProductionLabel } from "./playbookProductionPresentation";

export type ImportSuccessMessageOptions = {
  playbook: Playbook;
  fileSizeBytes: number;
  elapsedSeconds: number;
  replaced: boolean;
  persistentStorage: boolean | null;
};

export function importSuccessMessage({
  playbook,
  fileSizeBytes,
  elapsedSeconds,
  replaced,
  persistentStorage
}: ImportSuccessMessageOptions): string {
  const action = replaced ? "Replaced" : "Imported";
  const roleSummary = roleListSummary(playbook.roles.map((role) => role.id));
  const persistence =
    persistentStorage === null
      ? ""
      : persistentStorage
        ? " Persistent storage is enabled."
        : " Persistent storage was not granted; the browser may remove this Playbook if storage is low.";
  const production = ` ${playbookProductionLabel(playbook)}.`;
  const changes = playbook.production.changeSummary ? ` Production change: ${playbook.production.changeSummary}.` : "";
  const blocking = playbook.production.blockingChanges?.length
    ? ` Blocking updates: ${playbook.production.blockingChanges.length}.`
    : "";
  return `${action} ${playbook.title} (${formatBytes(fileSizeBytes)}) in ${elapsedSeconds.toFixed(1)}s. ${roleSummary}.${production}${changes}${blocking}${persistence}`;
}

function roleListSummary(roleIds: string[]): string {
  if (roleIds.length === 0) {
    return "No rehearsable roles are available";
  }
  if (roleIds.length <= 5) {
    return `Roles: ${roleIds.join(", ")}`;
  }
  return `${roleIds.length} roles: ${roleIds.slice(0, 5).join(", ")}, and ${roleIds.length - 5} more`;
}
