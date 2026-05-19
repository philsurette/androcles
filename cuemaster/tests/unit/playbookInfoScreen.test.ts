import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import type { Playbook } from "../../src/domain/playbook";
import { PlaybookInfoScreen } from "../../src/ui/screens/PlaybookInfoScreen";

describe("PlaybookInfoScreen", () => {
  it("shows production source and version", () => {
    render(createElement(PlaybookInfoScreen, { playbook: playbook(), onBack: () => undefined }));

    expect(screen.getByText("Production source")).toBeInTheDocument();
    expect(screen.getByText("published")).toBeInTheDocument();
    expect(screen.getByText("Production version")).toBeInTheDocument();
    expect(screen.getByText("1@k9f4p2x8m1qd")).toBeInTheDocument();
    expect(screen.getByText("Production change")).toBeInTheDocument();
    expect(screen.getByText("Adjusted opening blocking.")).toBeInTheDocument();
    expect(screen.getByText("Blocking changes")).toBeInTheDocument();
    expect(screen.getByText("I-1:b1")).toBeInTheDocument();
  });

  it("warns when a Playbook was built from a working source", () => {
    render(
      createElement(PlaybookInfoScreen, {
        playbook: { ...playbook(), production: { source: "working", version: "1@draft" } },
        onBack: () => undefined
      })
    );

    expect(screen.getByText("Production warning")).toBeInTheDocument();
    expect(screen.getByText(/unpublished working production/)).toBeInTheDocument();
  });
});

function playbook(): Playbook {
  return {
    id: "androcles",
    title: "Androcles and the Lion",
    authors: ["George Bernard Shaw"],
    production: {
      source: "published",
      version: "1@k9f4p2x8m1qd",
      sequence: 1,
      publicationId: "k9f4p2x8m1qd",
      publishedAt: "2026-05-10T13:00:00Z",
      changeSummary: "Adjusted opening blocking.",
      blockingChanges: ["I-1:b1"]
    },
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: []
  };
}
