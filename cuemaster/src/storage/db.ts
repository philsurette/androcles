import Dexie, { type Table } from "dexie";
import type { Playbook } from "../domain/playbook";
import type { RehearsalSession } from "../domain/session";

export class CuemasterDb extends Dexie {
  playbooks!: Table<Playbook, string>;
  sessions!: Table<RehearsalSession, [string, string]>;

  constructor() {
    super("cuemaster");
    this.version(1).stores({
      playbooks: "id,title",
      sessions: "[playbookId+roleId],playbookId,roleId"
    });
  }
}

export const db = new CuemasterDb();
