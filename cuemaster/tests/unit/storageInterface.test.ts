import { describe, expect, it } from "vitest";
import type { Bookmark } from "../../src/domain/bookmark";
import type { Playbook } from "../../src/domain/playbook";
import type { RehearsalSession } from "../../src/domain/session";
import type { TimingAttempt } from "../../src/domain/timingAttempt";
import type { StoredAudioAsset } from "../../src/storage/audioAssetRepository";
import type { CuemasterStorage } from "../../src/storage/storage";

describe("CuemasterStorage", () => {
  it("can be implemented without IndexedDB", async () => {
    const storage: CuemasterStorage = new MemoryStorage();
    const playbook = minimalPlaybook();

    await storage.playbooks.save(playbook);
    await storage.sessions.save(session(playbook.id, "ANDROCLES", 1));
    await storage.bookmarks.save(bookmark(playbook.id, "ANDROCLES", "line-one"));
    await storage.timingAttempts.save(attempt(playbook.id, "ANDROCLES", "line-one"));
    await storage.audioAssets.save({
      playbookId: playbook.id,
      path: "audio/line.wav",
      blob: new Blob(["audio"])
    });

    await expect(storage.playbooks.list()).resolves.toEqual([playbook]);
    await expect(storage.sessions.getLatestForPlaybook(playbook.id)).resolves.toMatchObject({ lineIndex: 1 });
    await expect(storage.bookmarks.listForRole(playbook.id, "ANDROCLES")).resolves.toHaveLength(1);
    await expect(storage.timingAttempts.latestForLine(playbook.id, "ANDROCLES", "line-one")).resolves.toMatchObject({
      lineId: "line-one"
    });
    await expect(storage.audioAssets.get(playbook.id, "audio/line.wav")).resolves.toMatchObject({
      path: "audio/line.wav"
    });
  });
});

class MemoryStorage implements CuemasterStorage {
  private readonly playbookRecords = new Map<string, Playbook>();
  private readonly sessionRecords = new Map<string, RehearsalSession>();
  private readonly audioAssetRecords = new Map<string, StoredAudioAsset>();
  private readonly bookmarkRecords = new Map<string, Bookmark>();
  private readonly timingAttemptRecords = new Map<string, TimingAttempt>();

  readonly playbooks = {
    list: async () => [...this.playbookRecords.values()],
    get: async (id: string) => this.playbookRecords.get(id),
    save: async (playbook: Playbook) => {
      this.playbookRecords.set(playbook.id, playbook);
    },
    delete: async (id: string) => {
      this.playbookRecords.delete(id);
      await this.sessions.deleteForPlaybook(id);
      await this.audioAssets.deleteForPlaybook(id);
      await this.bookmarks.deleteForPlaybook(id);
      await this.timingAttempts.deleteForPlaybook(id);
    }
  };

  readonly sessions = {
    get: async (playbookId: string, roleId: string) => this.sessionRecords.get(`${playbookId}:${roleId}`),
    getLatestForPlaybook: async (playbookId: string) =>
      [...this.sessionRecords.values()]
        .filter((record) => record.playbookId === playbookId)
        .sort((left, right) => right.updatedAt - left.updatedAt)[0],
    save: async (record: RehearsalSession) => {
      this.sessionRecords.set(`${record.playbookId}:${record.roleId}`, record);
    },
    deleteForPlaybook: async (playbookId: string) => {
      deleteWhere(this.sessionRecords, (record) => record.playbookId === playbookId);
    }
  };

  readonly audioAssets = {
    save: async (record: StoredAudioAsset) => {
      this.audioAssetRecords.set(`${record.playbookId}:${record.path}`, record);
    },
    get: async (playbookId: string, path: string) => this.audioAssetRecords.get(`${playbookId}:${path}`),
    deleteForPlaybook: async (playbookId: string) => {
      deleteWhere(this.audioAssetRecords, (record) => record.playbookId === playbookId);
    }
  };

  readonly bookmarks = {
    get: async (playbookId: string, roleId: string, lineId: string) =>
      this.bookmarkRecords.get(`${playbookId}:${roleId}:${lineId}`),
    listForRole: async (playbookId: string, roleId: string) =>
      [...this.bookmarkRecords.values()].filter((record) => record.playbookId === playbookId && record.roleId === roleId),
    save: async (record: Bookmark) => {
      this.bookmarkRecords.set(`${record.playbookId}:${record.roleId}:${record.lineId}`, record);
    },
    delete: async (playbookId: string, roleId: string, lineId: string) => {
      this.bookmarkRecords.delete(`${playbookId}:${roleId}:${lineId}`);
    },
    deleteForPlaybook: async (playbookId: string) => {
      deleteWhere(this.bookmarkRecords, (record) => record.playbookId === playbookId);
    }
  };

  readonly timingAttempts = {
    save: async (record: TimingAttempt) => {
      this.timingAttemptRecords.set(record.id, record);
    },
    latestForLine: async (playbookId: string, roleId: string, lineId: string) =>
      attemptsForLine([...this.timingAttemptRecords.values()], playbookId, roleId, lineId)[0],
    recentForLine: async (playbookId: string, roleId: string, lineId: string, limit = 5) =>
      attemptsForLine([...this.timingAttemptRecords.values()], playbookId, roleId, lineId).slice(0, limit),
    latestForRole: async (playbookId: string, roleId: string) =>
      [...this.timingAttemptRecords.values()]
        .filter((record) => record.playbookId === playbookId && record.roleId === roleId)
        .sort((left, right) => right.createdAt - left.createdAt),
    deleteForPlaybook: async (playbookId: string) => {
      deleteWhere(this.timingAttemptRecords, (record) => record.playbookId === playbookId);
    }
  };
}

function deleteWhere<T>(records: Map<string, T>, predicate: (record: T) => boolean): void {
  for (const [key, record] of records) {
    if (predicate(record)) {
      records.delete(key);
    }
  }
}

function attemptsForLine(
  attempts: TimingAttempt[],
  playbookId: string,
  roleId: string,
  lineId: string
): TimingAttempt[] {
  return attempts
    .filter((record) => record.playbookId === playbookId && record.roleId === roleId && record.lineId === lineId)
    .sort((left, right) => right.createdAt - left.createdAt);
}

function minimalPlaybook(): Playbook {
  return {
    id: "playbook",
    title: "Androcles and the Lion",
    authors: ["George Bernard Shaw"],
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: []
  };
}

function session(playbookId: string, roleId: string, lineIndex: number): RehearsalSession {
  return {
    playbookId,
    roleId,
    lineIndex,
    cueDepth: 1,
    includeDirections: true,
    revealLine: false,
    showLinesByDefault: false,
    cueWindowPresetId: "full",
    playbackRate: 1,
    speakAlongEnabled: false,
    speakAlongPauseMs: 750,
    tempoTargetHesitationMs: 750,
    syncPracticeTiming: true,
    tempoTimingPreferred: false,
    updatedAt: 1000
  };
}

function bookmark(playbookId: string, roleId: string, lineId: string): Bookmark {
  return {
    id: `${playbookId}:${roleId}:${lineId}`,
    playbookId,
    roleId,
    lineId,
    createdAt: 1000
  };
}

function attempt(playbookId: string, roleId: string, lineId: string): TimingAttempt {
  return {
    id: `${playbookId}:${roleId}:${lineId}:attempt`,
    playbookId,
    roleId,
    lineId,
    createdAt: 1000,
    hesitationMs: 750,
    deliveryMs: 1200,
    targetHesitationMs: 750,
    targetDeliveryMs: 1200,
    hesitationLabel: "close",
    deliveryLabel: "close",
    detectionMode: "energy"
  };
}
