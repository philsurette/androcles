import type { Cue } from "../../domain/cue";

export function CueCard({ cue }: { cue: Cue }) {
  return <article className="card">{cue.text}</article>;
}
