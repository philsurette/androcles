import type { Cue } from "../../domain/cue";

export function CueCard({ cue }: { cue: Cue }) {
  return (
    <article className="card cue-card">
      <p className="speaker">{cue.speaker}</p>
      <p>{leftTruncatedCueText(cue.text)}</p>
    </article>
  );
}

function leftTruncatedCueText(text: string): string {
  const maxCueCharacters = 110;
  if (text.length <= maxCueCharacters) {
    return text;
  }
  return `…${text.slice(-maxCueCharacters).replace(/^[\s.,;:!?-]+/, "")}`;
}
