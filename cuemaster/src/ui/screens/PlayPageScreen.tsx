import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Playbook } from "../../domain/playbook";
import { AudioQueue, type QueueItem } from "../../rehearsal/audioQueue";
import { buildCalloutResolver } from "../../rehearsal/calloutLookup";
import {
  buildDirectionAudioPathLookup,
  buildPlayEntries,
  compareSegmentIds,
  type PlayPageEntry
} from "../../rehearsal/playPageEntries";
import {
  nextLineIndex,
  nextRoleLineIndex,
  nextSectionStartIndex,
  previousLineIndex,
  previousRoleLineIndex,
  previousSectionStartIndex,
  sectionIndexByPartId,
  sectionWindowForIndex
} from "../../rehearsal/playPageNavigation";
import { entryMatchesSearchQuery } from "../../rehearsal/playPageSearch";
import { PlayPageControls, type PlayPagePlaybackState, type PlaySpeed } from "../components/PlayPageControls";

type PlayPageScreenProps = {
  playbook: Playbook;
  onBack: () => void;
};

const lineGapMs = 500;

const directionPlaybackRate = 1;

export function PlayPageScreen({ playbook, onBack }: PlayPageScreenProps) {
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playbackRate, setPlaybackRate] = useState<PlaySpeed>(1);
  const [playbackState, setPlaybackState] = useState<PlayPagePlaybackState>("idle");
  const [readNarration, setReadNarration] = useState(true);
  const [isCalloutEnabled, setIsCalloutEnabled] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMatchIndex, setSearchMatchIndex] = useState(-1);
  const playbackSeq = useRef(0);
  const calloutPlaybackSeq = useRef(0);
  const isRunthrough = useRef(false);
  const currentIndexRef = useRef(0);
  const advanceTimeout = useRef<number | null>(null);
  const playbackSpeedSelectRef = useRef<HTMLDivElement | null>(null);
  const linePaneRefs = useRef<Map<number, HTMLFieldSetElement | null>>(new Map());
  const [isPlaybackSpeedOpen, setIsPlaybackSpeedOpen] = useState(false);
  const audioAssetLookup = useMemo(() => buildDirectionAudioPathLookup(playbook), [playbook]);
  const entries = useMemo(() => buildPlayEntries(playbook, readNarration, audioAssetLookup), [playbook, readNarration, audioAssetLookup]);
  const orderedSections = useMemo(
    () => [...playbook.sections].sort((left, right) => left.ordinal - right.ordinal),
    [playbook.sections]
  );
  const resolveCallout = useMemo(() => buildCalloutResolver(playbook), [playbook]);
  const sectionIndexMap = useMemo(() => sectionIndexByPartId(orderedSections), [orderedSections]);
  const currentEntry: PlayPageEntry | null = entries[currentIndex] ?? null;
  const currentLine = currentEntry?.type === "line" ? currentEntry.line : null;
  const currentLineCallout = useMemo(() => {
    return resolveCallout(currentLine);
  }, [currentLine, resolveCallout]);
  const hasCurrentLineCallout = currentLineCallout !== null;
  const normalizedSearchQuery = searchQuery.trim().toLowerCase();
  const searchMatches = useMemo(() => {
    if (normalizedSearchQuery.length === 0 || entries.length === 0) {
      return [];
    }
    const matches: number[] = [];
    for (let index = 0; index < entries.length; index += 1) {
      const entry = entries[index];
      if (entryMatchesSearchQuery(entry, normalizedSearchQuery, playbook.title)) {
        matches.push(index);
      }
    }
    return matches;
  }, [entries, normalizedSearchQuery, playbook.title]);
  const searchMatchDisplay = useMemo(() => {
    if (!normalizedSearchQuery) {
      return "0/0";
    }
    const total = searchMatches.length;
    if (total === 0 || searchMatchIndex < 0) {
      return `0/${total}`;
    }
    return `${Math.min(searchMatchIndex + 1, total)}/${total}`;
  }, [normalizedSearchQuery, searchMatches.length, searchMatchIndex]);

  const clampedIndex = entries.length === 0
    ? -1
    : Math.max(0, Math.min(currentIndex, entries.length - 1));
  const playbackTargetId = clampedIndex === -1 ? "No line selected" : entries[clampedIndex]?.id ?? "No line selected";
  const previousLine = previousLineIndex(entries, currentIndex);
  const nextLine = nextLineIndex(entries, currentIndex);
  const previousLineForCurrentRole = previousRoleLineIndex(entries, currentIndex, currentEntry?.speaker);
  const nextLineForCurrentRole = nextRoleLineIndex(entries, currentIndex, currentEntry?.speaker);
  const previousSection = previousSectionStartIndex(entries, currentIndex, sectionIndexMap, orderedSections);
  const nextSection = nextSectionStartIndex(entries, currentIndex, sectionIndexMap, orderedSections);
  const currentSectionWindow = useMemo(
    () => sectionWindowForIndex(entries, currentIndex, sectionIndexMap, orderedSections),
    [entries, currentIndex, sectionIndexMap, orderedSections]
  );
  const currentSectionEntries = entries.slice(currentSectionWindow.start, currentSectionWindow.end);

  const isPlaying = playbackState === "playing";
  const isPaused = playbackState === "paused";

  function calloutPlaybackItemsForEntry(entry: PlayPageEntry): QueueItem[] {
    if (!isCalloutEnabled || entry.type !== "line") {
      return [];
    }
    const callout = resolveCallout(entry.line);
    if (!callout) {
      return [];
    }
    return [
      { kind: "audio", path: callout.audioPath, playbackRate: 1 },
      { kind: "delay", durationMs: 250 }
    ];
  }

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  useEffect(() => {
    const node = linePaneRefs.current.get(currentIndex);
    if (!node || !currentSectionWindow) {
      return;
    }
    node.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [currentIndex, currentSectionWindow.start, currentSectionWindow.end]);

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
      setSearchMatchIndex(-1);
      return;
    }
    if (currentIndex >= entries.length) {
      setCurrentIndex(entries.length - 1);
    } else if (currentIndex < 0) {
      setCurrentIndex(0);
    }
  }, [entries, currentIndex]);

  useEffect(() => {
    setSearchMatchIndex(-1);
  }, [normalizedSearchQuery]);

  useEffect(() => {
    setSearchMatchIndex((current) => (current >= searchMatches.length ? -1 : current));
  }, [searchMatches.length]);

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

  async function playCurrentCallout() {
    if (!currentLineCallout) {
      return;
    }
    stopPlayback();
    const thisCalloutPlaybackSeq = ++calloutPlaybackSeq.current;
    await audioQueue.play([{ kind: "audio", path: currentLineCallout.audioPath, playbackRate: 1 }]);
    if (thisCalloutPlaybackSeq !== calloutPlaybackSeq.current) {
      return;
    }
  }

  function changeLine(nextIndex: number) {
    navigateToIndex(nextIndex, true);
  }

  function playLineFromList(nextIndex: number) {
    if (entries[nextIndex] === undefined) {
      return;
    }
    stopPlayback();
    isRunthrough.current = true;
    setCurrentIndex(nextIndex);
    void playLineAtIndex(nextIndex);
  }

  function navigateToIndex(nextIndex: number, shouldResumePlayback: boolean) {
    if (entries[nextIndex] === undefined) {
      return;
    }
    if (!shouldResumePlayback || playbackState !== "playing") {
      stopPlayback();
      setCurrentIndex(nextIndex);
      return;
    }
    stopPlayback();
    isRunthrough.current = true;
    void playLineAtIndex(nextIndex);
  }

  function runSearch(direction: "previous" | "next") {
    if (searchMatches.length === 0) {
      setSearchMatchIndex(-1);
      return;
    }
    const shouldResumePlayback = playbackState === "playing";
    const currentMatchPosition = currentIndex >= 0 ? searchMatches.indexOf(currentIndex) : -1;
    let targetMatchPosition: number;

    if (currentMatchPosition >= 0) {
      targetMatchPosition =
        direction === "next"
          ? (currentMatchPosition + 1) % searchMatches.length
          : (currentMatchPosition - 1 + searchMatches.length) % searchMatches.length;
      if (targetMatchPosition < 0) {
        targetMatchPosition = searchMatches.length - 1;
      }
    } else if (searchMatchIndex >= 0 && searchMatchIndex < searchMatches.length) {
      targetMatchPosition =
        direction === "next"
          ? searchMatchIndex + 1 < searchMatches.length
            ? searchMatchIndex + 1
            : 0
          : searchMatchIndex - 1 >= 0
            ? searchMatchIndex - 1
            : searchMatches.length - 1;
    } else {
      targetMatchPosition = direction === "next" ? 0 : searchMatches.length - 1;
    }

    const targetIndex = searchMatches[targetMatchPosition] ?? -1;
    if (targetIndex >= 0) {
      setSearchMatchIndex(targetMatchPosition);
      setCurrentIndex(targetIndex);
      if (shouldResumePlayback) {
        isRunthrough.current = true;
        void playLineAtIndex(targetIndex);
      }
    } else {
      setSearchMatchIndex(-1);
    }
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

  function playbackItemsForEntry(entry: PlayPageEntry, speed: number): QueueItem[] {
    const calloutItems = calloutPlaybackItemsForEntry(entry);
    if (entry.type === "line") {
      const inlineDirectionItems = entry.inlineDirectionAudioPaths.map((direction, index) => ({
        kind: "direction" as const,
        segmentId: direction.segmentId,
        path: direction.path,
        playbackRate: directionPlaybackRate,
        sortOrder: index * 2 + 1,
      }));
      const responseItems = entry.line.responseSegments.map((segment, index) => ({
        kind: "response" as const,
        segmentId: segment.segmentId,
        path: segment.audioPath,
        playbackRate: speed,
        sortOrder: index * 2,
      }));
      const lineItems = [...inlineDirectionItems, ...responseItems]
        .sort((left, right) => {
          const segmentCompare = compareSegmentIds(left.segmentId, right.segmentId);
          if (segmentCompare !== 0) {
            return segmentCompare;
          }
          return left.sortOrder - right.sortOrder;
        })
        .map((item) => ({
          kind: "audio" as const,
          path: item.path,
          playbackRate: item.playbackRate,
        }));
      return [
        ...calloutItems,
        ...lineItems
      ];
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
          <div className="play-page-content">
            <section className="play-page-lines-area" aria-label={currentSectionWindow.label}>
              <p className="play-page-lines-label">{currentSectionWindow.label}</p>
              <div className="play-page-lines-list">
                {currentSectionEntries.map((entry, offset) => {
                    const globalIndex = currentSectionWindow.start + offset;
                    const isCurrent = globalIndex === currentIndex;
                    return (
                    <fieldset
                      key={`${entry.id}-${globalIndex}`}
                      className={`play-page-line-pane cue-section-panel${isCurrent ? " is-current" : ""}`}
                      ref={(node) => {
                        if (node) {
                          linePaneRefs.current.set(globalIndex, node);
                        } else {
                          linePaneRefs.current.delete(globalIndex);
                        }
                      }}
                      onClick={() => playLineFromList(globalIndex)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          playLineFromList(globalIndex);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-label={`${entry.speaker}: ${entry.id}`}
                      aria-current={isCurrent}
                    >
                      <legend className="play-page-line-pane-title">
                        <span>{entry.speaker}</span>
                        <span className="play-page-line-id-tag">{entry.id}</span>
                      </legend>
                      <p className="play-page-caption">{renderLineText(entry, readNarration)}</p>
                    </fieldset>
                  );
                })}
              </div>
            </section>
          </div>
          <PlayPageControls
            entryCount={entries.length}
            currentEntryExists={currentEntry !== null}
            previousSection={previousSection}
            previousLineForCurrentRole={previousLineForCurrentRole}
            previousLine={previousLine}
            nextLine={nextLine}
            nextLineForCurrentRole={nextLineForCurrentRole}
            nextSection={nextSection}
            playbackState={playbackState}
            searchQuery={searchQuery}
            searchMatchDisplay={searchMatchDisplay}
            searchMatchCount={searchMatches.length}
            readNarration={readNarration}
            isCalloutEnabled={isCalloutEnabled}
            hasCurrentLineCallout={hasCurrentLineCallout}
            playbackRate={playbackRate}
            isPlaybackSpeedOpen={isPlaybackSpeedOpen}
            playbackSpeedSelectRef={playbackSpeedSelectRef}
            onChangeLine={changeLine}
            onPlayLineFromList={playLineFromList}
            onPlayCurrentLine={() => void playCurrentLine()}
            onStopPlayback={stopPlayback}
            onSearchQueryChange={setSearchQuery}
            onRunSearch={runSearch}
            onToggleNarrationAndDirections={toggleNarrationAndDirections}
            onToggleCallout={() => setIsCalloutEnabled((current) => !current)}
            onTogglePlaybackSpeed={() => setIsPlaybackSpeedOpen((current) => !current)}
            onChangeRate={changeRate}
          />
        </div>
      </section>
    </main>
  );
}

function renderLineText(entry: PlayPageEntry, includeDirections: boolean) {
  if (entry.type !== "line" || !includeDirections || entry.line.directions.length === 0) {
    return entry.text;
  }
  const inlineDirections = entry.line.directions.filter((direction) => direction.placement === "inline");
  if (inlineDirections.length === 0) {
    return entry.text;
  }

  const mergedParts = [
    ...entry.line.responseSegments.map((segment, index) => ({
      kind: "response",
      segmentId: segment.segmentId,
      text: segment.text,
      orderIndex: index * 2
    })),
    ...inlineDirections.map((direction, index) => ({
      kind: "direction",
      segmentId: direction.segmentId,
      text: direction.text,
      orderIndex: index * 2 + 1
    }))
  ].sort((left, right) => {
    const segmentCompare = compareSegmentIds(left.segmentId, right.segmentId);
    if (segmentCompare !== 0) {
      return segmentCompare;
    }
    return left.orderIndex - right.orderIndex;
  });

  const nodes: ReactNode[] = [];
  mergedParts.forEach((part, index) => {
    if (part.text.trim().length === 0) {
      return;
    }
    if (index > 0 && nodes.length > 0 && nodes[nodes.length - 1] !== " ") {
      nodes.push(" ");
    }
    if (part.kind === "direction") {
      nodes.push(
        <span className="inline-stage-direction" key={`${entry.id}-inline-direction-${index}-${part.segmentId}`}>
          {part.text}
        </span>
      );
    } else {
      nodes.push(part.text);
    }
  });

  return <>{nodes}</>;
}
