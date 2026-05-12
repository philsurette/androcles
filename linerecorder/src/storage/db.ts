import Dexie, { type Table } from "dexie";
import type { FloorNoiseRecording } from "../domain/floorNoiseRecording";
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
  floorNoiseRecordings!: Table<FloorNoiseRecording, string>;

  constructor() {
    super("linerecorder");
    this.version(1).stores({
      projects: "id, importedAt, request.play.id, request.role.id",
      takes: "id, projectId, segmentId, status, recordedAt, [projectId+segmentId]"
    });
    this.version(2).stores({
      projects: "id, importedAt, request.play.id, request.role.id",
      takes: "id, projectId, segmentId, status, recordedAt, [projectId+segmentId]",
      floorNoiseRecordings: "id, projectId, recordedAt, [projectId+recordedAt]"
    });
  }
}

export const db = new LineRecorderDb();
