import type { FloorNoiseRecording } from "../domain/floorNoiseRecording";
import { db } from "./db";

export class FloorNoiseRepository {
  async save(recording: FloorNoiseRecording): Promise<void> {
    await db.floorNoiseRecordings.put(recording);
  }

  async forProject(projectId: string): Promise<FloorNoiseRecording[]> {
    const recordings = await db.floorNoiseRecordings.where("projectId").equals(projectId).toArray();
    return recordings.sort((a, b) => a.recordedAt.localeCompare(b.recordedAt));
  }
}

export const floorNoiseRepository = new FloorNoiseRepository();
