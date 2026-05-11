import type { RecordingRequest } from "../domain/recordingRequest";
import { db, type RecordingProjectRecord } from "./db";

export class ProjectRepository {
  async saveImportedRequest(request: RecordingRequest): Promise<RecordingProjectRecord> {
    const project: RecordingProjectRecord = {
      id: `${request.play.id}:${request.role.id}`,
      importedAt: new Date().toISOString(),
      currentSegmentId: request.items[0]?.segmentId,
      request
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
