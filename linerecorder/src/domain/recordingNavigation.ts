import type { RecordingItemProgress } from "./recordingItemStatus";

export function selectedProgressIndex(progress: RecordingItemProgress[], itemId: string | undefined): number {
  if (progress.length === 0) {
    return -1;
  }
  if (itemId === undefined) {
    return 0;
  }
  const index = progress.findIndex((candidate) => candidate.item.id === itemId);
  return index === -1 ? 0 : index;
}

export function previousProgress(progress: RecordingItemProgress[], selectedIndex: number): RecordingItemProgress | undefined {
  if (selectedIndex <= 0) {
    return undefined;
  }
  return progress[selectedIndex - 1];
}

export function nextProgress(progress: RecordingItemProgress[], selectedIndex: number): RecordingItemProgress | undefined {
  if (selectedIndex < 0 || selectedIndex >= progress.length - 1) {
    return undefined;
  }
  return progress[selectedIndex + 1];
}
