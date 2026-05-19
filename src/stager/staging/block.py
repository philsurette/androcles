from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import re

from stager.shared import paths
from stager.staging.diagram_state_builder import DiagramStateBuilder
from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_icons import StageSvgIconLibrary
from stager.staging.svg_renderer import StageSvgRenderer


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STAGING_FILE = Path("staging.txt")


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
        parser.add_argument(
            "input",
            type=Path,
            nargs="?",
            default=DEFAULT_STAGING_FILE,
            help="Staging file. Defaults to staging.txt.",
        )
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/<play>/staging/stage.svg.")
        parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._stage)

    def _add_render_command(self, subparsers) -> None:
        parser = subparsers.add_parser("render", help="Render a scene or beat diagram. Transitional alias for scene/beat.")
        parser.add_argument(
            "input",
            type=Path,
            nargs="?",
            default=DEFAULT_STAGING_FILE,
            help="Staging file. Defaults to staging.txt.",
        )
        parser.add_argument("--scene", required=True, help="Scene snapshot id to render")
        parser.add_argument("--beat", help="Optional blocking beat id to apply up to")
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/<play>/staging/scene-<scene>[-<beat>].svg.")
        parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._render)

    def _add_set_command(self, subparsers) -> None:
        parser = subparsers.add_parser("set", help="Render a set-only diagram.")
        parser.add_argument(
            "set_arg",
            nargs="?",
            metavar="SET_ID",
            help="Set/setup id. If --set is used, this may be the staging file.",
        )
        parser.add_argument("input", type=Path, nargs="?", help="Staging file. Defaults to staging.txt.")
        parser.add_argument("--set", dest="set_id", help="Set/setup id to render")
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/<play>/staging/set-<set>.svg.")
        parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._set)

    def _add_scene_command(self, subparsers) -> None:
        parser = subparsers.add_parser("scene", help="Render a scene snapshot diagram.")
        parser.add_argument(
            "scene_arg",
            nargs="?",
            metavar="SCENE_ID",
            help="Scene snapshot id. If --scene is used, this may be the staging file.",
        )
        parser.add_argument("input", type=Path, nargs="?", help="Staging file. Defaults to staging.txt.")
        parser.add_argument("--scene", help="Scene snapshot id to render")
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/<play>/staging/scene-<scene>.svg.")
        parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._scene)

    def _add_beat_command(self, subparsers) -> None:
        parser = subparsers.add_parser("beat", help="Render a point-in-time beat diagram.")
        parser.add_argument(
            "scene_arg",
            nargs="?",
            metavar="SCENE_ID",
            help="Scene snapshot id. If --scene is used, this may be the staging file.",
        )
        parser.add_argument("beat_arg", nargs="?", metavar="BEAT_ID", help="Blocking beat id to apply up to.")
        parser.add_argument("input", type=Path, nargs="?", help="Staging file. Defaults to staging.txt.")
        parser.add_argument("--scene", help="Scene snapshot id to render")
        parser.add_argument("--beat", help="Blocking beat id to apply up to")
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/<play>/staging/scene-<scene>-<beat>.svg.")
        parser.add_argument("--json-out", type=Path, help="Optional diagram-state JSON output path")
        parser.add_argument(
            "--orientation",
            choices=("portrait", "landscape"),
            default="portrait",
            help="Diagram orientation. Portrait puts downstage to the right and is the default.",
        )
        parser.set_defaults(handler=self._beat)

    def _add_icons_command(self, subparsers) -> None:
        parser = subparsers.add_parser("icons", help="Render a browsable SVG icon catalog.")
        parser.add_argument("--out", type=Path, help="Output SVG path. Defaults to build/staging/block-icon-library.svg.")
        parser.set_defaults(handler=self._icons)

    def _render(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        if args.beat is None:
            snapshot = StagingResolver().resolve_snapshot(document, args.scene)
        else:
            snapshot = StagingStateResolver().resolve_beat(document, args.scene, args.beat)
        self._write_snapshot(args, snapshot)

    def _set(self, args) -> None:
        set_id, input_path = self._resolve_set_args(args)
        args.input = input_path
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_set(document, set_id)
        self._write_snapshot(args, snapshot)

    def _scene(self, args) -> None:
        scene_id, input_path = self._resolve_scene_args(args)
        args.input = input_path
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_snapshot(document, scene_id)
        self._write_snapshot(args, snapshot)

    def _beat(self, args) -> None:
        scene_id, beat_id, input_path = self._resolve_beat_args(args)
        args.input = input_path
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingStateResolver().resolve_beat(document, scene_id, beat_id)
        self._write_snapshot(args, snapshot)

    def _stage(self, args) -> None:
        document = StagingParser().parse(args.input.read_text(encoding="utf-8"))
        snapshot = StagingResolver().resolve_stage(document)
        self._write_snapshot(args, snapshot)

    def _write_snapshot(self, args, snapshot) -> None:
        diagram = DiagramStateBuilder().build(snapshot)
        output_path = args.out or self._default_diagram_output(args.input, diagram)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(StageSvgRenderer(orientation=args.orientation).render(diagram), encoding="utf-8")
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(diagram.to_dict(), indent=2) + "\n", encoding="utf-8")
        for diagnostic in snapshot.diagnostics:
            location = f"line {diagnostic.line_no}: " if diagnostic.line_no is not None else ""
            print(f"{diagnostic.severity}: {location}{diagnostic.message}")
        print(paths.display_path(output_path))

    def _icons(self, args) -> None:
        output_path = args.out or REPO_ROOT / "build" / "staging" / "block-icon-library.svg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(StageSvgIconLibrary().catalog_svg(), encoding="utf-8")
        print(paths.display_path(output_path))

    def _default_diagram_output(self, input_path: Path, diagram) -> Path:
        return self._default_output_dir(input_path) / self._default_diagram_filename(diagram)

    def _default_output_dir(self, input_path: Path) -> Path:
        resolved = input_path.resolve()
        parts = resolved.parts
        if "plays" in parts:
            plays_index = parts.index("plays")
            if plays_index + 1 < len(parts):
                repo_root = Path(*parts[:plays_index])
                play_id = parts[plays_index + 1]
                return repo_root / "build" / play_id / "staging"
        return REPO_ROOT / "build" / input_path.stem / "staging"

    def _default_diagram_filename(self, diagram) -> str:
        if diagram.diagram_kind == "stage":
            return "stage.svg"
        if diagram.diagram_kind == "set":
            return f"set-{self._path_id(diagram.set_id or 'default')}.svg"
        if diagram.diagram_kind == "beat":
            return f"scene-{self._path_id(diagram.scene_id or 'scene')}-{self._path_id(diagram.beat_id or 'beat')}.svg"
        return f"scene-{self._path_id(diagram.scene_id or diagram.diagram_id)}.svg"

    def _path_id(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")

    def _resolve_set_args(self, args) -> tuple[str, Path]:
        if args.set_id is not None:
            return args.set_id, Path(args.set_arg) if args.set_arg is not None else DEFAULT_STAGING_FILE
        if args.set_arg is None:
            raise SystemExit("block set requires a set id, for example: block set act1")
        return str(args.set_arg), args.input or DEFAULT_STAGING_FILE

    def _resolve_scene_args(self, args) -> tuple[str, Path]:
        if args.scene is not None:
            return args.scene, Path(args.scene_arg) if args.scene_arg is not None else DEFAULT_STAGING_FILE
        if args.scene_arg is None:
            raise SystemExit("block scene requires a scene id, for example: block scene 1.3")
        return str(args.scene_arg), args.input or DEFAULT_STAGING_FILE

    def _resolve_beat_args(self, args) -> tuple[str, str, Path]:
        if args.scene is not None:
            if args.beat is None:
                raise SystemExit("block beat requires a beat id, for example: block beat --scene 1.3 --beat b2")
            return args.scene, args.beat, Path(args.scene_arg) if args.scene_arg is not None else DEFAULT_STAGING_FILE
        if args.scene_arg is None or args.beat_arg is None:
            raise SystemExit("block beat requires a scene id and beat id, for example: block beat 1.3 b2")
        return str(args.scene_arg), str(args.beat_arg), args.input or DEFAULT_STAGING_FILE


def main() -> None:
    BlockCli().main()


if __name__ == "__main__":
    main()
