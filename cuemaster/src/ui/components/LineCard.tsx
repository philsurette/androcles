import type { Line } from "../../domain/line";

export function LineCard({ line }: { line: Line }) {
  return (
    <article className="card line-card">
      <p className="speaker">{line.speaker}</p>
      <p>{line.responseText}</p>
    </article>
  );
}
