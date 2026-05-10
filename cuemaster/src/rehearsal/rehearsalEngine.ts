import type { Line } from "../domain/line";

export type RehearsalState = {
  lines: Line[];
  index: number;
};

export class RehearsalEngine {
  constructor(private readonly state: RehearsalState) {}

  currentLine(): Line | null {
    return this.state.lines[this.state.index] ?? null;
  }
}
