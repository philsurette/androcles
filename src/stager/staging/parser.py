from __future__ import annotations

from dataclasses import dataclass, field
import re
import shlex

from stager.staging.diagnostics import StagingDiagnostic
from stager.staging.model import (
    AnchorDefinition,
    ConnectorDefinition,
    LevelDefinition,
    Placement,
    Point3D,
    PropDefinition,
    SceneSnapshot,
    SetPieceDefinition,
    SourceLocation,
    StageDefinition,
    StagingDocument,
)


COORD_RE = re.compile(r"^\((-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:,(-?\d+(?:\.\d+)?))?\)$")
SIZE_RE = re.compile(r"^\((-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\)$")
SCENE_SNAPSHOT_RE = re.compile(r"^scene\s+(\S+)\s+snapshot$")


@dataclass
class StagingParser:
    diagnostics: list[StagingDiagnostic] = field(default_factory=list)

    def parse(self, text: str) -> StagingDocument:
        self.diagnostics = []
        stage = StageDefinition()
        grid_standard: int | None = 9
        anchors: dict[str, AnchorDefinition] = {}
        levels: dict[str, LevelDefinition] = {}
        connectors: dict[str, ConnectorDefinition] = {}
        set_pieces: dict[str, SetPieceDefinition] = {}
        props: dict[str, PropDefinition] = {}
        snapshots: dict[str, SceneSnapshot] = {}
        current_scene: str | None = None
        current_snapshot_line: int | None = None
        current_placements: list[Placement] = []

        def flush_snapshot() -> None:
            nonlocal current_scene, current_snapshot_line, current_placements
            if current_scene is None:
                return
            snapshots[current_scene] = SceneSnapshot(
                scene_id=current_scene,
                placements=tuple(current_placements),
                line_no=current_snapshot_line,
            )
            current_scene = None
            current_snapshot_line = None
            current_placements = []

        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue
            scene_match = SCENE_SNAPSHOT_RE.match(line)
            if scene_match:
                flush_snapshot()
                current_scene = scene_match.group(1)
                current_snapshot_line = line_no
                continue
            if current_scene is not None and self._looks_like_placement(line):
                current_placements.append(self._parse_placement(line, line_no))
                continue
            flush_snapshot()
            tokens = self._tokens(line, line_no)
            if not tokens:
                continue
            keyword = tokens[0]
            fields = self._fields(tokens[1:])
            try:
                if keyword == "stage":
                    stage = self._parse_stage(fields)
                elif keyword == "grid":
                    grid_standard = int(fields.get("standard", "9"))
                elif keyword == "anchor":
                    anchor = self._parse_anchor(tokens, fields, line_no)
                    if anchor is not None:
                        self._put_unique(anchors, anchor.id, anchor, "anchor", line_no)
                elif keyword == "set":
                    set_piece = self._parse_set_piece(tokens, fields, line_no)
                    if set_piece is not None:
                        self._put_unique(set_pieces, set_piece.id, set_piece, "set piece", line_no)
                elif keyword == "prop":
                    prop = self._parse_prop(tokens, fields, line_no)
                    if prop is not None:
                        self._put_unique(props, prop.id, prop, "prop", line_no)
                elif keyword == "level":
                    level = self._parse_level(tokens, fields, line_no)
                    if level is not None:
                        self._put_unique(levels, level.id, level, "level", line_no)
                elif keyword in ("stair", "ramp", "lift"):
                    connector = self._parse_connector(keyword, tokens, fields, line_no)
                    if connector is not None:
                        self._put_unique(connectors, connector.id, connector, "connector", line_no)
                else:
                    self._warn(f"Unknown staging statement: {keyword}", line_no)
            except ValueError as exc:
                self._warn(str(exc), line_no)
        flush_snapshot()
        return StagingDocument(
            stage=stage,
            grid_standard=grid_standard,
            anchors=anchors,
            levels=levels,
            connectors=connectors,
            set_pieces=set_pieces,
            props=props,
            snapshots=snapshots,
            diagnostics=tuple(self.diagnostics),
        )

    def _parse_stage(self, fields: dict[str, str]) -> StageDefinition:
        width = self._float(fields.get("width"), default=36.0)
        depth = self._float(fields.get("depth"), default=24.0)
        measured = "width" in fields or "depth" in fields
        return StageDefinition(
            stage_type=fields.get("type", "proscenium"),
            width=width,
            depth=depth,
            units=fields.get("units", "ft"),
            audience=fields.get("audience", "south"),
            measured=measured,
        )

    def _parse_anchor(self, tokens: list[str], fields: dict[str, str], line_no: int) -> AnchorDefinition | None:
        if len(tokens) < 2:
            self._warn("Anchor statement requires an id", line_no)
            return None
        anchor_id = tokens[1]
        if len(tokens) >= 4 and tokens[2] == "=":
            at = self._source_location(tokens[3])
        else:
            at = self._source_location(fields.get("at"))
        return AnchorDefinition(
            id=anchor_id,
            at=at,
            kind=fields.get("kind", "mark"),
            size=self._size(fields.get("size")),
        )

    def _parse_set_piece(self, tokens: list[str], fields: dict[str, str], line_no: int) -> SetPieceDefinition | None:
        if len(tokens) < 2:
            self._warn("Set statement requires an id", line_no)
            return None
        return SetPieceDefinition(
            id=tokens[1],
            at=self._source_location(fields.get("at")),
            kind=fields.get("kind", "set"),
            size=self._size(fields.get("size")),
            fixed=self._bool(fields.get("fixed")),
            movable=self._bool(fields.get("movable")),
        )

    def _parse_prop(self, tokens: list[str], fields: dict[str, str], line_no: int) -> PropDefinition | None:
        if len(tokens) < 2:
            self._warn("Prop statement requires an id", line_no)
            return None
        return PropDefinition(
            id=tokens[1],
            preset=self._source_location(fields.get("preset") or fields.get("at")),
        )

    def _parse_level(self, tokens: list[str], fields: dict[str, str], line_no: int) -> LevelDefinition | None:
        if len(tokens) < 2:
            self._warn("Level statement requires an id", line_no)
            return None
        return LevelDefinition(id=tokens[1], z=self._float(fields.get("z"), default=0.0))

    def _parse_connector(
        self,
        kind: str,
        tokens: list[str],
        fields: dict[str, str],
        line_no: int,
    ) -> ConnectorDefinition | None:
        if len(tokens) < 2:
            self._warn(f"{kind} statement requires an id", line_no)
            return None
        return ConnectorDefinition(
            id=tokens[1],
            kind=kind,
            start=self._source_location(fields.get("from")),
            end=self._source_location(fields.get("to")),
        )

    def _parse_placement(self, line: str, line_no: int) -> Placement:
        tokens = self._tokens(line, line_no)
        fields = self._fields(tokens[2:])
        if len(tokens) >= 3 and tokens[1] == "@":
            return Placement(
                entity=tokens[0],
                location=self._source_location(tokens[2]),
                face=fields.get("face"),
                line_no=line_no,
            )
        if len(tokens) >= 2 and tokens[1] == "offstage":
            return Placement(
                entity=tokens[0],
                offstage=True,
                via=fields.get("via"),
                line_no=line_no,
            )
        self._warn(f"Malformed placement: {line}", line_no)
        return Placement(entity=tokens[0] if tokens else "unknown", offstage=True, line_no=line_no)

    def _looks_like_placement(self, line: str) -> bool:
        tokens = line.split()
        return len(tokens) >= 2 and (tokens[1] == "@" or tokens[1] == "offstage")

    def _tokens(self, line: str, line_no: int) -> list[str]:
        try:
            return shlex.split(line)
        except ValueError as exc:
            self._warn(f"Malformed staging line: {exc}", line_no)
            return []

    def _fields(self, tokens: list[str]) -> dict[str, str]:
        fields = {}
        for token in tokens:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            fields[key] = value
        return fields

    def _source_location(self, value: str | None) -> SourceLocation:
        if value is None or not value.strip():
            raise ValueError("Missing location reference")
        value = value.strip()
        return SourceLocation(source=value, point=self._point(value))

    def _point(self, value: str) -> Point3D | None:
        match = COORD_RE.match(value)
        if match is None:
            return None
        return Point3D(
            x=float(match.group(1)),
            y=float(match.group(2)),
            z=float(match.group(3) or 0.0),
        )

    def _size(self, value: str | None) -> tuple[float, float] | None:
        if value is None:
            return None
        match = SIZE_RE.match(value)
        if match is None:
            return None
        return (float(match.group(1)), float(match.group(2)))

    def _float(self, value: str | None, *, default: float) -> float:
        if value is None:
            return default
        return float(value)

    def _bool(self, value: str | None) -> bool:
        return value in ("true", "yes", "1")

    def _put_unique(self, target: dict, key: str, value, label: str, line_no: int) -> None:
        if key in target:
            self._warn(f"Duplicate {label} id {key!r}", line_no)
            return
        target[key] = value

    def _strip_comment(self, line: str) -> str:
        return line.split("#", 1)[0]

    def _warn(self, message: str, line_no: int | None = None) -> None:
        self.diagnostics.append(StagingDiagnostic(severity="warning", message=message, line_no=line_no))
