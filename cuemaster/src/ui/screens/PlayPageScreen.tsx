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
const includedContextKinds = new Set(["heading", "description", "direction"]);

type PlayPageEntry =
  | {
      type: "line";
      id: string;
      blockId: string;
      speaker: string;
      text: string;
      line: Line;
      sourceOrder: number;
    }
  | {
      type: "context";
      id: string;
      blockId: string;
      speaker: string;
      text: string;
      audioPath: string;
      sourceOrder: number;
    };

export function PlayPageScreen({ playbook, onBack }: PlayPageScreenProps) {
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playbackRate, setPlaybackRate] = useState<PlaySpeed>(1);
  const [playbackState, setPlaybackState] = useState<PlaybackUiState>("idle");
  const [readNarration, setReadNarration] = useState(true);
  const playbackSeq = useRef(0);
  const isRunthrough = useRef(false);
  const currentIndexRef = useRef(0);
  const advanceTimeout = useRef<number | null>(null);
  const entries = useMemo(() => buildPlayEntries(playbook, readNarration), [playbook, readNarration]);
  const currentEntry: PlayPageEntry | null = entries[currentIndex] ?? null;
  const currentItemText = currentEntry?.text ?? "";
  const currentItemSpeaker = currentEntry?.speaker ?? "";
  const currentItemId = currentEntry?.id ?? "No line selected";
  const clampedIndex = entries.length === 0
    ? -1
    : Math.max(0, Math.min(currentIndex, entries.length - 1));
  const playbackTargetId = clampedIndex === -1 ? "No line selected" : entries[clampedIndex]?.id ?? "No line selected";

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

  useEffect(() => {
    if (entries.length === 0) {
      setCurrentIndex(0);
      return;
    }
    if (currentIndex >= entries.length) {
      setCurrentIndex(entries.length - 1);
    } else if (currentIndex < 0) {
      setCurrentIndex(0);
    }
  }, [entries, currentIndex]);

  async function playCurrentLine() {
    if (!currentEntry) {
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

  async function playLineAtIndex(index: number) {
    const entry = entries[index];
    if (!entry) {
      return;
    }

    const thisPlaybackSeq = ++playbackSeq.current;
    setCurrentIndex(index);
    setPlaybackState("playing");
    try {
      await audioQueue.play(playbackItemsForEntry(entry, playbackRate));
    } finally {
      if (thisPlaybackSeq !== playbackSeq.current) {
        return;
      }
      setPlaybackState("idle");
      if (!isRunthrough.current) {
        return;
      }
      if (index >= entries.length - 1) {
        isRunthrough.current = false;
        return;
      }
      scheduleAutoAdvance(index, thisPlaybackSeq);
    }
  }

  function scheduleAutoAdvance(completedIndex: number, thisPlaybackSeq: number) {
    const nextIndex = completedIndex + 1;
    if (nextIndex >= entries.length) {
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

  function playbackItemsForEntry(entry: PlayPageEntry, speed: number) {
    if (entry.type === "line") {
      return responsePlaybackItems(entry.line, speed);
    }
    return [{ kind: "audio", path: entry.audioPath, playbackRate: 1 }];
  }

  function toggleNarrationAndDirections() {
    stopPlayback();
    setReadNarration((current) => !current);
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
          <div className="play-page-progress">{playbackTargetId}</div>
        </header>
        <div className="play-page-main">
          <div className="play-page-meta">
            <p className="play-page-line-id">
              {currentItemId}
            </p>
            <p className="play-page-line-speaker">{currentItemSpeaker}</p>
          </div>
          <p className="play-page-caption">{currentItemText}</p>
          <div className="play-page-controls">
            <button
              type="button"
              className="play-page-control"
              onClick={() => changeLine(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0 || entries.length === 0}
              aria-label="Previous section"
              title="Previous section"
            >
              ⏮
            </button>
            <button
              type="button"
              className="play-page-control play-page-primary"
              onClick={() => void playCurrentLine()}
              disabled={!currentEntry}
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
              className={`quick-toggle${readNarration ? " active" : ""}`}
              aria-label={readNarration ? "Disable narration and directions" : "Enable narration and directions"}
              aria-pressed={readNarration}
              title={readNarration ? "Narration and directions on" : "Narration and directions off"}
              onClick={toggleNarrationAndDirections}
            >
              <span aria-hidden="true">⌞⌝</span>
            </button>
            <button
              type="button"
              className="play-page-control"
              onClick={() => changeLine(Math.min(entries.length - 1, currentIndex + 1))}
              disabled={entries.length === 0 || currentIndex >= entries.length - 1}
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

function buildPlayEntries(playbook: Playbook, includeNarration: boolean): PlayPageEntry[] {
  const linesById = new Map<string, Line>();
  const contextEntries: PlayPageEntry[] = [];
  let sourceOrder = 0;

  for (const role of playbook.roles) {
    for (const line of role.lines) {
      const prior = linesById.get(line.id);
      if (!prior || blockOrderForLine(line) < blockOrderForLine(prior)) {
        linesById.set(line.id, line);
      }
    }
  }

  if (includeNarration) {
    for (const block of playbook.context) {
      if (!block.audioPath || !includedContextKinds.has(block.kind)) {
        continue;
      }
      contextEntries.push({
        type: "context",
        id: block.id,
        blockId: block.blockId,
        speaker: block.speaker,
        text: block.text,
        audioPath: block.audioPath,
        sourceOrder
      });
      sourceOrder += 1;
    }
  }

  const lines = Array.from(linesById.values())
    .sort((left, right) => blockOrderForBlockId(left.blockId) - blockOrderForBlockId(right.blockId))
    .map((line) => ({
      type: "line",
      id: line.id,
      blockId: line.blockId,
      speaker: line.speaker,
      text: line.responseText,
      line,
      sourceOrder: sourceOrder++
    }));

  return [...lines, ...contextEntries]
    .sort((left, right) => {
      const leftOrder = blockOrderForBlockId(left.blockId);
      const rightOrder = blockOrderForBlockId(right.blockId);
      if (leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }
      if (left.type !== right.type) {
        return left.type === "context" ? -1 : 1;
      }
      return left.sourceOrder - right.sourceOrder;
    });
}

function blockOrderForBlockId(blockId: string): number {
  return blockId
    .split(".")
    .reduce((total, part, index) => total + Number(part) * 1000 ** (3 - index), 0);
}

function blockOrderForLine(line: Line): number {
  return blockOrderForBlockId(line.blockId);
}
