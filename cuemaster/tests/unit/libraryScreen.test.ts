import { describe, expect, it } from "vitest";
import type { Playbook } from "../../src/domain/playbook";
import { playbookProductionLabel, playbookProductionWarning } from "../../src/ui/playbookProductionPresentation";

describe("playbookProductionLabel", () => {
  it("labels published playbooks with their production version", () => {
    expect(playbookProductionLabel(playbook({ source: "published", version: "2@abc123" }))).toBe(
      "Published 2@abc123"
    );
  });

  it("warns when a library playbook was built from a working source", () => {
    const workingPlaybook = playbook({ source: "working" });

    expect(playbookProductionLabel(workingPlaybook)).toBe("Working source");
    expect(playbookProductionWarning(workingPlaybook)).toContain("unpublished working production");
  });
});

function playbook(production: Playbook["production"]): Playbook {
  return {
    id: "androcles",
    title: "Androcles and the Lion",
    authors: [],
    production,
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: []
  };
}
