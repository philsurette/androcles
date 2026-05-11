import type { Playbook } from "../domain/playbook";
import { audioAssetRepository } from "./audioAssetRepository";
import { db } from "./db";
import { timingAttemptRepository } from "./timingAttemptRepository";

export const playbookRepository = {
  list: () => db.playbooks.toArray(),
  get: (id: string) => db.playbooks.get(id),
  save: (playbook: Playbook) => db.playbooks.put(playbook),
  delete: (id: string) =>
    db.transaction("rw", db.playbooks, db.sessions, db.audioAssets, db.timingAttempts, async () => {
      await audioAssetRepository.deleteForPlaybook(id);
      await timingAttemptRepository.deleteForPlaybook(id);
      await db.sessions.where("playbookId").equals(id).delete();
      await db.playbooks.delete(id);
    })
};
