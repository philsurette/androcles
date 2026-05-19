import type { BlockingNote, Line } from "../../domain/line";

export type BlockingScope = "role" | "all";

export function LineCard({
  line,
  includeDirections = false,
  includeBlocking = true,
  blockingScope = "role",
  hasBlockingDiagram,
  onOpenBlockingDiagram
}: {
  line: Line;
  includeDirections?: boolean;
  includeBlocking?: boolean;
  blockingScope?: BlockingScope;
  hasBlockingDiagram?: (blocking: BlockingNote) => boolean;
  onOpenBlockingDiagram?: (blocking: BlockingNote) => void;
}) {
  const visibleBlocking =
    includeBlocking && line.blocking
      ? line.blocking.filter(
          (blocking) =>
            (blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role))
        )
      : [];
  const leadingBlocking = visibleBlocking.filter((blocking) => blocking.placement !== "after");
  const trailingBlocking = visibleBlocking.filter((blocking) => blocking.placement === "after");

  return (
    <article className="card line-card">
      {leadingBlocking.map((blocking) => (
        <BlockingNoteView
          blocking={blocking}
          canOpen={Boolean(hasBlockingDiagram?.(blocking) && onOpenBlockingDiagram)}
          key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}
          onOpen={onOpenBlockingDiagram}
        />
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
      {trailingBlocking.map((blocking) => (
        <BlockingNoteView
          blocking={blocking}
          canOpen={Boolean(hasBlockingDiagram?.(blocking) && onOpenBlockingDiagram)}
          key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}
          onOpen={onOpenBlockingDiagram}
        />
      ))}
    </article>
  );
}

function BlockingNoteView({
  blocking,
  canOpen,
  onOpen
}: {
  blocking: BlockingNote;
  canOpen: boolean;
  onOpen?: (blocking: BlockingNote) => void;
}) {
  const content = (
    <>
      <span className="blocking-target">{blocking.targets.join(", ")}</span>
      <span className="blocking-text">({blocking.text})</span>
    </>
  );
  return canOpen ? (
    <button
      type="button"
      className="blocking-note blocking-note-button"
      title="Open blocking diagram"
      onClick={() => onOpen?.(blocking)}
    >
      {content}
      <span className="blocking-diagram-affordance" aria-hidden="true">
        ⧉
      </span>
    </button>
  ) : (
    <p className="blocking-note">{content}</p>
  );
}
