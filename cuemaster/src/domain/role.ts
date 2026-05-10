import type { Line } from "./line";

export type Role = {
  id: string;
  displayName: string;
  reader: string;
  parts: Array<number | null>;
  lines: Line[];
};
