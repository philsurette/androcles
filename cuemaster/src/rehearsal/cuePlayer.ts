import type { Cue } from "../domain/cue";

export class CuePlayer {
  async play(_cue: Cue): Promise<void> {
    throw new Error("CuePlayer.play is not implemented");
  }
}
