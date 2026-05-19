from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_icons import StageSvgIconLibrary
from stager.staging.svg_renderer import StageSvgRenderer


@dataclass
class BlockCli:
    def main(self) -> None:
        parser = argparse.ArgumentParser(
            prog="block",
            description="Standalone staging/blocking tools.",
        )
        subparsers = parser.add_subparsers(dest="command", required=True)
        self._add_render_command(subparsers)
        self._add_icons_command(subparsers)
        args = parser.parse_args()
        args.handler(args)

    def _add_render_command(self, subparsers) -> None:
        parser = subparsers.add_parser("render", help="Render a point-in-time blocking diagram.")
        parser.add_argument("input", type=Path, help="Blocking file / stage file")
        parser.add_argument("--scene", required=True, help="Scene snapshot id to render")
        parser.add_argument("--beat", help="Optional blocking beat id to apply up to")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.add_argument("--json-out", type=Path, help="Optional normalized point-in-time JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._render)

    def _add_icons_command(self, subparsers) -> None:
        parser = subparsers.add_parser("icons", help="Render a browsable SVG icon catalog.")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.set_defaults(handler=self._icons)

    def _render(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        if args.beat is None:
            snapshot = StagingResolver().resolve_snapshot(document, args.scene)
        else:
            snapshot = StagingStateResolver().resolve_beat(document, args.scene, args.beat)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(StageSvgRenderer(orientation=args.orientation).render(snapshot), encoding="utf-8")
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")
        for diagnostic in snapshot.diagnostics:
            location = f"line {diagnostic.line_no}: " if diagnostic.line_no is not None else ""
            print(f"{diagnostic.severity}: {location}{diagnostic.message}")
        print(args.out)

    def _icons(self, args) -> None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(StageSvgIconLibrary().catalog_svg(), encoding="utf-8")
        print(args.out)


def main() -> None:
    BlockCli().main()


if __name__ == "__main__":
    main()
