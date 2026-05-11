import type { Line } from "../domain/line";
import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";

export type RehearsalState = {
  playbook: Playbook;
  role: Role;
  lines: Line[];
  index: number;
  cueDepth: number;
  includeDirections: boolean;
};

export class RehearsalEngine {
  constructor(private readonly state: RehearsalState) {}

  static forRole(
    playbook: Playbook,
    roleId: string,
    options: { startLineId?: string; cueDepth?: number; includeDirections?: boolean } = {}
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
      cueDepth: options.cueDepth ?? 1,
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

  cuePayloads(): Array<Line["cue"]> {
    const start = Math.max(this.state.index - this.state.cueDepth + 1, 0);
    return this.state.lines.slice(start, this.state.index + 1).map((line) => line.cue);
  }

  cueDepth(): number {
    return this.state.cueDepth;
  }

  setCueDepth(cueDepth: number): void {
    this.state.cueDepth = cueDepth;
  }

  includeDirections(): boolean {
    return this.state.includeDirections;
  }
}
