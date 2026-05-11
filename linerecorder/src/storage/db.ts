import Dexie, { type Table } from "dexie";
import type { RecordingPack } from "../domain/recordingPack";
import type { RecordingTake } from "../domain/take";

export type RecordingProjectRecord = {
  id: string;
  importedAt: string;
  currentSegmentId?: string;
  pack: RecordingPack;
};

export class LineRecorderDb extends Dexie {
  projects!: Table<RecordingProjectRecord, string>;
  takes!: Table<RecordingTake, string>;

  constructor() {
    super("linerecorder");
    this.version(1).stores({
      projects: "id, importedAt, pack.play.id, pack.role.id",
      takes: "id, projectId, segmentId, status, recordedAt, [projectId+segmentId]"
    });
  }
}

export const db = new LineRecorderDb();
