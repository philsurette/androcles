import type { RecordingPack } from "../domain/recordingPack";
import { db, type RecordingProjectRecord } from "./db";

export class ProjectRepository {
  async saveImportedPack(pack: RecordingPack): Promise<RecordingProjectRecord> {
    const project: RecordingProjectRecord = {
      id: `${pack.play.id}:${pack.role.id}`,
      importedAt: new Date().toISOString(),
      currentSegmentId: pack.items[0]?.segmentId,
      pack
    };
    await db.projects.put(project);
    return project;
  }

  async list(): Promise<RecordingProjectRecord[]> {
    return db.projects.orderBy("importedAt").reverse().toArray();
  }

  async get(id: string): Promise<RecordingProjectRecord | undefined> {
    return db.projects.get(id);
  }
}

export const projectRepository = new ProjectRepository();
