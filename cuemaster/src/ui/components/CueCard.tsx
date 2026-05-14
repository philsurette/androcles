import { useLayoutEffect, useRef, useState } from "react";
import type { Cue } from "../../domain/cue";

export function CueCard({ cue, showSpeaker = true }: { cue: Cue; showSpeaker?: boolean }) {
  const cueTextRef = useRef<HTMLParagraphElement | null>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);

  useLayoutEffect(() => {
    function scrollCueTextToEnd() {
      const cueText = cueTextRef.current;
      if (!cueText) {
        return;
      }
      setIsOverflowing(cueText.scrollWidth > cueText.clientWidth);
      cueText.scrollLeft = cueText.scrollWidth - cueText.clientWidth;
    }

    scrollCueTextToEnd();
    const resizeObserver = new ResizeObserver(scrollCueTextToEnd);
    if (cueTextRef.current) {
      resizeObserver.observe(cueTextRef.current);
    }
    return () => resizeObserver.disconnect();
  }, [cue.text, isOverflowing]);

  return (
    <article className="card cue-card">
      {showSpeaker ? <p className="speaker">{cue.speaker}</p> : null}
      <div className="cue-text-window">
        {isOverflowing ? <span className="cue-overflow-prefix" aria-hidden="true">…</span> : null}
        <p className="cue-text-clip" ref={cueTextRef}>
          {cue.text}
        </p>
      </div>
    </article>
  );
}
