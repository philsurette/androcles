import type { RecordingRequest } from "../domain/recordingRequest";
import { db, type RecordingProjectRecord } from "./db";

export class ProjectRepository {
  async saveImportedRequest(request: RecordingRequest): Promise<RecordingProjectRecord> {
    const project: RecordingProjectRecord = {
      id: request.request.id,
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

  async setCurrentSegment(projectId: string, segmentId: string): Promise<void> {
    await db.projects.update(projectId, { currentSegmentId: segmentId });
  }

  async delete(projectId: string): Promise<void> {
    await db.transaction("rw", db.projects, db.takes, async () => {
      await db.takes.where("projectId").equals(projectId).delete();
      await db.projects.delete(projectId);
    });
  }
}

export const projectRepository = new ProjectRepository();
