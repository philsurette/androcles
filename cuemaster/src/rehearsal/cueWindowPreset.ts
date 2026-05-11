export type CueWindowPresetId = "full" | "last_5s" | "last_10s" | "last_15s" | "last_20s";

export type CueWindowPreset = {
  id: CueWindowPresetId;
  label: string;
  windowMs: number | null;
};

export const cueWindowPresets: CueWindowPreset[] = [
  { id: "full", label: "Full cue", windowMs: null },
  { id: "last_5s", label: "Last 5s", windowMs: 5000 },
  { id: "last_10s", label: "Last 10s", windowMs: 10000 },
  { id: "last_15s", label: "Last 15s", windowMs: 15000 },
  { id: "last_20s", label: "Last 20s", windowMs: 20000 }
];

export const defaultCueWindowPresetId: CueWindowPresetId = "full";

export function cueWindowPresetForId(id: string | undefined): CueWindowPreset {
  return cueWindowPresets.find((preset) => preset.id === id) ?? cueWindowPresets[0];
}

