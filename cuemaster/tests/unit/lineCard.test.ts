import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import type { Line } from "../../src/domain/line";
import { LineCard } from "../../src/ui/components/LineCard";

const line: Line = {
  id: "P-3",
  partId: null,
  blockId: "0_3",
  role: "LILLIAN",
  speaker: "Lillian",
  contentHash: "line-hash",
  cue: {
    speaker: "Christine",
    text: "Do you mind if I record?",
    audioPath: "audio/cue.wav",
    durationMs: 1000
  },
  responseText: "Please do.",
  responseSegments: [],
  directions: [],
  blocking: [
    {
      id: "P-3:b1",
      contentHash: "blocking-hash",
      text: "settles beside the recorder.",
      placement: "before",
      targets: ["LILLIAN"]
    }
  ],
  previousRoles: []
};

describe("LineCard", () => {
  it("does not render out-of-line blocking with the spoken line", () => {
    render(createElement(LineCard, { line, includeBlocking: true }));

    expect(screen.queryByText("(settles beside the recorder.)")).not.toBeInTheDocument();
    expect(screen.getByText("Please do.")).not.toHaveTextContent("settles beside the recorder");
  });
});
