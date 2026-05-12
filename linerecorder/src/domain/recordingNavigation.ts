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
  for (let index = selectedIndex - 1; index >= 0; index -= 1) {
    if (progress[index].status === "missing") {
      return progress[index];
    }
  }
  return undefined;
}

export function nextProgress(progress: RecordingItemProgress[], selectedIndex: number): RecordingItemProgress | undefined {
  for (let index = selectedIndex + 1; index < progress.length; index += 1) {
    if (progress[index].status === "missing") {
      return progress[index];
    }
  }
  return undefined;
}
