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
          (blocking) =>
            blocking.placement === "inline" &&
            (blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role))
        )
      : [];

  return (
    <article className="card line-card">
      {visibleBlocking.map((blocking) => (
        <p className="blocking-note" key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}>
          <span className="blocking-target">{blocking.targets.join(", ")}</span>
          <span className="blocking-text">({blocking.text})</span>
        </p>
      ))}
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
