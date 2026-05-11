import type { Line } from "../../domain/line";

export function LineCard({ line, includeDirections = false }: { line: Line; includeDirections?: boolean }) {
  return (
    <article className="card line-card">
      <p className="speaker">{line.speaker}</p>
      <p>
        {includeDirections
          ? line.directions.map((direction) => (
              <span className="inline-stage-direction" key={`${direction.segmentId}-${direction.placement}`}>
                {direction.text}
              </span>
            ))
          : null}
        {line.responseText}
      </p>
    </article>
  );
}
