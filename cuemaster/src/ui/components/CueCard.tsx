import type { Cue } from "../../domain/cue";

export function CueCard({ cue }: { cue: Cue }) {
  return (
    <article className="card cue-card">
      <p className="speaker">{cue.speaker}</p>
      <p>{cue.text}</p>
    </article>
  );
}
