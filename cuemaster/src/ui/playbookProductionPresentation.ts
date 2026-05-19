import type { Playbook } from "../domain/playbook";

export function playbookProductionLabel(playbook: Playbook): string {
  if (playbook.production.source === "working") {
    return playbook.production.version ? `Working source ${playbook.production.version}` : "Working source";
  }
  return playbook.production.version ? `Published ${playbook.production.version}` : "Published version unknown";
}

export function playbookProductionWarning(playbook: Playbook): string | null {
  if (playbook.production.source !== "working") {
    return null;
  }
  return "Built from an unpublished working production. Use this for review, not cast distribution.";
}
