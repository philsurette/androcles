import type { Line } from "../domain/line";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";
import { cueWindowPresetForId } from "./cueWindowPreset";

export type RehearsalState = {
  playbook: Playbook;
  role: Role;
  lines: Line[];
  index: number;
  includeDirections: boolean;
};

export class RehearsalEngine {
  constructor(private readonly state: RehearsalState) {}

  static forRole(
    playbook: Playbook,
    roleId: string,
    options: { startLineId?: string; includeDirections?: boolean } = {}
  ): RehearsalEngine {
    const role = playbook.roles.find((candidate) => candidate.id === roleId);
    if (!role) {
      throw new Error(`Role not found: ${roleId}`);
    }
    const startIndex = options.startLineId ? role.lines.findIndex((line) => line.id === options.startLineId) : 0;
    if (options.startLineId && startIndex < 0) {
      throw new Error(`Line not found for role ${roleId}: ${options.startLineId}`);
    }
    return new RehearsalEngine({
      playbook,
      role,
      lines: role.lines,
      index: startIndex < 0 ? 0 : startIndex,
      includeDirections: options.includeDirections ?? true
    });
  }

  currentLine(): Line | null {
    return this.state.lines[this.state.index] ?? null;
  }

  selectedRole(): Role {
    return this.state.role;
  }

  position() {
    return {
      index: this.state.index,
      total: this.state.lines.length,
      atBeginning: this.state.index <= 0,
      atEnd: this.state.index >= Math.max(this.state.lines.length - 1, 0)
    };
  }

  next(): Line | null {
    this.state.index = Math.min(this.state.index + 1, Math.max(this.state.lines.length - 1, 0));
    return this.currentLine();
  }

  previous(): Line | null {
    this.state.index = Math.max(this.state.index - 1, 0);
    return this.currentLine();
  }

  cuePayloads(cueWindowPresetId = "full"): Array<Line["cue"]> {
    const preset = cueWindowPresetForId(cueWindowPresetId);
    if (preset.windowMs === 0) {
      return [];
    }
    if (preset.windowMs === null) {
      const line = this.currentLine();
      return line ? [line.cue] : [];
    }
    if (preset.id === "last_2s") {
      const line = this.currentLine();
      return line ? [line.cue] : [];
    }

    const cues: Array<Line["cue"]> = [];
    let durationMs = 0;

    for (let index = this.state.index; index >= 0; index -= 1) {
      const cue = this.state.lines[index].cue;
      cues.unshift(cue);
      durationMs += cue.durationMs;
      if (durationMs >= preset.windowMs) {
        break;
      }
    }

    return cues;
  }

  includeDirections(): boolean {
    return this.state.includeDirections;
  }

  setIncludeDirections(includeDirections: boolean): void {
    this.state.includeDirections = includeDirections;
  }
}
