export type ContextKind = "heading" | "description" | "direction";

export type ContextBlock = {
  id: string;
  partId: number | null;
  blockId: string;
  kind: ContextKind;
  speaker: "_NARRATOR";
  text: string;
  audioPath: string;
  durationMs: number;
};
