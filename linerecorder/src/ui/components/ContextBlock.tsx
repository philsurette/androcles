import { useLayoutEffect, useRef, useState } from "react";

type ContextBlockProps = {
  label: string;
  speaker?: string;
  text?: string;
  labelPosition?: "inline" | "border";
};

export function ContextBlock({ label, speaker, text, labelPosition = "inline" }: ContextBlockProps) {
  const textRef = useRef<HTMLParagraphElement | null>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const cropFromStart = label !== "Next";

  useLayoutEffect(() => {
    function positionText() {
      const textElement = textRef.current;
      if (!textElement) {
        return;
      }
      setIsOverflowing(textElement.scrollWidth > textElement.clientWidth);
      textElement.scrollLeft = cropFromStart ? textElement.scrollWidth - textElement.clientWidth : 0;
    }

    positionText();
    const resizeObserver = new ResizeObserver(positionText);
    if (textRef.current) {
      resizeObserver.observe(textRef.current);
    }
    return () => resizeObserver.disconnect();
  }, [text, isOverflowing, cropFromStart]);

  if (!text) {
    return null;
  }
  const contentId = `context-${label.toLowerCase().replace(/\s+/g, "-")}-${speaker ?? "text"}`;
  const isBorderLabel = labelPosition === "border";

  return (
    <section className={isExpanded ? `context-panel expanded ${isBorderLabel ? "context-panel--border-label" : ""}`.trim() : `context-panel${isBorderLabel ? " context-panel--border-label" : ""}`}>
      {isBorderLabel ? <span className="context-border-label">{label}</span> : null}
      <button
        type="button"
        className="context-toggle"
        aria-expanded={isExpanded}
        aria-controls={contentId}
        title={isExpanded ? `Collapse ${label.toLowerCase()}` : `Expand ${label.toLowerCase()}`}
        onClick={() => setIsExpanded((current) => !current)}
      >
        <span className={isBorderLabel ? "visually-hidden" : "context-label"}>{label}</span>
        {speaker ? <span className="context-speaker">{speaker}</span> : null}
        <span className={cropFromStart ? "context-text-window" : "context-text-window crop-end"}>
          {isOverflowing && !isExpanded && cropFromStart ? (
            <span className="context-overflow-prefix" aria-hidden="true">…</span>
          ) : null}
          <p className="context-text-clip" id={contentId} ref={textRef}>
            {text}
          </p>
        </span>
        <span className="context-disclosure" aria-hidden="true" />
      </button>
      {isExpanded ? (
        <p className="context-expanded-text" aria-hidden="true">
          {text}
        </p>
      ) : null}
    </section>
  );
}
