import { describe, expect, it } from "vitest";
import type { Playbook } from "../../src/domain/playbook";
import { importSuccessMessage } from "../../src/ui/importSuccessMessage";

describe("importSuccessMessage", () => {
  it("summarizes imported playbooks with roles, production version, and persistence", () => {
    expect(
      importSuccessMessage({
        playbook: playbook(["ANDROCLES", "MEGAERA"]),
        fileSizeBytes: 1024 * 1024,
        elapsedSeconds: 1.23,
        replaced: false,
        persistentStorage: true
      })
    ).toBe(
      "Imported Androcles and the Lion (1.0 MB) in 1.2s. Roles: ANDROCLES, MEGAERA. Published 1@k9f4p2x8m1qd. Persistent storage is enabled."
    );
  });

  it("summarizes replacement imports and long role lists without making the message huge", () => {
    expect(
      importSuccessMessage({
        playbook: playbook(["A", "B", "C", "D", "E", "F"]),
        fileSizeBytes: 512,
        elapsedSeconds: 10,
        replaced: true,
        persistentStorage: false
      })
    ).toContain("Replaced Androcles and the Lion (512 B) in 10.0s. 6 roles: A, B, C, D, E, and 1 more.");
  });
});

function playbook(roleIds: string[]): Playbook {
  return {
    id: "androcles",
    title: "Androcles and the Lion",
    authors: [],
    production: {
      source: "published",
      version: "1@k9f4p2x8m1qd"
    },
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: roleIds.map((id) => ({ id, displayName: id, reader: "Anonymous", parts: [0], lines: [] }))
  };
}
