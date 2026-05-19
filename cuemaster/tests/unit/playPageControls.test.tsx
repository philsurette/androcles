import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlayPageControls } from "../../src/ui/components/PlayPageControls";

describe("PlayPageControls", () => {
  afterEach(() => cleanup());

  it("keeps search collapsed until the search button opens the drawer", () => {
    const onToggleSearch = vi.fn();

    render(
      <PlayPageControls
        entryCount={2}
        currentEntryExists={true}
        previousSection={-1}
        previousLineForCurrentRole={-1}
        previousLine={-1}
        nextLine={1}
        nextLineForCurrentRole={1}
        nextSection={-1}
        playbackState="idle"
        isSearchOpen={false}
        searchQuery=""
        searchMatchDisplay="0/0"
        searchMatchCount={0}
        readNarration={true}
        includeBlocking={false}
        hasBlocking={true}
        isCalloutEnabled={false}
        hasCurrentLineCallout={false}
        playbackRate={1}
        isPlaybackSpeedOpen={false}
        playbackSpeedSelectRef={createRef<HTMLDivElement>()}
        onChangeLine={() => undefined}
        onPlayLineFromList={() => undefined}
        onPlayCurrentLine={() => undefined}
        onStopPlayback={() => undefined}
        onSearchQueryChange={() => undefined}
        onRunSearch={() => undefined}
        onToggleSearch={onToggleSearch}
        onToggleNarrationAndDirections={() => undefined}
        onToggleIncludeBlocking={() => undefined}
        onToggleCallout={() => undefined}
        onTogglePlaybackSpeed={() => undefined}
        onChangeRate={() => undefined}
      />
    );

    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /show search/i }));
    expect(onToggleSearch).toHaveBeenCalled();
  });

  it("shows a blocking toggle when the Playbook has blocking notes", () => {
    const onToggleIncludeBlocking = vi.fn();

    render(
      <PlayPageControls
        entryCount={2}
        currentEntryExists={true}
        previousSection={-1}
        previousLineForCurrentRole={-1}
        previousLine={-1}
        nextLine={1}
        nextLineForCurrentRole={1}
        nextSection={-1}
        playbackState="idle"
        isSearchOpen={false}
        searchQuery=""
        searchMatchDisplay="0/0"
        searchMatchCount={0}
        readNarration={true}
        includeBlocking={false}
        hasBlocking={true}
        isCalloutEnabled={false}
        hasCurrentLineCallout={false}
        playbackRate={1}
        isPlaybackSpeedOpen={false}
        playbackSpeedSelectRef={createRef<HTMLDivElement>()}
        onChangeLine={() => undefined}
        onPlayLineFromList={() => undefined}
        onPlayCurrentLine={() => undefined}
        onStopPlayback={() => undefined}
        onSearchQueryChange={() => undefined}
        onRunSearch={() => undefined}
        onToggleSearch={() => undefined}
        onToggleNarrationAndDirections={() => undefined}
        onToggleIncludeBlocking={onToggleIncludeBlocking}
        onToggleCallout={() => undefined}
        onTogglePlaybackSpeed={() => undefined}
        onChangeRate={() => undefined}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /show blocking/i }));

    expect(onToggleIncludeBlocking).toHaveBeenCalled();
  });
});
