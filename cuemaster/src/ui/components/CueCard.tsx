import { useEffect, useRef } from "react";
import type { Cue } from "../../domain/cue";

export function CueCard({ cue }: { cue: Cue }) {
  const cueTextRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    const cueText = cueTextRef.current;
    if (cueText) {
      cueText.scrollLeft = cueText.scrollWidth;
    }
  }, [cue.text]);

  return (
    <article className="card cue-card">
      <p className="speaker">{cue.speaker}</p>
      <p className="cue-text-clip" ref={cueTextRef}>
        {cue.text}
      </p>
    </article>
  );
}
