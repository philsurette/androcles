import type { Playbook } from "../domain/playbook";
import { db } from "./db";

export const playbookRepository = {
  list: () => db.playbooks.toArray(),
  get: (id: string) => db.playbooks.get(id),
  save: (playbook: Playbook) => db.playbooks.put(playbook),
  delete: (id: string) => db.playbooks.delete(id)
};
