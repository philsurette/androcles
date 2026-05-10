import type { ResponseSegment } from "../domain/line";

export class ResponsePlayer {
  async play(_segments: ResponseSegment[]): Promise<void> {
    throw new Error("ResponsePlayer.play is not implemented");
  }
}
