import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Line } from "../../src/domain/line";
import { RehearsalLineWorkspace } from "../../src/ui/components/RehearsalLineWorkspace";

describe("RehearsalLineWorkspace", () => {
  afterEach(() => cleanup());

  it("opens a blocking diagram from a targeted blocking note", () => {
    const onOpenBlockingDiagram = vi.fn();
    const line = lineWithBlocking();

    render(
      <RehearsalLineWorkspace
        line={line}
        roleDisplayName="Lillian"
        rehearsalTextSize="medium"
        visibleCues={[]}
        playbackSource={null}
        playbackState="idle"
        hasStarted={false}
        atBeginning={true}
        atEnd={true}
        bookmarkNeighbors={{ previousLineId: null, nextLineId: null }}
        isCurrentLineBookmarked={false}
        includeBlocking={true}
        includeDirections={true}
        isLineRevealed={true}
        blockingScope="role"
        hasBlockingDiagram={() => true}
        onCommand={() => undefined}
        onOpenBlockingDiagram={onOpenBlockingDiagram}
        onJumpToLine={() => undefined}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settles beside the recorder/i }));

    expect(onOpenBlockingDiagram).toHaveBeenCalledWith(line, line.blocking?.[0]);
  });

  it("keeps blocking text plain when no diagram target is available", () => {
    render(
      <RehearsalLineWorkspace
        line={lineWithBlocking()}
        roleDisplayName="Lillian"
        rehearsalTextSize="medium"
        visibleCues={[]}
        playbackSource={null}
        playbackState="idle"
        hasStarted={false}
        atBeginning={true}
        atEnd={true}
        bookmarkNeighbors={{ previousLineId: null, nextLineId: null }}
        isCurrentLineBookmarked={false}
        includeBlocking={true}
        includeDirections={true}
        isLineRevealed={true}
        blockingScope="role"
        hasBlockingDiagram={() => false}
        onCommand={() => undefined}
        onOpenBlockingDiagram={() => undefined}
        onJumpToLine={() => undefined}
      />
    );

    expect(screen.queryByRole("button", { name: /settles beside the recorder/i })).not.toBeInTheDocument();
    expect(screen.getByText(/settles beside the recorder/i)).toBeInTheDocument();
  });

  it("does not render current-line blocking in the cue strip", () => {
    render(
      <RehearsalLineWorkspace
        line={lineWithBlocking()}
        roleDisplayName="Lillian"
        rehearsalTextSize="medium"
        visibleCues={[]}
        playbackSource={null}
        playbackState="idle"
        hasStarted={false}
        atBeginning={true}
        atEnd={true}
        bookmarkNeighbors={{ previousLineId: null, nextLineId: null }}
        isCurrentLineBookmarked={false}
        includeBlocking={true}
        includeDirections={true}
        isLineRevealed={true}
        blockingScope="role"
        hasBlockingDiagram={() => true}
        onCommand={() => undefined}
        onOpenBlockingDiagram={() => undefined}
        onJumpToLine={() => undefined}
      />
    );

    expect(document.querySelector(".cue-blocking-card")).not.toBeInTheDocument();
    expect(screen.getByText(/settles beside the recorder/i).closest(".line-card")).toBeInTheDocument();
  });
});

function lineWithBlocking(): Line {
  return {
    id: "2-3",
    partId: 2,
    blockId: "2.3",
    role: "LILLIAN",
    speaker: "LILLIAN",
    contentHash: "sha256:test",
    cue: {
      speaker: "CHRISTINE",
      text: "Do you mind if I record?",
      audioPath: "audio/christine.wav",
      durationMs: 1000
    },
    responseText: "Please do.",
    responseSegments: [],
    directions: [],
    previousRoles: [],
    blocking: [
      {
        id: "2-3:b1",
        contentHash: "sha256:blocking",
        placement: "before",
        targets: ["LILLIAN"],
        text: "settles beside the recorder"
      }
    ]
  };
}
