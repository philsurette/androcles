import Dexie, { type Table } from "dexie";
import type { RecordingRequest } from "../domain/recordingRequest";
import type { RecordingTake } from "../domain/take";

export type RecordingProjectRecord = {
  id: string;
  importedAt: string;
  currentItemId?: string;
  request: RecordingRequest;
};

export class LineRecorderDb extends Dexie {
  projects!: Table<RecordingProjectRecord, string>;
  takes!: Table<RecordingTake, string>;

  constructor() {
    super("linerecorder");
    this.version(1).stores({
      projects: "id, importedAt, request.play.id, request.role.id",
      takes: "id, projectId, segmentId, status, recordedAt, [projectId+segmentId]"
    });
  }
}

export const db = new LineRecorderDb();
