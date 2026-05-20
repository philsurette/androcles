import { describe, expect, it } from "vitest";
import { fairiesDemoManifest } from "../../src/fixtures/fairiesDemoManifest";
import { PlaybookNormalizer } from "../../src/playbook/normalizePlaybook";

describe("PlaybookNormalizer", () => {
  it("normalizes Fairies role lines from the playbook manifest shape", () => {
    const playbook = new PlaybookNormalizer().normalize(fairiesDemoManifest);

    expect(playbook.title).toBe("The Curious Case of the Cottingley Fairies");
    expect(playbook.roles.map((role) => role.id)).toEqual(["CHRISTINE", "LILLIAN"]);
    expect(playbook.roles.find((role) => role.id === "LILLIAN")?.lines[0]).toMatchObject({
      id: "P-3",
      cue: { speaker: "CHRISTINE", text: "Do you mind if I record?" },
      responseText: "Please do."
    });
  });

  it("attaches standalone and inline blocking notes to role lines", () => {
    const playbook = new PlaybookNormalizer().normalize(fairiesDemoManifest);
    const lillian = playbook.roles.find((role) => role.id === "LILLIAN");

    expect(lillian?.lines.find((line) => line.id === "P-3")?.blocking.map((blocking) => blocking.text)).toEqual([
      "@ interview_chair face=CHRISTINE"
    ]);
    expect(lillian?.lines.find((line) => line.id === "3-2")?.blocking.map((blocking) => blocking.text)).toEqual([
      "leans in to see the drawing"
    ]);
  });
});
