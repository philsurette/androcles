import type { Line } from "../../domain/line";

export type BlockingScope = "role" | "all";

export function LineCard({
  line,
  includeDirections = false,
  includeBlocking = true,
  blockingScope = "role"
}: {
  line: Line;
  includeDirections?: boolean;
  includeBlocking?: boolean;
  blockingScope?: BlockingScope;
}) {
  const visibleBlocking =
    includeBlocking && line.blocking
      ? line.blocking.filter(
          (blocking) => blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role)
        )
      : [];

  return (
    <article className="card line-card">
      <p>
        <span className="speaker inline-speaker">{line.speaker}</span>
        {includeDirections
          ? line.directions.map((direction) => (
              <span className="inline-stage-direction" key={`${direction.segmentId}-${direction.placement}`}>
                {direction.text}
              </span>
            ))
          : null}
        {visibleBlocking.map((blocking) => (
          <span className="inline-stage-direction" key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}>
            {blocking.targets.join(", ")}: {blocking.text}
          </span>
        ))}
        {line.responseText}
      </p>
    </article>
  );
}
