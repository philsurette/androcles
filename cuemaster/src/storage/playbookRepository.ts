import type { Playbook } from "../domain/playbook";
import { db } from "./db";

export const playbookRepository = {
  list: () => db.playbooks.toArray(),
  get: (id: string) => db.playbooks.get(id),
  save: (playbook: Playbook) => db.playbooks.put(playbook),
  delete: (id: string) =>
    db.transaction("rw", db.playbooks, db.sessions, async () => {
      await db.sessions.where("playbookId").equals(id).delete();
      await db.playbooks.delete(id);
    })
};
