import type { TimingAttempt } from "../domain/timingAttempt";
import { db } from "./db";

const maxAttemptsPerLine = 20;

export const timingAttemptRepository = {
  async save(attempt: TimingAttempt): Promise<void> {
    await db.timingAttempts.put(attempt);
    await trimAttemptsForLine(attempt.playbookId, attempt.roleId, attempt.lineId);
  },

  async latestForLine(playbookId: string, roleId: string, lineId: string): Promise<TimingAttempt | undefined> {
    const attempts = await attemptsForLine(playbookId, roleId, lineId);
    return attempts[0];
  },

  deleteForPlaybook: (playbookId: string) => db.timingAttempts.where("playbookId").equals(playbookId).delete()
};

async function trimAttemptsForLine(playbookId: string, roleId: string, lineId: string): Promise<void> {
  const attempts = await attemptsForLine(playbookId, roleId, lineId);
  const staleAttempts = attempts.slice(maxAttemptsPerLine);
  await Promise.all(staleAttempts.map((attempt) => db.timingAttempts.delete(attempt.id)));
}

async function attemptsForLine(playbookId: string, roleId: string, lineId: string): Promise<TimingAttempt[]> {
  const attempts = await db.timingAttempts
    .where("[playbookId+roleId+lineId]")
    .equals([playbookId, roleId, lineId])
    .toArray();
  return attempts.sort((left, right) => right.createdAt - left.createdAt);
}
