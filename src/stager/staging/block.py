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
        self._add_stage_command(subparsers)
        self._add_set_command(subparsers)
        self._add_scene_command(subparsers)
        self._add_beat_command(subparsers)
        self._add_render_command(subparsers)
        self._add_icons_command(subparsers)
        args = parser.parse_args()
        args.handler(args)

    def _add_stage_command(self, subparsers) -> None:
        parser = subparsers.add_parser("stage", help="Render a stage-only diagram.")
        parser.add_argument("input", type=Path, help="Blocking file / stage file")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.add_argument("--json-out", type=Path, help="Optional normalized stage JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._stage)

    def _add_render_command(self, subparsers) -> None:
        parser = subparsers.add_parser("render", help="Render a scene or beat diagram. Transitional alias for scene/beat.")
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

    def _add_set_command(self, subparsers) -> None:
        parser = subparsers.add_parser("set", help="Render a set-only diagram.")
        parser.add_argument("input", type=Path, help="Blocking file / stage file")
        parser.add_argument("--set", required=True, dest="set_id", help="Set/setup id to render")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.add_argument("--json-out", type=Path, help="Optional normalized set JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._set)

    def _add_scene_command(self, subparsers) -> None:
        parser = subparsers.add_parser("scene", help="Render a scene snapshot diagram.")
        parser.add_argument("input", type=Path, help="Blocking file / stage file")
        parser.add_argument("--scene", required=True, help="Scene snapshot id to render")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.add_argument("--json-out", type=Path, help="Optional normalized scene JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._scene)

    def _add_beat_command(self, subparsers) -> None:
        parser = subparsers.add_parser("beat", help="Render a point-in-time beat diagram.")
        parser.add_argument("input", type=Path, help="Blocking file / stage file")
        parser.add_argument("--scene", required=True, help="Scene snapshot id to render")
        parser.add_argument("--beat", required=True, help="Blocking beat id to apply up to")
        parser.add_argument("--out", type=Path, required=True, help="Output SVG path")
        parser.add_argument("--json-out", type=Path, help="Optional normalized beat JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._beat)

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
        self._write_snapshot(args, snapshot)

    def _set(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_set(document, args.set_id)
        self._write_snapshot(args, snapshot)

    def _scene(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_snapshot(document, args.scene)
        self._write_snapshot(args, snapshot)

    def _beat(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingStateResolver().resolve_beat(document, args.scene, args.beat)
        self._write_snapshot(args, snapshot)

    def _stage(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_stage(document)
        self._write_snapshot(args, snapshot)

    def _write_snapshot(self, args, snapshot) -> None:
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
