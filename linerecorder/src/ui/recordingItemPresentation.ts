import type { MicrophoneReading } from "../audio/microphoneSession";
import type { RecordedWav } from "../audio/wavRecorder";
import type { RecordingItem } from "../domain/recordingItem";

export function recordingItemSearchText(item: RecordingItem): string {
  return [
    item.id,
    item.lineId,
    item.displayText,
    item.segmentText,
    item.cueSpeaker,
    item.cueText,
    item.previousSpeaker,
    item.previousText,
    item.nextSpeaker,
    item.nextText,
    item.sectionTitle,
    item.sceneHeading,
    item.reason,
    item.notes,
    ...item.stageDirections,
    ...item.blocking.map((blocking) => `${blocking.targets.join(" ")} ${blocking.text}`)
  ]
    .filter(Boolean)
    .join(" ");
}

export function requestKindLabel(kind: string): string {
  return kind
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function reasonLabel(reason: string | undefined): string {
  return (reason ?? "recording").replace(/_/g, " ");
}

export function levelLabel(level: MicrophoneReading["level"]): string {
  switch (level) {
    case "no-signal":
      return "No signal";
    case "too-quiet":
      return "Too quiet";
    case "good":
      return "Good";
    case "clipping":
      return "Clipping";
  }
}

export function levelStatus(level: MicrophoneReading["level"]): string {
  switch (level) {
    case "no-signal":
      return "No microphone signal detected.";
    case "too-quiet":
      return "Input is too quiet.";
    case "good":
      return "Microphone level looks good.";
    case "clipping":
      return "Input is clipping. Move back or reduce gain.";
  }
}

export function recordingInputQuality(recording: RecordedWav) {
  return {
    peakEnergy: recording.inputQuality.peakEnergy,
    levelCounts: {
      noSignal: recording.inputQuality.levelCounts["no-signal"],
      tooQuiet: recording.inputQuality.levelCounts["too-quiet"],
      good: recording.inputQuality.levelCounts.good,
      clipping: recording.inputQuality.levelCounts.clipping
    }
  };
}

export function isUsableFloorNoise(recording: RecordedWav): boolean {
  const levelCounts = recording.inputQuality.levelCounts;
  const total = Object.values(levelCounts).reduce((sum, count) => sum + count, 0);
  if (total === 0 || levelCounts.clipping > 0) {
    return false;
  }
  return levelCounts.good / total < 0.25;
}

export function sameContext(
  firstSpeaker: string | undefined,
  firstText: string | undefined,
  secondSpeaker: string | undefined,
  secondText: string | undefined
): boolean {
  if (!firstText || !secondText) {
    return false;
  }
  return firstSpeaker === secondSpeaker && firstText.trim() === secondText.trim();
}
