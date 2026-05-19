from __future__ import annotations

from dataclasses import dataclass, field

from stager.staging.diagnostics import StagingDiagnostic


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float = 0.0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass(frozen=True)
class SourceLocation:
    source: str
    point: Point3D | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            **({"point": self.point.to_dict()} if self.point is not None else {}),
        }


@dataclass(frozen=True)
class StageDefinition:
    stage_type: str = "proscenium"
    width: float = 36.0
    depth: float = 24.0
    units: str = "ft"
    audience: str = "south"
    measured: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.stage_type,
            "width": self.width,
            "depth": self.depth,
            "units": self.units,
            "audience": self.audience,
            "measured": self.measured,
        }


@dataclass(frozen=True)
class AreaDefinition:
    id: str
    center: Point3D
    width: float
    depth: float
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "center": self.center.to_dict(),
            "width": self.width,
            "depth": self.depth,
            "aliases": list(self.aliases),
        }


@dataclass(frozen=True)
class ActorDefinition:
    id: str
    label: str
    name: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "name": self.name,
        }


@dataclass(frozen=True)
class AnchorDefinition:
    id: str
    at: SourceLocation
    kind: str = "mark"
    size: tuple[float, float] | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "at": self.at.to_dict(),
            **({"size": list(self.size)} if self.size is not None else {}),
        }


@dataclass(frozen=True)
class LevelDefinition:
    id: str
    z: float
    at: SourceLocation | None = None
    size: tuple[float, float] | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "z": self.z,
            **({"at": self.at.to_dict()} if self.at is not None else {}),
            **({"size": list(self.size)} if self.size is not None else {}),
        }


@dataclass(frozen=True)
class ConnectorDefinition:
    id: str
    kind: str
    start: SourceLocation
    end: SourceLocation

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "from": self.start.to_dict(),
            "to": self.end.to_dict(),
        }


@dataclass(frozen=True)
class SetPieceDefinition:
    id: str
    at: SourceLocation
    kind: str = "set"
    size: tuple[float, float] | None = None
    fixed: bool = False
    movable: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "at": self.at.to_dict(),
            "fixed": self.fixed,
            "movable": self.movable,
            **({"size": list(self.size)} if self.size is not None else {}),
        }


@dataclass(frozen=True)
class PropDefinition:
    id: str
    preset: SourceLocation

    def to_dict(self) -> dict:
        return {"id": self.id, "preset": self.preset.to_dict()}


@dataclass(frozen=True)
class ScenicSetDefinition:
    id: str
    anchors: dict[str, AnchorDefinition] = field(default_factory=dict)
    levels: dict[str, LevelDefinition] = field(default_factory=dict)
    connectors: dict[str, ConnectorDefinition] = field(default_factory=dict)
    set_pieces: dict[str, SetPieceDefinition] = field(default_factory=dict)
    props: dict[str, PropDefinition] = field(default_factory=dict)
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "anchors": {key: value.to_dict() for key, value in sorted(self.anchors.items())},
            "levels": {key: value.to_dict() for key, value in sorted(self.levels.items())},
            "connectors": {key: value.to_dict() for key, value in sorted(self.connectors.items())},
            "set_pieces": {key: value.to_dict() for key, value in sorted(self.set_pieces.items())},
            "props": {key: value.to_dict() for key, value in sorted(self.props.items())},
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class Placement:
    entity: str
    location: SourceLocation | None = None
    face: str | None = None
    offstage: bool = False
    via: str | None = None
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "offstage": self.offstage,
            **({"location": self.location.to_dict()} if self.location is not None else {}),
            **({"face": self.face} if self.face is not None else {}),
            **({"via": self.via} if self.via is not None else {}),
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class SceneSnapshot:
    scene_id: str
    placements: tuple[Placement, ...]
    set_id: str = "default"
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "set_id": self.set_id,
            "placements": [placement.to_dict() for placement in self.placements],
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class BlockingBeat:
    beat_id: str
    scene_id: str
    placements: tuple[Placement, ...]
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "beat_id": self.beat_id,
            "scene_id": self.scene_id,
            "placements": [placement.to_dict() for placement in self.placements],
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class StagingDocument:
    stage: StageDefinition = field(default_factory=StageDefinition)
    grid_standard: int | None = 9
    actors: dict[str, ActorDefinition] = field(default_factory=dict)
    sets: dict[str, ScenicSetDefinition] = field(default_factory=dict)
    snapshots: dict[str, SceneSnapshot] = field(default_factory=dict)
    beats: tuple[BlockingBeat, ...] = ()
    diagnostics: tuple[StagingDiagnostic, ...] = ()

    @property
    def anchors(self) -> dict[str, AnchorDefinition]:
        return self.sets.get("default", ScenicSetDefinition("default")).anchors

    @property
    def levels(self) -> dict[str, LevelDefinition]:
        return self.sets.get("default", ScenicSetDefinition("default")).levels

    @property
    def connectors(self) -> dict[str, ConnectorDefinition]:
        return self.sets.get("default", ScenicSetDefinition("default")).connectors

    @property
    def set_pieces(self) -> dict[str, SetPieceDefinition]:
        return self.sets.get("default", ScenicSetDefinition("default")).set_pieces

    @property
    def props(self) -> dict[str, PropDefinition]:
        return self.sets.get("default", ScenicSetDefinition("default")).props

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.to_dict(),
            "grid_standard": self.grid_standard,
            "actors": {key: value.to_dict() for key, value in sorted(self.actors.items())},
            "sets": {key: value.to_dict() for key, value in sorted(self.sets.items())},
            "snapshots": {key: value.to_dict() for key, value in sorted(self.snapshots.items())},
            "beats": [beat.to_dict() for beat in self.beats],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True)
class ResolvedPlacement:
    entity: str
    kind: str
    source: str
    point: Point3D | None = None
    face: str | None = None
    offstage: bool = False
    via: str | None = None
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "kind": self.kind,
            "source": self.source,
            "offstage": self.offstage,
            **({"point": self.point.to_dict()} if self.point is not None else {}),
            **({"face": self.face} if self.face is not None else {}),
            **({"via": self.via} if self.via is not None else {}),
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class ResolvedSnapshot:
    scene_id: str
    stage: StageDefinition
    areas: dict[str, AreaDefinition]
    set_id: str | None
    anchors: dict[str, AnchorDefinition]
    actors: dict[str, ActorDefinition]
    connectors: dict[str, ConnectorDefinition]
    levels: dict[str, LevelDefinition]
    set_pieces: dict[str, SetPieceDefinition]
    placements: tuple[ResolvedPlacement, ...]
    diagnostics: tuple[StagingDiagnostic, ...] = ()

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "set_id": self.set_id,
            "stage": self.stage.to_dict(),
            "areas": {key: value.to_dict() for key, value in sorted(self.areas.items())},
            "anchors": {key: value.to_dict() for key, value in sorted(self.anchors.items())},
            "actors": {key: value.to_dict() for key, value in sorted(self.actors.items())},
            "connectors": {key: value.to_dict() for key, value in sorted(self.connectors.items())},
            "levels": {key: value.to_dict() for key, value in sorted(self.levels.items())},
            "set_pieces": {key: value.to_dict() for key, value in sorted(self.set_pieces.items())},
            "placements": [placement.to_dict() for placement in self.placements],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
