import type { RehearsalSession } from "../domain/session";
import { db } from "./db";

export const sessionRepository = {
  get: (playbookId: string, roleId: string) => db.sessions.get([playbookId, roleId]),
  async getLatestForPlaybook(playbookId: string) {
    const sessions = await db.sessions.where("playbookId").equals(playbookId).toArray();
    return sessions.sort((left, right) => right.updatedAt - left.updatedAt)[0];
  },
  save: (session: RehearsalSession) => db.sessions.put(session),
  deleteForPlaybook: (playbookId: string) => db.sessions.where("playbookId").equals(playbookId).delete()
};
