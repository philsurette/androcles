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
      partId: number | null;
      speaker: string;
      text: string;
      line: Line;
      sourceOrder: number;
    }
  | {
      type: "context";
      id: string;
      blockId: string;
      partId: number | null;
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
  const playbackSpeedSelectRef = useRef<HTMLDivElement | null>(null);
  const [isPlaybackSpeedOpen, setIsPlaybackSpeedOpen] = useState(false);
  const entries = useMemo(() => buildPlayEntries(playbook, readNarration), [playbook, readNarration]);
  const orderedSections = useMemo(
    () => [...playbook.sections].sort((left, right) => left.ordinal - right.ordinal),
    [playbook.sections]
  );
  const sectionIndexByPartId = useMemo(() => {
    const mapping = new Map<number | null, number>();
    for (let index = 0; index < orderedSections.length; index += 1) {
      mapping.set(orderedSections[index].partId, index);
    }
    return mapping;
  }, [orderedSections]);
  const currentEntry: PlayPageEntry | null = entries[currentIndex] ?? null;
  const currentItemText = currentEntry?.text ?? "";
  const currentItemSpeaker = currentEntry?.speaker ?? "";
  const currentItemId = currentEntry?.id ?? "No line selected";
  const clampedIndex = entries.length === 0
    ? -1
    : Math.max(0, Math.min(currentIndex, entries.length - 1));
  const playbackTargetId = clampedIndex === -1 ? "No line selected" : entries[clampedIndex]?.id ?? "No line selected";
  const previousLine = previousLineIndex(entries, currentIndex);
  const nextLine = nextLineIndex(entries, currentIndex);
  const previousSection = previousSectionStartIndex(entries, currentIndex, sectionIndexByPartId, orderedSections);
  const nextSection = nextSectionStartIndex(entries, currentIndex, sectionIndexByPartId, orderedSections);

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
    if (!isPlaybackSpeedOpen) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      const container = playbackSpeedSelectRef.current;
      if (container && !container.contains(event.target as Node)) {
        setIsPlaybackSpeedOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsPlaybackSpeedOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isPlaybackSpeedOpen]);

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
    setIsPlaybackSpeedOpen(false);
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

  const selectedPlaybackRateLabel = `${playbackRate}×`;

  function previousLineIndex(entriesToSearch: PlayPageEntry[], index: number) {
    return index > 0 ? index - 1 : -1;
  }

  function nextLineIndex(entriesToSearch: PlayPageEntry[], index: number) {
    return index >= 0 && index < entriesToSearch.length - 1 ? index + 1 : -1;
  }

  function sectionStartIndexForPartId(entriesToSearch: PlayPageEntry[], targetPartId: number | null) {
    for (let entryIndex = 0; entryIndex < entriesToSearch.length; entryIndex += 1) {
      if (entriesToSearch[entryIndex]?.partId === targetPartId) {
        return entryIndex;
      }
    }
    return -1;
  }

  function previousSectionStartIndex(
    entriesToSearch: PlayPageEntry[],
    index: number,
    sectionIndexMap: Map<number | null, number>,
    orderedSectionList: (typeof orderedSections),
  ) {
    if (index < 0 || index >= entriesToSearch.length) {
      return -1;
    }
    const currentPartId = entriesToSearch[index]?.partId ?? null;
    const currentSectionIndex = sectionIndexMap.get(currentPartId);
    if (currentSectionIndex === undefined) {
      return -1;
    }

    const currentSectionStart = sectionStartIndexForPartId(entriesToSearch, currentPartId);
    if (currentSectionStart < 0) {
      return -1;
    }
    if (index > currentSectionStart) {
      return currentSectionStart;
    }
    if (currentSectionIndex <= 0) {
      return -1;
    }

    const targetPartId = orderedSectionList[currentSectionIndex - 1]?.partId ?? null;
    return sectionStartIndexForPartId(entriesToSearch, targetPartId);
  }

  function nextSectionStartIndex(
    entriesToSearch: PlayPageEntry[],
    index: number,
    sectionIndexMap: Map<number | null, number>,
    orderedSectionList: (typeof orderedSections),
  ) {
    if (index < 0 || index >= entriesToSearch.length) {
      return -1;
    }
    const currentPartId = entriesToSearch[index]?.partId ?? null;
    const currentSectionIndex = sectionIndexMap.get(currentPartId);
    if (currentSectionIndex === undefined) {
      return -1;
    }
    const currentSectionStart = sectionStartIndexForPartId(entriesToSearch, currentPartId);
    if (currentSectionStart < 0) {
      return -1;
    }
    if (index < currentSectionStart) {
      return currentSectionStart;
    }
    if (currentSectionIndex >= orderedSectionList.length - 1) {
      return -1;
    }
    const targetPartId = orderedSectionList[currentSectionIndex + 1]?.partId ?? null;
    return sectionStartIndexForPartId(entriesToSearch, targetPartId);
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
          <div className="play-page-content">
            <div className="play-page-meta">
              <p className="play-page-line-speaker">{currentItemSpeaker}</p>
            </div>
            <p className="play-page-caption">{currentItemText}</p>
          </div>
          <div className="play-page-bottom-bar">
            <div className="play-page-controls">
              <div className="play-page-control-group play-page-control-group-left">
                <button
                  type="button"
                  className="play-page-control"
                  onClick={() => {
                    if (previousSection !== -1) {
                      changeLine(previousSection);
                    }
                  }}
                  disabled={previousSection === -1 || entries.length === 0}
                  aria-label="Previous section"
                  title="Previous section"
                >
                  |◀
                </button>
                <button
                  type="button"
                  className="play-page-control"
                  aria-label="Rewind 15 seconds"
                  title="Rewind 15 seconds (not implemented yet)"
                  onClick={() => {
                    // No-op until implementation discussion is complete.
                  }}
                >
                  ◀◀
                </button>
                <button
                  type="button"
                  className="play-page-control"
                  onClick={() => {
                    if (previousLine !== -1) {
                      changeLine(previousLine);
                    }
                  }}
                  disabled={previousLine === -1 || entries.length === 0}
                  aria-label="Previous line"
                  title="Previous line"
                >
                  ←
                </button>
              </div>
              <div className="play-page-control-group play-page-control-group-center">
                <button
                  type="button"
                  className="play-page-control play-page-primary"
                  onClick={() => void playCurrentLine()}
                  disabled={!currentEntry}
                  aria-label={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
                  title={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
                >
                  {playbackState === "playing" ? "Ⅱ" : "▶"}
                </button>
                <button
                  type="button"
                  className="play-page-control"
                  onClick={stopPlayback}
                  disabled={playbackState === "idle"}
                  aria-label="Stop"
                  title="Stop"
                >
                  ■
                </button>
              </div>
              <div className="play-page-control-group play-page-control-group-right">
                <button
                  type="button"
                  className="play-page-control"
                  onClick={() => {
                    if (nextLine !== -1) {
                      changeLine(nextLine);
                    }
                  }}
                  disabled={nextLine === -1 || entries.length === 0}
                  aria-label="Next line"
                  title="Next line"
                >
                  →
                </button>
                <button
                  type="button"
                  className="play-page-control"
                  aria-label="Fast-forward 30 seconds"
                  title="Fast-forward 30 seconds (not implemented yet)"
                  onClick={() => {
                    // No-op until implementation discussion is complete.
                  }}
                >
                  ▶▶
                </button>
                <button
                  type="button"
                  className="play-page-control"
                  onClick={() => {
                    if (nextSection !== -1) {
                      changeLine(nextSection);
                    }
                  }}
                  disabled={nextSection === -1 || entries.length === 0}
                  aria-label="Next section"
                  title="Next section"
                >
                  ▶|
                </button>
              </div>
            </div>
            <div className="play-page-utility-bar">
              <button
                type="button"
                className={`quick-toggle${readNarration ? " active" : ""}`}
                aria-label={readNarration ? "Disable directions" : "Enable directions"}
                aria-pressed={readNarration}
                title={readNarration ? "Directions are enabled" : "Directions are disabled"}
                onClick={toggleNarrationAndDirections}
              >
                <span aria-hidden="true">⌞</span>
              </button>
              <div className="play-page-speed-wrap" ref={playbackSpeedSelectRef}>
                <button
                  type="button"
                  className="practice-select-trigger"
                  aria-label="Select playback speed"
                  title="Select playback speed"
                  aria-expanded={isPlaybackSpeedOpen}
                  aria-controls="play-page-speed-options"
                  onClick={() => setIsPlaybackSpeedOpen((current) => !current)}
                >
                  <span>{selectedPlaybackRateLabel}</span>
                  <span className="practice-select-caret" aria-hidden="true">
                    ▾
                  </span>
                </button>
                <div id="play-page-speed-options" role="listbox" className={`practice-select-options ${isPlaybackSpeedOpen ? "open" : ""}`} aria-label="Playback speed">
                  {playRates.map((rate) => (
                    <button
                      key={rate}
                      type="button"
                      role="option"
                      aria-selected={playbackRate === rate}
                      className={playbackRate === rate ? "practice-select-option active" : "practice-select-option"}
                      onClick={() => changeRate(rate)}
                    >
                      {rate}×
                    </button>
                  ))}
                </div>
              </div>
            </div>
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
        partId: block.partId,
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
        partId: line.partId,
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
