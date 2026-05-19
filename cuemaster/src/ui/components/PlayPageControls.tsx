import type { RefObject } from "react";

export type PlayPagePlaybackState = "idle" | "playing" | "paused";

export type PlaySpeed = 0.5 | 0.75 | 1 | 1.25 | 1.5 | 2;

const playRates: PlaySpeed[] = [0.5, 0.75, 1, 1.25, 1.5, 2];

type PlayPageControlsProps = {
  entryCount: number;
  currentEntryExists: boolean;
  previousSection: number;
  previousLineForCurrentRole: number;
  previousLine: number;
  nextLine: number;
  nextLineForCurrentRole: number;
  nextSection: number;
  playbackState: PlayPagePlaybackState;
  isSearchOpen: boolean;
  searchQuery: string;
  searchMatchDisplay: string;
  searchMatchCount: number;
  readNarration: boolean;
  includeBlocking: boolean;
  hasBlocking: boolean;
  isCalloutEnabled: boolean;
  hasCurrentLineCallout: boolean;
  playbackRate: PlaySpeed;
  isPlaybackSpeedOpen: boolean;
  playbackSpeedSelectRef: RefObject<HTMLDivElement | null>;
  onChangeLine: (index: number) => void;
  onPlayLineFromList: (index: number) => void;
  onPlayCurrentLine: () => void;
  onStopPlayback: () => void;
  onSearchQueryChange: (query: string) => void;
  onRunSearch: (direction: "previous" | "next") => void;
  onToggleSearch: () => void;
  onToggleNarrationAndDirections: () => void;
  onToggleIncludeBlocking: () => void;
  onToggleCallout: () => void;
  onTogglePlaybackSpeed: () => void;
  onChangeRate: (rate: PlaySpeed) => void;
};

export function PlayPageControls({
  entryCount,
  currentEntryExists,
  previousSection,
  previousLineForCurrentRole,
  previousLine,
  nextLine,
  nextLineForCurrentRole,
  nextSection,
  playbackState,
  isSearchOpen,
  searchQuery,
  searchMatchDisplay,
  searchMatchCount,
  readNarration,
  includeBlocking,
  hasBlocking,
  isCalloutEnabled,
  hasCurrentLineCallout,
  playbackRate,
  isPlaybackSpeedOpen,
  playbackSpeedSelectRef,
  onChangeLine,
  onPlayLineFromList,
  onPlayCurrentLine,
  onStopPlayback,
  onSearchQueryChange,
  onRunSearch,
  onToggleSearch,
  onToggleNarrationAndDirections,
  onToggleIncludeBlocking,
  onToggleCallout,
  onTogglePlaybackSpeed,
  onChangeRate,
}: PlayPageControlsProps) {
  const selectedPlaybackRateLabel = `${playbackRate}×`;

  return (
    <div className="play-page-bottom-bar">
      <div className="play-page-controls">
        <div className="play-page-control-group play-page-control-group-left">
          <button
            type="button"
            className="play-page-control"
            onClick={() => {
              if (previousSection !== -1) {
                onChangeLine(previousSection);
              }
            }}
            disabled={previousSection === -1 || entryCount === 0}
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
                onPlayLineFromList(previousLineForCurrentRole);
              }
            }}
            disabled={previousLineForCurrentRole === -1 || entryCount === 0}
          >
            🎭◀
          </button>
          <button
            type="button"
            className="play-page-control"
            onClick={() => {
              if (previousLine !== -1) {
                onChangeLine(previousLine);
              }
            }}
            disabled={previousLine === -1 || entryCount === 0}
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
            onClick={onPlayCurrentLine}
            disabled={!currentEntryExists}
            aria-label={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
            title={playbackState === "playing" ? "Pause section" : playbackState === "paused" ? "Resume section" : "Play section"}
          >
            {playbackState === "playing" ? "Ⅱ" : "▶"}
          </button>
          <button
            type="button"
            className="play-page-control"
            onClick={onStopPlayback}
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
                onChangeLine(nextLine);
              }
            }}
            disabled={nextLine === -1 || entryCount === 0}
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
                onPlayLineFromList(nextLineForCurrentRole);
              }
            }}
            disabled={nextLineForCurrentRole === -1 || entryCount === 0}
          >
            ▶🎭
          </button>
          <button
            type="button"
            className="play-page-control"
            onClick={() => {
              if (nextSection !== -1) {
                onChangeLine(nextSection);
              }
            }}
            disabled={nextSection === -1 || entryCount === 0}
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
          className={`quick-toggle${isSearchOpen || searchQuery ? " active" : ""}`}
          aria-label={isSearchOpen ? "Hide search." : "Show search."}
          aria-pressed={isSearchOpen}
          title={searchQuery ? `Search ${searchMatchDisplay}` : "Search"}
          onClick={onToggleSearch}
        >
          <span aria-hidden="true">⌕</span>
        </button>
        <button
          type="button"
          className={`quick-toggle${readNarration ? " active" : ""}`}
          aria-label={readNarration ? "Disable directions" : "Enable directions"}
          aria-pressed={readNarration}
          title={readNarration ? "Directions are enabled" : "Directions are disabled"}
          onClick={onToggleNarrationAndDirections}
        >
          <span aria-hidden="true">⌞⌝</span>
        </button>
        <button
          type="button"
          className={includeBlocking ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={includeBlocking}
          aria-label={includeBlocking ? "Hide blocking." : "Show blocking."}
          title={hasBlocking ? `Blocking ${includeBlocking ? "visible" : "hidden"}` : "No blocking notes in this Playbook"}
          onClick={onToggleIncludeBlocking}
          disabled={!hasBlocking}
        >
          <span aria-hidden="true">⌖</span>
        </button>
        <button
          type="button"
          className={isCalloutEnabled ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={isCalloutEnabled}
          aria-label={isCalloutEnabled ? "Disable line callouts." : "Enable line callouts."}
          title={hasCurrentLineCallout ? `Callouts ${isCalloutEnabled ? "enabled" : "disabled"}` : "No callout for this line"}
          onClick={onToggleCallout}
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
            onClick={onTogglePlaybackSpeed}
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
                onClick={() => onChangeRate(rate)}
              >
                {rate}×
              </button>
            ))}
          </div>
        </div>
      </div>
      {isSearchOpen ? (
        <form
          className="play-page-search"
          onSubmit={(event) => event.preventDefault()}
        >
          <label className="play-page-search-field">
            <input
              type="search"
              placeholder="Search lines, directions, IDs, or title…"
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  onRunSearch("next");
                }
              }}
              aria-label="Search lines, directions, IDs, or title"
            />
          </label>
          <button
            type="button"
            className="quick-toggle play-page-search-arrow"
            aria-label="Previous match"
            onClick={() => onRunSearch("previous")}
            disabled={searchMatchCount === 0}
          >
            &lt;
          </button>
          <span className="play-page-search-count" aria-live="polite">{searchMatchDisplay}</span>
          <button
            type="button"
            className="quick-toggle play-page-search-arrow"
            aria-label="Next match"
            onClick={() => onRunSearch("next")}
            disabled={searchMatchCount === 0}
          >
            &gt;
          </button>
        </form>
      ) : null}
    </div>
  );
}
