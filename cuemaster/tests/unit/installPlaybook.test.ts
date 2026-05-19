import JSZip from "jszip";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  installPlaybook,
  PlaybookReplacementDeclinedError,
  playbookReplacementDecision
} from "../../src/playbook/installPlaybook";
import type { Playbook } from "../../src/domain/playbook";
import { db } from "../../src/storage/db";
import { playbookRepository } from "../../src/storage/playbookRepository";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";

describe("installPlaybook", () => {
  afterEach(async () => {
    vi.useRealTimers();
    await db.playbooks.clear();
    await db.audioAssets.clear();
    await db.jsonAssets.clear();
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
      importMetadata: playbook.importMetadata,
      production: {
        source: "published",
        version: "1@k9f4p2x8m1qd"
      }
    });
  });

  it("reports import progress while extracting, storing audio, and saving the Playbook", async () => {
    const file = await buildPlaybookFile("androcles-minimal.playbook.zip");
    const progress: string[] = [];

    await installPlaybook(file, {
      onProgress: (event) => {
        progress.push(event.phase === "storing-audio" ? `${event.phase}:${event.completed}/${event.total}` : event.phase);
      }
    });

    expect(progress[0]).toBe("extracting");
    expect(progress).toContain("saving-playbook");
    expect(progress.filter((event) => event.startsWith("storing-audio:"))).toHaveLength(requiredAudioPaths().length);
  });

  it("stores staging JSON assets when the Playbook includes blocking diagrams", async () => {
    const file = await buildPlaybookFile("androcles-minimal.playbook.zip", manifestWithStaging());

    await installPlaybook(file);

    await expect(db.jsonAssets.get(["androcles-minimal", "staging/diagram_manifest.json"])).resolves.toMatchObject({
      text: expect.stringContaining("quince.blocking.diagram_bundle")
    });
    await expect(db.jsonAssets.get(["androcles-minimal", "staging/checkpoints/scene-start.json"])).resolves.toMatchObject({
      text: "{}"
    });
    await expect(db.jsonAssets.get(["androcles-minimal", "staging/icons.svg"])).resolves.toMatchObject({
      text: expect.stringContaining("stage-icon-table")
    });
  });

  it("preserves local rehearsal progress when replacing an installed Playbook", async () => {
    const first = await buildPlaybookFile("androcles-minimal.playbook.zip");
    await installPlaybook(first);
    await db.sessions.put({
      playbookId: "androcles-minimal",
      roleId: "ANDROCLES",
      lineIndex: 1,
      cueDepth: 1,
      includeDirections: true,
      revealLine: false,
      showLinesByDefault: false,
      cueWindowPresetId: "full",
      playbackRate: 1,
      speakAlongEnabled: false,
      speakAlongPauseMs: 0,
      tempoTargetHesitationMs: 500,
      syncPracticeTiming: true,
      tempoTimingPreferred: false,
      updatedAt: 1
    });
    const replacementManifest = manifestWithProductionVersion("2@p2");
    const second = await buildPlaybookFile("androcles-minimal-v2.playbook.zip", replacementManifest);

    await installPlaybook(second);

    await expect(db.sessions.get(["androcles-minimal", "ANDROCLES"])).resolves.toMatchObject({
      lineIndex: 1
    });
    await expect(playbookRepository.get("androcles-minimal")).resolves.toMatchObject({
      production: { version: "2@p2" }
    });
  });

  it("requires confirmation before replacing with an older Playbook", async () => {
    await installPlaybook(await buildPlaybookFile("androcles-minimal-v2.playbook.zip", manifestWithProductionVersion("2@p2")));
    const older = await buildPlaybookFile("androcles-minimal-v1.playbook.zip", manifestWithProductionVersion("1@p1"));
    const confirmReplacement = vi.fn(() => false);

    await expect(installPlaybook(older, { confirmReplacement })).rejects.toBeInstanceOf(PlaybookReplacementDeclinedError);

    expect(confirmReplacement).toHaveBeenCalledWith(
      expect.objectContaining({
        risk: "older-version",
        requiresConfirmation: true
      })
    );
    await expect(playbookRepository.get("androcles-minimal")).resolves.toMatchObject({
      production: { version: "2@p2" }
    });
  });

  it("classifies production forks before replacement", () => {
    const decision = playbookReplacementDecision(
      playbookForReplacement("1@oldpub", "published"),
      playbookForReplacement("1@newpub", "published")
    );

    expect(decision.risk).toBe("fork");
    expect(decision.requiresConfirmation).toBe(true);
  });
});

async function buildPlaybookFile(filename: string, manifest = manifestFixture): Promise<File> {
  const zip = new JSZip();
  zip.file("manifest.json", JSON.stringify(manifest));
  if ((manifest as { staging?: unknown }).staging) {
    zip.file("staging/diagram_manifest.json", JSON.stringify(stagingManifest()));
    zip.file("staging/checkpoints/scene-start.json", "{}");
    zip.file("staging/deltas/scene-b1.json", "{}");
    zip.file("staging/icons.svg", '<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"></symbol></defs>');
  }

  for (const audioPath of requiredAudioPaths()) {
    zip.file(audioPath, "");
  }

  return new File([await zip.generateAsync({ type: "blob" })], filename, { type: "application/zip" });
}

function manifestWithStaging(): typeof manifestFixture {
  return {
    ...manifestFixture,
    format_version: "1.1.0",
    staging: {
      included: true,
      format: "quince.blocking.diagram_bundle",
      format_version: "1.0.0",
      manifest_path: "staging/diagram_manifest.json"
    }
  } as typeof manifestFixture;
}

function stagingManifest() {
  return {
    format: "quince.blocking.diagram_bundle",
    format_version: "1.0.0",
    icon_library: {
      format: "svg-symbols",
      path: "staging/icons.svg"
    },
    checkpoints: [{ id: "scene:start", scene_id: "1", path: "staging/checkpoints/scene-start.json" }],
    deltas: [
      {
        id: "scene:1@b1",
        scene_id: "1",
        beat_id: "b1",
        production_anchor: "1-1",
        from_checkpoint: "scene:start",
        path: "staging/deltas/scene-b1.json"
      }
    ]
  };
}

function manifestWithProductionVersion(version: string): typeof manifestFixture {
  return {
    ...manifestFixture,
    production: {
      ...manifestFixture.production,
      version,
      sequence: Number(version.split("@")[0]),
      publication_id: version.split("@")[1]
    }
  };
}

function playbookForReplacement(version: string | undefined, source: "published" | "working"): Playbook {
  return {
    id: "androcles-minimal",
    title: "Androcles",
    authors: [],
    production: { source, version },
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: []
  };
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
