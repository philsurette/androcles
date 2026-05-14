import { useLayoutEffect, useRef, useState } from "react";
import type { Cue } from "../../domain/cue";

export function CueCard({ cue, showSpeaker = true }: { cue: Cue; showSpeaker?: boolean }) {
  const cueTextRef = useRef<HTMLParagraphElement | null>(null);
  const cueWindowRef = useRef<HTMLDivElement | null>(null);
  const [displayedCueText, setDisplayedCueText] = useState(cue.text);
  const [isOverflowing, setIsOverflowing] = useState(false);

  function trimToTailText(fullText: string, pixelWidth: number, font: string): string {
    if (fullText.length <= 1 || pixelWidth <= 0) {
      return fullText;
    }

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) {
      return fullText;
    }
    context.font = font;

    const measure = (text: string) => context.measureText(text).width;
    if (measure(fullText) <= pixelWidth) {
      return fullText;
    }

    let low = 1;
    let high = fullText.length;
    let best = 1;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const rawTail = fullText.slice(-mid);
      const tail = `…${rawTail.replace(/^[\s.,;:!?-]+/, "")}`;
      if (measure(tail) <= pixelWidth) {
        best = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    const finalRawTail = fullText.slice(-best).replace(/^[\s.,;:!?-]+/, "");
    const finalText = best === fullText.length ? fullText : finalRawTail;
    return finalText;
  }

  useLayoutEffect(() => {
    const windowElement = cueWindowRef.current;
    const textElement = cueTextRef.current;
    if (!windowElement || !textElement) {
      setDisplayedCueText(cue.text);
      setIsOverflowing(false);
      return;
    }

    const updateText = () => {
      const maxWidth = windowElement.clientWidth;
      if (maxWidth <= 0) {
        return;
      }
      const style = getComputedStyle(textElement);
      const nextText = trimToTailText(cue.text, maxWidth, style.font);
      const overflow = nextText !== cue.text;
      setIsOverflowing(overflow);
      setDisplayedCueText(nextText);
    };

    updateText();
    const resizeObserver = new ResizeObserver(updateText);
    resizeObserver.observe(windowElement);
    return () => resizeObserver.disconnect();
  }, [cue.text]);

  return (
    <article className="card cue-card">
      {showSpeaker ? <p className="speaker">{cue.speaker}</p> : null}
      {!showSpeaker ? <span className="cue-speaker-placeholder" aria-hidden="true" /> : null}
      <div className="cue-text-window" ref={cueWindowRef}>
        {isOverflowing ? <span className="cue-overflow-prefix" aria-hidden="true">…</span> : null}
        <p className="cue-text-clip" ref={cueTextRef}>
          {displayedCueText}
        </p>
      </div>
    </article>
  );
}
