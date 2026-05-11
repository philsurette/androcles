import type { RecordingTake } from "../domain/take";
import { db } from "./db";

export class TakeRepository {
  async saveAccepted(take: RecordingTake): Promise<void> {
    const previousAccepted = await db.takes
      .where("[projectId+segmentId]")
      .equals([take.projectId, take.segmentId])
      .and((candidate) => candidate.status === "accepted")
      .toArray();

    await db.transaction("rw", db.takes, async () => {
      for (const previous of previousAccepted) {
        await db.takes.put({ ...previous, status: "replaced" });
      }
      await db.takes.put({ ...take, status: "accepted" });
    });
  }

  async acceptedForProject(projectId: string): Promise<RecordingTake[]> {
    return db.takes.where("projectId").equals(projectId).and(isAccepted).toArray();
  }
}

function isAccepted(take: RecordingTake): boolean {
  return take.status === "accepted";
}

export const takeRepository = new TakeRepository();
