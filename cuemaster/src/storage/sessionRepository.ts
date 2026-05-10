import type { RehearsalSession } from "../domain/session";
import { db } from "./db";

export const sessionRepository = {
  get: (playbookId: string, roleId: string) => db.sessions.get([playbookId, roleId]),
  save: (session: RehearsalSession) => db.sessions.put(session)
};
