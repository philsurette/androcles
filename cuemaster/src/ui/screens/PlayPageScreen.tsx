import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Line } from "../../domain/line";
import { AudioQueue, type QueueItem } from "../../rehearsal/audioQueue";
import { buildCalloutResolver } from "../../rehearsal/calloutLookup";

type PlaybackUiState = "idle" | "playing" | "paused";

type PlayPageScreenProps = {
  playbook: Playbook;
  onBack: () => void;
};

type PlaySpeed = 0.5 | 0.75 | 1 | 1.25 | 1.5 | 2;

const playRates: PlaySpeed[] = [0.5, 0.75, 1, 1.25, 1.5, 2];
const lineGapMs = 500;
const includedContextKinds = new Set(["heading", "description", "direction"]);

const directionPlaybackRate = 1;

type PlayPageEntry =
  | {
      type: "line";
      id: string;
      blockId: string;
      partId: number | null;
      speaker: string;
      text: string;
      line: Line;
      inlineDirectionAudioPaths: Array<{
        segmentId: string;
        path: string;
      }>;
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
  const sectionIndexByPartId = useMemo(() => {
    const mapping = new Map<number | null, number>();
    for (let index = 0; index < orderedSections.length; index += 1) {
      mapping.set(orderedSections[index].partId, index);
    }
    return mapping;
  }, [orderedSections]);
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
  const previousSection = previousSectionStartIndex(entries, currentIndex, sectionIndexByPartId, orderedSections);
  const nextSection = nextSectionStartIndex(entries, currentIndex, sectionIndexByPartId, orderedSections);
  const currentSectionWindow = useMemo(
    () => sectionWindowForIndex(entries, currentIndex, sectionIndexByPartId, orderedSections),
    [entries, currentIndex, sectionIndexByPartId, orderedSections]
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

  const selectedPlaybackRateLabel = `${playbackRate}×`;

  function previousLineIndex(entriesToSearch: PlayPageEntry[], index: number) {
    return index > 0 ? index - 1 : -1;
  }

  function nextLineIndex(entriesToSearch: PlayPageEntry[], index: number) {
    return index >= 0 && index < entriesToSearch.length - 1 ? index + 1 : -1;
  }

function previousRoleLineIndex(entriesToSearch: PlayPageEntry[], index: number, role?: string) {
  if (!role) {
    return -1;
  }
  const targetRole = canonicalRoleKey(role);
  for (let entryIndex = index - 1; entryIndex >= 0; entryIndex -= 1) {
    const entry = entriesToSearch[entryIndex];
    if (canonicalRoleKey(entry?.speaker) === targetRole) {
      return entryIndex;
    }
  }
  return -1;
}

function nextRoleLineIndex(entriesToSearch: PlayPageEntry[], index: number, role?: string) {
  if (!role) {
    return -1;
  }
  const targetRole = canonicalRoleKey(role);
  for (let entryIndex = index + 1; entryIndex < entriesToSearch.length; entryIndex += 1) {
    const entry = entriesToSearch[entryIndex];
    if (canonicalRoleKey(entry?.speaker) === targetRole) {
      return entryIndex;
    }
  }
  return -1;
}

function canonicalRoleKey(rawSpeaker?: string) {
  return (rawSpeaker ?? "").trim().replace(/^_+/, "").toLowerCase();
}

function entryMatchesSearchQuery(entry: PlayPageEntry, query: string, title: string): boolean {
  if (query.length === 0) {
    return false;
  }
  const looksLikeId = isLikelyIdQuery(query);
  if (looksLikeId) {
    return entryTokensForSearch(entry, title).some((token) => token === query);
  }
  const haystack = entrySearchHaystack(entry, title);
  return haystack.includes(query);
}

function entrySearchHaystack(entry: PlayPageEntry, title: string): string {
  const searchableParts: string[] = [title, entry.id, entry.speaker, entry.text];
  if (entry.type === "line") {
    for (const direction of entry.line.directions) {
      searchableParts.push(direction.text);
    }
  }
  return searchableParts.join(" ").toLowerCase();
}

function isLikelyIdQuery(query: string): boolean {
  return /^[a-z0-9]+-[0-9]+(?:\.[0-9]+)?$/.test(query) || /^[a-z0-9]+-[a-z0-9]+$/.test(query);
}

function entryTokensForSearch(entry: PlayPageEntry, title: string): string[] {
  const searchableParts: string[] = [title, entry.id, entry.speaker, entry.text];
  if (entry.type === "line") {
    for (const direction of entry.line.directions) {
      searchableParts.push(direction.text);
    }
  }
  return searchableParts
    .flatMap((part) => part
      .toLowerCase()
      .split(/[^a-z0-9-]+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0));
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

  function sectionWindowForIndex(
    entriesToSearch: PlayPageEntry[],
    index: number,
    sectionIndexMap: Map<number | null, number>,
    orderedSectionList: (typeof orderedSections),
  ) {
    if (entriesToSearch.length === 0) {
      return { start: 0, end: 0, label: "Section" };
    }

    if (index < 0 || index >= entriesToSearch.length) {
      const fallbackStart = 0;
      const fallbackEnd = entriesToSearch.length;
      return { start: fallbackStart, end: fallbackEnd, label: orderedSectionList[0]?.title ?? "Section" };
    }

    const currentPartId = entriesToSearch[index]?.partId ?? null;
    const currentSectionIndex = sectionIndexMap.get(currentPartId);
    if (currentSectionIndex === undefined) {
      return { start: 0, end: entriesToSearch.length, label: "Section" };
    }

    const currentSectionStart = sectionStartIndexForPartId(entriesToSearch, currentPartId);
    if (currentSectionStart < 0) {
      return { start: 0, end: entriesToSearch.length, label: "Section" };
    }

    let endIndex = entriesToSearch.length;
    for (let sectionOffset = currentSectionIndex + 1; sectionOffset < orderedSectionList.length; sectionOffset += 1) {
      const nextPartId = orderedSectionList[sectionOffset]?.partId ?? null;
      const nextSectionStart = sectionStartIndexForPartId(entriesToSearch, nextPartId);
      if (nextSectionStart > currentSectionStart) {
        endIndex = nextSectionStart;
        break;
      }
    }

    const sectionTitle = orderedSectionList[currentSectionIndex]?.title?.trim();
    return {
      start: currentSectionStart,
      end: endIndex,
      label: sectionTitle && sectionTitle.length > 0 ? sectionTitle : "Section",
    };
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
                  aria-label="Previous line for current role"
                  title="Previous line for current role"
                  onClick={() => {
                    if (previousLineForCurrentRole !== -1) {
                      playLineFromList(previousLineForCurrentRole);
                    }
                  }}
                  disabled={previousLineForCurrentRole === -1 || entries.length === 0}
                >
                  🎭◀
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
                  aria-label="Next line for current role"
                  title="Next line for current role"
                  onClick={() => {
                    if (nextLineForCurrentRole !== -1) {
                      playLineFromList(nextLineForCurrentRole);
                    }
                  }}
                  disabled={nextLineForCurrentRole === -1 || entries.length === 0}
                >
                  ▶🎭
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
              <form
                className="play-page-search"
                onSubmit={(event) => event.preventDefault()}
              >
                <label className="play-page-search-field">
                  <input
                    type="search"
                    placeholder="Search…"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        runSearch("next");
                      }
                    }}
                    aria-label="Search lines, directions, IDs, or title"
                  />
                </label>
                <button
                  type="button"
                  className="quick-toggle play-page-search-arrow"
                  aria-label="Previous match"
                  onClick={() => runSearch("previous")}
                  disabled={searchMatches.length === 0}
                >
                  &lt;
                </button>
                <span className="play-page-search-count" aria-live="polite">{searchMatchDisplay}</span>
                <button
                  type="button"
                  className="quick-toggle play-page-search-arrow"
                  aria-label="Next match"
                  onClick={() => runSearch("next")}
                  disabled={searchMatches.length === 0}
                >
                  &gt;
                </button>
              </form>
              <button
                type="button"
                className={`quick-toggle${readNarration ? " active" : ""}`}
                aria-label={readNarration ? "Disable directions" : "Enable directions"}
                aria-pressed={readNarration}
                title={readNarration ? "Directions are enabled" : "Directions are disabled"}
                onClick={toggleNarrationAndDirections}
              >
                <span aria-hidden="true">⌞⌝</span>
              </button>
              <button
                type="button"
                className={isCalloutEnabled ? "quick-toggle active" : "quick-toggle"}
                aria-pressed={isCalloutEnabled}
                aria-label={isCalloutEnabled ? "Disable line callouts." : "Enable line callouts."}
                title={hasCurrentLineCallout ? `Callouts ${isCalloutEnabled ? "enabled" : "disabled"}` : "No callout for this line"}
                onClick={() => {
                  setIsCalloutEnabled((current) => !current);
                }}
              >
                <span aria-hidden="true">📢</span>
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

function buildPlayEntries(playbook: Playbook, includeNarration: boolean, directionAudioLookup: DirectionAudioLookup): PlayPageEntry[] {
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

  const lines: Array<Extract<PlayPageEntry, { type: "line" }> > = Array.from(linesById.values())
      .sort((left, right) => blockOrderForBlockId(left.blockId) - blockOrderForBlockId(right.blockId))
      .map((line) => {
        const inlineDirectionAudioPaths: Array<{ segmentId: string; path: string }> = [];
        if (includeNarration) {
          for (const direction of line.directions) {
            if (direction.placement !== "inline") {
              continue;
            }
            const directionPath = directionAudioLookup.resolvePath(line, direction.segmentId);
            if (directionPath !== null) {
              inlineDirectionAudioPaths.push({
                segmentId: direction.segmentId,
                path: directionPath,
              });
            }
          }
        }

        return {
          type: "line",
          id: line.id,
          blockId: line.blockId,
          partId: line.partId,
          speaker: line.speaker,
          text: line.responseText,
          line,
          inlineDirectionAudioPaths,
          sourceOrder: sourceOrder++
        };
      });

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

type DirectionAudioLookup = {
  resolvePath(line: Line, segmentId: string): string | null;
};

function buildDirectionAudioPathLookup(playbook: Playbook): DirectionAudioLookup {
  const segmentMap = new Map<string, string>();
  const ambiguousSegments = new Set<string>();
  const candidateSegmentsByRole = new Map<string, string[]>();

  const addPath = (rawPath: string) => {
    const normalizedPath = normalizeAssetPath(rawPath);
    const match = normalizedPath.match(/^audio\/segments\/([^/]+)\/(.+)\.[a-zA-Z0-9]+$/);
    if (!match) {
      return;
    }
    const [, role, segmentId] = match;
    const roleKey = normalizeRoleForPath(role);
    const key = `${roleKey}:${segmentId}`;
    const existing = segmentMap.get(key);
    if (existing === undefined) {
      segmentMap.set(key, normalizedPath);
      candidateSegmentsByRole.set(segmentId, [...(candidateSegmentsByRole.get(segmentId) ?? []), normalizedPath]);
      return;
    }
    if (existing !== normalizedPath) {
      ambiguousSegments.add(key);
    }
  };

  if (playbook.audioAssetPaths) {
    for (const path of playbook.audioAssetPaths) {
      addPath(path);
    }
  }

  for (const role of playbook.roles) {
    for (const line of role.lines) {
      addPath(line.cue.audioPath);
      for (const segment of line.responseSegments) {
        addPath(segment.audioPath);
      }
    }
  }

  for (const block of playbook.context) {
    if (block.audioPath) {
      addPath(block.audioPath);
    }
  }

  return {
    resolvePath(line: Line, segmentId: string) {
      const preferredRoles = [
        normalizeRoleForPath(line.speaker),
        normalizeRoleForPath(line.cue.speaker),
        "NARRATOR"
      ];

      for (const role of preferredRoles) {
        const key = `${role}:${segmentId}`;
        if (ambiguousSegments.has(key)) {
          continue;
        }
        const candidate = segmentMap.get(key);
        if (candidate) {
          return candidate;
        }
      }

      const ambiguousCandidates = candidateSegmentsByRole.get(segmentId);
      if (!ambiguousCandidates || ambiguousCandidates.length === 0) {
        return null;
      }
      if (ambiguousCandidates.length === 1) {
        return ambiguousCandidates[0];
      }
      for (const role of preferredRoles) {
        const key = `${role}:${segmentId}`;
        const candidate = segmentMap.get(key);
        if (candidate && !ambiguousSegments.has(key)) {
          return candidate;
        }
      }
      return null;
    }
  };
}

function normalizeAssetPath(assetPath: string): string {
  return assetPath.replace(/^\/+/, "");
}

function normalizeRoleForPath(role: string): string {
  return role.trim().toUpperCase().replace(/^_+/, "");
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

function compareSegmentIds(left: string, right: string): number {
  if (left === right) {
    return 0;
  }
  const leftParts = splitSegmentId(left);
  const rightParts = splitSegmentId(right);
  const sharedLength = Math.min(leftParts.length, rightParts.length);
  for (let index = 0; index < sharedLength; index += 1) {
    const leftPart = leftParts[index];
    const rightPart = rightParts[index];
    if (leftPart === rightPart) {
      continue;
    }
    const leftIsNumber = typeof leftPart === "number";
    const rightIsNumber = typeof rightPart === "number";
    if (leftIsNumber && rightIsNumber) {
      return leftPart - rightPart;
    }
    if (leftIsNumber !== rightIsNumber) {
      return leftIsNumber ? -1 : 1;
    }
    return String(leftPart).localeCompare(String(rightPart));
  }
  return leftParts.length - rightParts.length;
}

function splitSegmentId(segmentId: string): Array<string | number> {
  const tokens = segmentId.split(/[^\da-zA-Z]+/).filter((token) => token.length > 0);
  return tokens.map((token) => {
    const value = Number(token);
    return Number.isFinite(value) && String(value) === token ? value : token;
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
