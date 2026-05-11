export const rehearsalCommands = [
  "next",
  "back",
  "repeat-cue",
  "hear-line",
  "pause",
  "resume",
  "stop",
  "bookmark",
  "start-timing"
] as const;

export type RehearsalCommand = (typeof rehearsalCommands)[number];

export type RehearsalShortcut = RehearsalCommand | "toggle-playback";
