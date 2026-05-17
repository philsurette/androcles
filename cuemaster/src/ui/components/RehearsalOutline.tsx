import { useEffect, useRef, useState } from "react";
import type { Line } from "../../domain/line";
import type { Playbook } from "../../domain/playbook";
import {
  outlineSearchText,
  outlineSpeaker,
  outlineText,
  type OutlineMode
} from "../../rehearsal/rehearsalPresentation";
import { scriptBrowserSections } from "../../rehearsal/scriptBrowser";
import type { BlockingScope } from "./LineCard";

export type TimingLineStatus = "untimed" | "slow" | "fast" | "good";

type RehearsalOutlineProps = {
  currentLineId: string | null;
  includeBlocking: boolean;
  blockingScope: BlockingScope;
  includeDirections: boolean;
  bookmarkedLineIds: Set<string>;
  lineTimingStatusByLineId: Map<string, TimingLineStatus>;
  isOpen: boolean;
  isCompactViewport: boolean;
  playbook: Playbook;
  lines: Line[];
  sections: Playbook["sections"];
  onSelectLine: (lineId: string) => void;
  onToggleOpen: () => void;
};

type OutlinePanelProps = Omit<RehearsalOutlineProps, "isOpen">;

export function RehearsalOutline({
  currentLineId,
  includeBlocking,
  blockingScope,
  includeDirections,
  bookmarkedLineIds,
  lineTimingStatusByLineId,
  isOpen,
  isCompactViewport,
  playbook,
  lines,
  sections,
  onSelectLine,
  onToggleOpen
}: RehearsalOutlineProps) {
  if (isCompactViewport && !isOpen) {
    return null;
  }
  if (!isOpen) {
    return (
      <aside className="outline-sidecar collapsed" aria-label="Rehearsal outline">
        <button
          type="button"
          className="outline-disclosure-button"
          aria-label="Show outline."
          title="Show outline"
          onClick={onToggleOpen}
        >
          <span className="context-disclosure" aria-hidden="true" />
        </button>
        <span className="outline-progress" aria-label={`${currentLineId ?? "No line"} selected`}>
          {currentLineId ?? "No line"}
        </span>
      </aside>
    );
  }

  return (
    <OutlinePanel
      currentLineId={currentLineId}
      includeBlocking={includeBlocking}
      blockingScope={blockingScope}
      includeDirections={includeDirections}
      playbook={playbook}
      lines={lines}
      sections={sections}
      isCompactViewport={isCompactViewport}
      bookmarkedLineIds={bookmarkedLineIds}
      lineTimingStatusByLineId={lineTimingStatusByLineId}
      onSelectLine={onSelectLine}
      onToggleOpen={onToggleOpen}
    />
  );
}

function OutlinePanel({
  currentLineId,
  includeBlocking,
  blockingScope,
  includeDirections,
  bookmarkedLineIds,
  lineTimingStatusByLineId,
  playbook,
  lines,
  sections,
  isCompactViewport,
  onSelectLine,
  onToggleOpen
}: OutlinePanelProps) {
  const [mode, setMode] = useState<OutlineMode>("cues");
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showBookmarksOnly, setShowBookmarksOnly] = useState(false);
  const [activeTimingFilters, setActiveTimingFilters] = useState<TimingLineStatus[]>([]);
  const currentLineRef = useRef<HTMLButtonElement | null>(null);
  const modeMenuRef = useRef<HTMLDivElement | null>(null);
  const showAllTimings = activeTimingFilters.length === 0;
  const normalizedSearchQuery = searchQuery.trim();
  const sectionGroups = scriptBrowserSections(lines, sections)
    .map((section) => ({
      ...section,
      lines: section.lines
        .filter((line) => (showBookmarksOnly ? bookmarkedLineIds.has(line.id) : true))
        .filter((line) =>
          showAllTimings ? true : activeTimingFilters.includes(lineTimingStatusByLineId.get(line.id) ?? "untimed")
        )
        .filter((line) =>
          outlineSearchText(line, mode, includeDirections, includeBlocking, blockingScope, playbook)
            .toLocaleLowerCase()
            .includes(normalizedSearchQuery.toLocaleLowerCase())
      )
    }))
    .filter((section) => section.lines.length > 0);
  const activeTimingFilterSummary = showAllTimings ? "" : activeTimingFilters.join(" + ");

  function toggleTimingFilter(target: TimingLineStatus) {
    setActiveTimingFilters((current) => {
      if (current.includes(target)) {
        return current.filter((status) => status !== target);
      }
      return [...current, target];
    });
  }

  function timingFilterGlyph(status: TimingLineStatus): string {
    if (status === "slow") {
      return "🐢";
    }
    if (status === "fast") {
      return "🐇";
    }
    if (status === "good") {
      return "🎯";
    }
    return "⏱";
  }

  function timingFilterLabel(status: TimingLineStatus): string {
    if (status === "slow") {
      return "slow";
    }
    if (status === "fast") {
      return "fast";
    }
    if (status === "good") {
      return "on target";
    }
    return "untimed";
  }

  useEffect(() => {
    currentLineRef.current?.scrollIntoView({ block: "nearest" });
  }, [currentLineId, mode]);

  useEffect(() => {
    if (!isModeMenuOpen) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (!modeMenuRef.current?.contains(event.target as Node)) {
        setIsModeMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsModeMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isModeMenuOpen]);

  return (
    <aside className="outline-sidecar outline-browser" aria-label="Rehearsal outline">
      <div className="outline-header">
        <div className="outline-header-actions">
          <div className="outline-header-left">
            {isCompactViewport ? (
              <button
                type="button"
                className="icon-button secondary"
                aria-label="Back to rehearsal."
                title="Back to rehearsal."
                onClick={onToggleOpen}
              >
                <span aria-hidden="true">←</span>
              </button>
            ) : null}
            <div className="outline-timing-filter-group" aria-label="Timing filters">
              {(["slow", "good", "fast", "untimed"] as TimingLineStatus[]).map((status) => {
                const isActive = activeTimingFilters.includes(status);
                return (
                  <button
                    type="button"
                    key={status}
                    className={`outline-timing-filter ${isActive ? "active" : ""}`}
                    aria-pressed={isActive}
                    aria-label={`Show ${timingFilterLabel(status)} lines`}
                    title={isActive ? `Hide ${timingFilterLabel(status)} lines` : `Show ${timingFilterLabel(status)} lines`}
                    onClick={() => toggleTimingFilter(status)}
                  >
                    {timingFilterGlyph(status)}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              className={showBookmarksOnly ? "outline-bookmark-filter active" : "outline-bookmark-filter"}
              aria-pressed={showBookmarksOnly}
              aria-label={showBookmarksOnly ? "Show all lines" : "Show bookmarked lines only"}
              onClick={() => setShowBookmarksOnly((current) => !current)}
              title={showBookmarksOnly ? "Show all lines" : "Show bookmarked lines only"}
            >
              {showBookmarksOnly ? "★" : "☆"}
            </button>
            <div className="outline-mode-select-wrap" ref={modeMenuRef}>
              <button
                type="button"
                className="outline-mode-select"
                aria-label="Outline mode"
                aria-expanded={isModeMenuOpen}
                aria-controls="outline-mode-options"
                title={mode === "cues" ? "Outline mode: cues" : "Outline mode: lines"}
                onClick={() => setIsModeMenuOpen((current) => !current)}
              >
                <span>{mode === "cues" ? "Cues" : "Lines"}</span>
                <span className="outline-mode-select-caret" aria-hidden="true">
                  ▾
                </span>
              </button>
              <div
                id="outline-mode-options"
                className={`outline-mode-select-options ${isModeMenuOpen ? "open" : ""}`}
                role="listbox"
                aria-label="Outline mode"
              >
                <button
                  type="button"
                  role="option"
                  className={mode === "cues" ? "outline-mode-select-option active" : "outline-mode-select-option"}
                  aria-selected={mode === "cues"}
                  title="Show cues"
                  onClick={() => {
                    setMode("cues");
                    setIsModeMenuOpen(false);
                  }}
                >
                  Cues
                </button>
                <button
                  type="button"
                  role="option"
                  className={mode === "lines" ? "outline-mode-select-option active" : "outline-mode-select-option"}
                  aria-selected={mode === "lines"}
                  title="Show lines"
                  onClick={() => {
                    setMode("lines");
                    setIsModeMenuOpen(false);
                  }}
                >
                  Lines
                </button>
              </div>
            </div>
          </div>
          {!isCompactViewport ? (
            <button
              type="button"
              className="outline-disclosure-button expanded"
              aria-label="Hide outline."
              title="Hide outline"
              onClick={onToggleOpen}
            >
              <span className="context-disclosure" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </div>
      <label className="outline-search">
        <span>Search {mode === "cues" ? "cues" : "lines"}</span>
        <div>
          <input
            type="search"
            value={searchQuery}
            placeholder={mode === "cues" ? "Find a line by cue text or line id" : "Find a line by line text or line id"}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          {searchQuery ? (
            <button
              type="button"
              aria-label="Clear outline search."
              title="Clear outline search."
              onClick={() => setSearchQuery("")}
            >
              ×
            </button>
          ) : null}
        </div>
      </label>
      <div className="outline-list">
        {sectionGroups.length === 0 ? (
          <p className="outline-empty">
            No matching {showBookmarksOnly ? "bookmarked " : ""}
            {!showAllTimings ? ` ${activeTimingFilterSummary} ` : ""}
            {mode === "cues" ? "cues" : "lines"}.
          </p>
        ) : null}
        {sectionGroups.map((section) => (
          <section className="outline-section" key={section.id}>
            <h3>{section.title}</h3>
            <div className="outline-section-list">
              {section.lines.map((line) => (
                <button
                  type="button"
                  key={line.id}
                  className={line.id === currentLineId ? "outline-row selected" : "outline-row"}
                  ref={line.id === currentLineId ? currentLineRef : undefined}
                  onClick={() => onSelectLine(line.id)}
                >
                  <span
                    className={`status-dot timing timing-${lineTimingStatusByLineId.get(line.id) ?? "untimed"}`}
                    title={timingLineStatusToLabel(lineTimingStatusByLineId.get(line.id) ?? "untimed")}
                    aria-hidden="true"
                  >
                    {timingLineStatusToGlyph(lineTimingStatusByLineId.get(line.id) ?? "untimed")}
                  </span>
                  <span
                    className={`status-dot${bookmarkedLineIds.has(line.id) ? " bookmark" : ""}`}
                    aria-hidden="true"
                  >
                    {bookmarkedLineIds.has(line.id) ? "★" : null}
                  </span>
                  <strong>{line.id}</strong>
                  <span className="outline-speaker">{outlineSpeaker(line, mode, includeDirections, playbook)}</span>
                  <span className="outline-text">{outlineText(line, mode, includeDirections, playbook)}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}

function timingLineStatusToGlyph(status: TimingLineStatus): string {
  if (status === "slow") {
    return "🐢";
  }
  if (status === "fast") {
    return "🐇";
  }
  if (status === "good") {
    return "🎯";
  }
  return "⏱";
}

function timingLineStatusToLabel(status: TimingLineStatus): string {
  if (status === "slow") {
    return "Slow timing";
  }
  if (status === "fast") {
    return "Fast timing";
  }
  if (status === "good") {
    return "Good timing";
  }
  return "Untimed";
}
