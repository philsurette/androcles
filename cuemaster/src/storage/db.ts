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
  }
}

export const db = new CuemasterDb();
