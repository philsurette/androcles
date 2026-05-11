export type CueWindowPresetId = "none" | "full" | "last_2s" | "last_5s" | "last_10s" | "last_15s" | "last_20s";

export type CueWindowPreset = {
  id: CueWindowPresetId;
  label: string;
  windowMs: number | null;
};

export const cueWindowPresets: CueWindowPreset[] = [
  { id: "none", label: "No cue", windowMs: 0 },
  { id: "full", label: "Full cue", windowMs: null },
  { id: "last_2s", label: "Last 2s", windowMs: 2000 },
  { id: "last_5s", label: "Last 5s", windowMs: 5000 },
  { id: "last_10s", label: "Last 10s", windowMs: 10000 },
  { id: "last_15s", label: "Last 15s", windowMs: 15000 },
  { id: "last_20s", label: "Last 20s", windowMs: 20000 }
];

export const defaultCueWindowPresetId: CueWindowPresetId = "full";

export function cueWindowPresetForId(id: string | undefined): CueWindowPreset {
  return (
    cueWindowPresets.find((preset) => preset.id === id) ??
    cueWindowPresets.find((preset) => preset.id === defaultCueWindowPresetId) ??
    cueWindowPresets[0]
  );
}

export function timedCueWindowMsAtLeast(durationMs: number): number | null {
  return (
    cueWindowPresets
      .map((preset) => preset.windowMs)
      .filter((windowMs): windowMs is number => windowMs !== null)
      .filter((windowMs) => windowMs > 0)
      .find((windowMs) => windowMs >= durationMs) ?? null
  );
}
