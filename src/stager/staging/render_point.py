from __future__ import annotations

import argparse
import json
from pathlib import Path

from stager.shared import paths
from stager.staging.diagram_state_builder import DiagramStateBuilder
from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_renderer import StageSvgRenderer


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a point-in-time stage snapshot to SVG.")
    parser.add_argument("input", type=Path, help="Stage description text file")
    parser.add_argument("--scene", required=True, help="Scene snapshot id to render")
    parser.add_argument("--beat", help="Optional beat id. Applies scene blocking beats up to and including this beat.")
    parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
    parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
    parser.add_argument(
        "--orientation",
        choices=("portrait", "landscape"),
        default="portrait",
        help="SVG orientation. Portrait puts downstage to the right and is the default.",
    )
    args = parser.parse_args()

    document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
    if args.beat is None:
        snapshot = StagingResolver().resolve_snapshot(document, args.scene)
    else:
        snapshot = StagingStateResolver().resolve_beat(document, args.scene, args.beat)
    diagram = DiagramStateBuilder().build(snapshot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(StageSvgRenderer(orientation=args.orientation).render(diagram), encoding="utf-8")
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(diagram.to_dict(), indent=2) + "\n", encoding="utf-8")
    for diagnostic in snapshot.diagnostics:
        location = f"line {diagnostic.line_no}: " if diagnostic.line_no is not None else ""
        print(f"{diagnostic.severity}: {location}{diagnostic.message}")
    print(paths.display_path(args.out))


if __name__ == "__main__":
    main()
