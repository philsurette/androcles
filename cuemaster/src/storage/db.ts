import Dexie, { type Table } from "dexie";
import type { Bookmark } from "../domain/bookmark";
import type { Playbook } from "../domain/playbook";
import type { RehearsalSession } from "../domain/session";
import type { TimingAttempt } from "../domain/timingAttempt";
import type { StoredAudioAsset } from "./audioAssetRepository";
import type { StoredJsonAsset } from "./jsonAssetRepository";

export class CuemasterDb extends Dexie {
  playbooks!: Table<Playbook, string>;
  sessions!: Table<RehearsalSession, [string, string]>;
  audioAssets!: Table<StoredAudioAsset, [string, string]>;
  jsonAssets!: Table<StoredJsonAsset, [string, string]>;
  timingAttempts!: Table<TimingAttempt, string>;
  bookmarks!: Table<Bookmark, [string, string, string]>;

  constructor() {
    super("cuemaster");
    this.version(1).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId"
    });
    this.version(2).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId",
      audioAssets: "[playbookId+path],playbookId,path"
    });
    this.version(3)
      .stores({
        playbooks: "id,title",
        sessions: "[playbookId+roleId],playbookId,roleId",
        audioAssets: "[playbookId+path],playbookId,path"
      })
      .upgrade(async (transaction) => {
        await transaction.table("playbooks").clear();
        await transaction.table("sessions").clear();
        await transaction.table("audioAssets").clear();
      });
    this.version(4).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId",
      audioAssets: "[playbookId+path],playbookId,path",
      timingAttempts: "id,playbookId,roleId,lineId,[playbookId+roleId+lineId],createdAt"
    });
    this.version(5).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId",
      audioAssets: "[playbookId+path],playbookId,path",
      timingAttempts: "id,playbookId,roleId,lineId,[playbookId+roleId+lineId],createdAt",
      bookmarks: "[playbookId+roleId+lineId],playbookId,roleId,lineId"
    });
    this.version(6).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId",
      audioAssets: "[playbookId+path],playbookId,path",
      jsonAssets: "[playbookId+path],playbookId,path",
      timingAttempts: "id,playbookId,roleId,lineId,[playbookId+roleId+lineId],createdAt",
      bookmarks: "[playbookId+roleId+lineId],playbookId,roleId,lineId"
    });
  }
}

export const db = new CuemasterDb();
