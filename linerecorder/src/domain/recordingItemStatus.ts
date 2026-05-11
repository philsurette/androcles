import type { RecordingItem } from "./recordingItem";

export type RecordingItemStatus = "missing" | "accepted";

export type RecordingItemProgress = {
  item: RecordingItem;
  status: RecordingItemStatus;
};

export function recordingItemProgress(
  items: RecordingItem[],
  acceptedSegmentIds: Set<string>
): RecordingItemProgress[] {
  return items.map((item) => ({
    item,
    status: acceptedSegmentIds.has(item.segmentId) ? "accepted" : "missing"
  }));
}
