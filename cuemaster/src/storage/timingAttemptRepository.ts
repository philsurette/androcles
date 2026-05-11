import type { TimingAttempt } from "../domain/timingAttempt";
import { db } from "./db";
import Dexie from "dexie";
import type { TimingAttemptRepository } from "./storage";

const maxAttemptsPerLine = 20;

export const timingAttemptRepository: TimingAttemptRepository = {
  async save(attempt: TimingAttempt): Promise<void> {
    await db.timingAttempts.put(attempt);
    await trimAttemptsForLine(attempt.playbookId, attempt.roleId, attempt.lineId);
  },

  async latestForLine(playbookId: string, roleId: string, lineId: string): Promise<TimingAttempt | undefined> {
    const attempts = await attemptsForLine(playbookId, roleId, lineId);
    return attempts[0];
  },

  recentForLine(playbookId: string, roleId: string, lineId: string, limit = 5): Promise<TimingAttempt[]> {
    return attemptsForLine(playbookId, roleId, lineId, limit);
  },

  async latestForRole(playbookId: string, roleId: string): Promise<TimingAttempt[]> {
    const attempts = await db.timingAttempts
      .where("[playbookId+roleId+lineId]")
      .between([playbookId, roleId, Dexie.minKey], [playbookId, roleId, Dexie.maxKey])
      .toArray();
    const latestByLine = new Map<string, TimingAttempt>();
    for (const attempt of attempts.sort((left, right) => right.createdAt - left.createdAt)) {
      if (!latestByLine.has(attempt.lineId)) {
        latestByLine.set(attempt.lineId, attempt);
      }
    }
    return Array.from(latestByLine.values()).sort((left, right) => right.createdAt - left.createdAt);
  },

  deleteForPlaybook: (playbookId: string) => db.timingAttempts.where("playbookId").equals(playbookId).delete()
};

async function trimAttemptsForLine(playbookId: string, roleId: string, lineId: string): Promise<void> {
  const attempts = await attemptsForLine(playbookId, roleId, lineId);
  const staleAttempts = attempts.slice(maxAttemptsPerLine);
  await Promise.all(staleAttempts.map((attempt) => db.timingAttempts.delete(attempt.id)));
}

async function attemptsForLine(
  playbookId: string,
  roleId: string,
  lineId: string,
  limit?: number
): Promise<TimingAttempt[]> {
  const attempts = await db.timingAttempts
    .where("[playbookId+roleId+lineId]")
    .equals([playbookId, roleId, lineId])
    .toArray();
  const sortedAttempts = attempts.sort((left, right) => right.createdAt - left.createdAt);
  return limit === undefined ? sortedAttempts : sortedAttempts.slice(0, limit);
}
