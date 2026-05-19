import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { DiagramState } from "../../src/staging/diagramTypes";
import { BlockingDiagram } from "../../src/ui/components/BlockingDiagram";

describe("BlockingDiagram", () => {
  afterEach(() => cleanup());

  it("uses packaged icon symbols for set pieces and props", () => {
    const { container } = render(
      <BlockingDiagram
        state={diagramState()}
        iconLibrarySvg={'<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"></symbol><symbol id="stage-icon-sword" viewBox="0 0 24 24"></symbol></defs>'}
      />
    );

    expect(container.querySelector('use[href="#stage-icon-table"]')).toBeInTheDocument();
    expect(container.querySelector('use[href="#stage-icon-sword"]')).toBeInTheDocument();
  });

  it("places a single prop at the center of its set piece", () => {
    const { container } = render(
      <BlockingDiagram
        state={diagramState()}
        iconLibrarySvg={'<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"></symbol><symbol id="stage-icon-sword" viewBox="0 0 24 24"></symbol></defs>'}
      />
    );

    expect(container.querySelector(".blocking-entity-prop use")).toHaveAttribute("x", "-0.675");
    expect(container.querySelector(".blocking-entity-prop")?.getAttribute("transform")).toEqual(
      container.querySelector(".blocking-set-piece")?.getAttribute("transform")
    );
  });

  it("offsets multiple props that are placed on the same set piece", () => {
    const { container } = render(
      <BlockingDiagram
        state={diagramStateWithMultipleProps()}
        iconLibrarySvg={
          '<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"></symbol><symbol id="stage-icon-sword" viewBox="0 0 24 24"></symbol><symbol id="stage-icon-dagger" viewBox="0 0 24 24"></symbol></defs>'
        }
      />
    );

    const transforms = [...container.querySelectorAll(".blocking-entity-prop")].map((element) =>
      element.getAttribute("transform")
    );
    expect(new Set(transforms).size).toBe(2);
  });

  it("falls back to generic prop shapes when the icon library is unavailable", () => {
    const { container } = render(<BlockingDiagram state={diagramState()} />);

    expect(container.querySelector('use[href="#stage-icon-sword"]')).not.toBeInTheDocument();
    expect(container.querySelector(".blocking-entity-prop path")).toBeInTheDocument();
  });
});

function diagramState(): DiagramState {
  return {
    format: "quince.blocking.diagram_state",
    format_version: "1.0.0",
    diagram_id: "scene:P:b1",
    scene_id: "P",
    beat_id: "b1",
    stage: { width: 30, depth: 20 },
    areas: [],
    set_pieces: [
      {
        id: "set_piece:table",
        source_id: "table",
        kind: "set_piece",
        title: "table",
        icon: "table",
        point: { x: 0, y: 10 },
        size: { width: 4, depth: 3 }
      }
    ],
    entities: [
      {
        id: "prop:sword",
        kind: "prop",
        title: "sword",
        icon: "sword",
        point: { x: 0, y: 10 },
        source: "table",
        slot_index: 0
      }
    ],
    offstage: []
  };
}

function diagramStateWithMultipleProps(): DiagramState {
  return {
    ...diagramState(),
    entities: [
      ...(diagramState().entities ?? []),
      {
        id: "prop:dagger",
        kind: "prop",
        title: "dagger",
        icon: "dagger",
        point: { x: 0, y: 10 },
        source: "table",
        slot_index: 1
      }
    ]
  };
}
