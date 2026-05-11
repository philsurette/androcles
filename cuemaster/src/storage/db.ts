import Dexie, { type Table } from "dexie";
import type { Playbook } from "../domain/playbook";
import type { RehearsalSession } from "../domain/session";
import type { StoredAudioAsset } from "./audioAssetRepository";

export class CuemasterDb extends Dexie {
  playbooks!: Table<Playbook, string>;
  sessions!: Table<RehearsalSession, [string, string]>;
  audioAssets!: Table<StoredAudioAsset, [string, string]>;

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
  }
}

export const db = new CuemasterDb();
