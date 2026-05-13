export type ContextKind = "heading" | "description" | "direction" | "blocking";

export type ContextBlock = {
  id: string;
  partId: number | null;
  blockId: string;
  kind: ContextKind;
  speaker: "_NARRATOR";
  text: string;
  contentHash: string;
  audioPath?: string;
  durationMs?: number;
  targets?: string[];
};
