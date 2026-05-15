import { useEffect, useMemo, useRef, useState } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Line } from "../../domain/line";
import { AudioQueue } from "../../rehearsal/audioQueue";
import { responsePlaybackItems } from "../../rehearsal/playbackItems";

type PlaybackUiState = "idle" | "playing" | "paused";

type PlayPageScreenProps = {
  playbook: Playbook;
  onBack: () => void;
};

type PlaySpeed = 0.5 | 0.75 | 1 | 1.25 | 1.5 | 2;

const playRates: PlaySpeed[] = [0.5, 0.75, 1, 1.25, 1.5, 2];
const lineGapMs = 500;

export function PlayPageScreen({ playbook, onBack }: PlayPageScreenProps) {
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playbackRate, setPlaybackRate] = useState<PlaySpeed>(1);
  const [playbackState, setPlaybackState] = useState<PlaybackUiState>("idle");
  const playbackSeq = useRef(0);
  const isRunthrough = useRef(false);
  const currentIndexRef = useRef(0);
  const advanceTimeout = useRef<number | null>(null);
  const lines = useMemo(() => buildPlayLineList(playbook), [playbook]);
  const currentLine: Line | null = lines[currentIndex] ?? null;
  const progressLabel = lines.length === 0 ? "" : `${currentIndex + 1} / ${lines.length}`;

  const isPlaying = playbackState === "playing";
  const isPaused = playbackState === "paused";

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  useEffect(() => {
    clearPendingAdvance();
    return () => {
      audioQueue.cancel();
      clearPendingAdvance();
    };
  }, [audioQueue]);

  async function playCurrentLine() {
    if (!currentLine) {
      return;
    }
    if (isPlaying) {
      audioQueue.pause();
      setPlaybackState("paused");
      return;
    }
    if (isPaused) {
      audioQueue.resume();
      setPlaybackState("playing");
      return;
    }
    isRunthrough.current = true;
    void playLineAtIndex(currentIndexRef.current);
  }

  function stopPlayback() {
    isRunthrough.current = false;
    playbackSeq.current += 1;
    clearPendingAdvance();
    audioQueue.cancel();
    setPlaybackState("idle");
  }

  function changeLine(nextIndex: number) {
    stopPlayback();
    setCurrentIndex(nextIndex);
  }

  function changeRate(nextRate: PlaySpeed) {
    setPlaybackRate(nextRate);
  }

  const currentLineText = currentLine?.responseText ?? "";

  async function playLineAtIndex(index: number) {
    const line = lines[index];
    if (!line) {
      return;
    }

    const thisPlaybackSeq = ++playbackSeq.current;
    setCurrentIndex(index);
    setPlaybackState("playing");
    try {
      await audioQueue.play(responsePlaybackItems(line, playbackRate));
    } finally {
      if (thisPlaybackSeq !== playbackSeq.current) {
        return;
      }
      setPlaybackState("idle");
      if (!isRunthrough.current) {
        return;
      }
      if (index >= lines.length - 1) {
        isRunthrough.current = false;
        return;
      }
      scheduleAutoAdvance(index, thisPlaybackSeq);
    }
  }

  function scheduleAutoAdvance(completedIndex: number, thisPlaybackSeq: number) {
    const nextIndex = completedIndex + 1;
    if (nextIndex >= lines.length) {
      return;
    }
    clearPendingAdvance();
    advanceTimeout.current = window.setTimeout(() => {
      if (thisPlaybackSeq !== playbackSeq.current) {
        return;
      }
      if (!isRunthrough.current) {
        return;
      }
      void playLineAtIndex(nextIndex);
    }, lineGapMs);
  }

  function clearPendingAdvance() {
    if (advanceTimeout.current !== null) {
      window.clearTimeout(advanceTimeout.current);
      advanceTimeout.current = null;
    }
  }

  return (
    <main className="shell">
      <section className="hero play-page">
        <header className="play-page-header rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary"
              aria-label="Back to library"
              title="Back to library"
              onClick={onBack}
            >
              <span aria-hidden="true">←</span>
            </button>
            <div className="rehearsal-title-stack">
              <p className="rehearsal-play-title">{playbook.title}</p>
              <p className="play-page-subtitle">Play</p>
            </div>
          </div>
          <div className="play-page-progress">{progressLabel}</div>
        </header>
        <div className="play-page-main">
          <div className="play-page-meta">
            <p className="play-page-line-id">
              {currentLine ? currentLine.id : "No line selected"}
            </p>
            <p className="play-page-line-speaker">{currentLine ? currentLine.speaker : ""}</p>
          </div>
          <p className="play-page-caption">{currentLineText}</p>
          <div className="play-page-controls">
            <button
              type="button"
              className="play-page-control"
              onClick={() => changeLine(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0 || lines.length === 0}
              aria-label="Previous section"
              title="Previous section"
            >
              ⏮
            </button>
            <button
              type="button"
              className="play-page-control play-page-primary"
              onClick={() => void playCurrentLine()}
              disabled={!currentLine}
              aria-label={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
              title={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
            >
              {playbackState === "playing" ? "⏸" : "▶"}
            </button>
            <button type="button" className="play-page-control" onClick={stopPlayback} disabled={playbackState === "idle"} aria-label="Stop" title="Stop">
              ⏹
            </button>
            <button
              type="button"
              className="play-page-control"
              onClick={() => changeLine(Math.min(lines.length - 1, currentIndex + 1))}
              disabled={lines.length === 0 || currentIndex >= lines.length - 1}
              aria-label="Next section"
              title="Next section"
            >
              ⏭
            </button>
          </div>
          <div className="play-speed-control">
            {playRates.map((rate) => (
              <button
                type="button"
                key={rate}
                className={`play-speed-button${playbackRate === rate ? " is-active" : ""}`}
                onClick={() => changeRate(rate)}
              >
                {rate}×
              </button>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function buildPlayLineList(playbook: Playbook): Line[] {
  const linesById = new Map<string, Line>();

  for (const role of playbook.roles) {
    for (const line of role.lines) {
      const prior = linesById.get(line.id);
      if (!prior || blockOrderForLine(line) < blockOrderForLine(prior)) {
        linesById.set(line.id, line);
      }
    }
  }

  return Array.from(linesById.values()).sort((left, right) => blockOrderForLine(left) - blockOrderForLine(right));
}

function blockOrderForLine(line: Line): number {
  return line.blockId
    .split(".")
    .reduce((total, part, index) => total + Number(part) * 1000 ** (3 - index), 0);
}
