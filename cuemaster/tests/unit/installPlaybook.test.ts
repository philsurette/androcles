import JSZip from "jszip";
import { afterEach, describe, expect, it, vi } from "vitest";
import { installPlaybook } from "../../src/playbook/installPlaybook";
import { db } from "../../src/storage/db";
import { playbookRepository } from "../../src/storage/playbookRepository";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";

describe("installPlaybook", () => {
  afterEach(async () => {
    vi.useRealTimers();
    await db.playbooks.clear();
    await db.audioAssets.clear();
    await db.sessions.clear();
    await db.timingAttempts.clear();
    await db.bookmarks.clear();
  });

  it("stores import metadata with the persisted Playbook", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-05-11T14:00:00Z"));
    const file = await buildPlaybookFile("androcles-minimal.playbook.zip");

    const playbook = await installPlaybook(file);

    expect(playbook.importMetadata).toEqual({
      filename: "androcles-minimal.playbook.zip",
      sizeBytes: file.size,
      importedAt: Date.parse("2026-05-11T14:00:00Z")
    });
    await expect(playbookRepository.get("androcles-minimal")).resolves.toMatchObject({
      importMetadata: playbook.importMetadata
    });
  });
});

async function buildPlaybookFile(filename: string): Promise<File> {
  const zip = new JSZip();
  zip.file("manifest.json", JSON.stringify(manifestFixture));

  for (const audioPath of requiredAudioPaths()) {
    zip.file(audioPath, "");
  }

  return new File([await zip.generateAsync({ type: "blob" })], filename, { type: "application/zip" });
}

function requiredAudioPaths(): string[] {
  const paths = new Set<string>();
  for (const contextBlock of manifestFixture.context) {
    paths.add(contextBlock.audio.path);
  }
  for (const role of manifestFixture.roles) {
    for (const line of role.lines) {
      paths.add(line.cue.audio.path);
      for (const segment of line.response.segments) {
        paths.add(segment.audio.path);
      }
    }
  }
  return [...paths];
}
