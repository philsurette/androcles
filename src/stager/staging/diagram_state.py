from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from stager.staging.model import Point3D


DiagramKind = Literal["stage", "set", "scene", "beat"]


@dataclass(frozen=True)
class DiagramStage:
    stage_type: str
    width: float
    depth: float
    units: str
    audience: str
    measured: bool

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
class DiagramArea:
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
class DiagramLevel:
    id: str
    point: Point3D
    width: float
    depth: float
    title: str
    label: str | None = None
    elevation: str = "deck"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "point": self.point.to_dict(),
            "width": self.width,
            "depth": self.depth,
            "title": self.title,
            "elevation": self.elevation,
            **({"label": self.label} if self.label is not None else {}),
        }


@dataclass(frozen=True)
class DiagramConnector:
    id: str
    kind: str
    start: Point3D
    end: Point3D
    title: str
    label: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "from": self.start.to_dict(),
            "to": self.end.to_dict(),
            "title": self.title,
            **({"label": self.label} if self.label is not None else {}),
        }


@dataclass(frozen=True)
class DiagramAnchor:
    id: str
    point: Point3D
    kind: str
    title: str
    elevation: str = "deck"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "point": self.point.to_dict(),
            "kind": self.kind,
            "title": self.title,
            "elevation": self.elevation,
        }


@dataclass(frozen=True)
class DiagramSize:
    width: float
    depth: float

    def to_dict(self) -> dict:
        return {"width": self.width, "depth": self.depth}


@dataclass(frozen=True)
class DiagramOffset:
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class DiagramEntity:
    id: str
    source_id: str
    kind: str
    layer: str
    point: Point3D | None
    source: str
    title: str
    movement_from: Point3D | None = None
    movement_from_source: str | None = None
    movement_to: Point3D | None = None
    movement_to_source: str | None = None
    visible: bool = True
    label: str | None = None
    icon: str | None = None
    face: str | None = None
    elevation: str = "deck"
    size: DiagramSize | None = None
    fixed: bool = False
    movable: bool = False
    offset: DiagramOffset = field(default_factory=DiagramOffset)
    slot_index: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "kind": self.kind,
            "layer": self.layer,
            "source": self.source,
            "title": self.title,
            "visible": self.visible,
            "elevation": self.elevation,
            "fixed": self.fixed,
            "movable": self.movable,
            **({"point": self.point.to_dict()} if self.point is not None else {}),
            **({"movement_from": self.movement_from.to_dict()} if self.movement_from is not None else {}),
            **({"movement_from_source": self.movement_from_source} if self.movement_from_source is not None else {}),
            **({"movement_to": self.movement_to.to_dict()} if self.movement_to is not None else {}),
            **({"movement_to_source": self.movement_to_source} if self.movement_to_source is not None else {}),
            **({"label": self.label} if self.label is not None else {}),
            **({"icon": self.icon} if self.icon is not None else {}),
            **({"face": self.face} if self.face is not None else {}),
            **({"size": self.size.to_dict()} if self.size is not None else {}),
            **({"offset": self.offset.to_dict()} if self.offset != DiagramOffset() else {}),
            **({"slot_index": self.slot_index} if self.slot_index is not None else {}),
        }


@dataclass(frozen=True)
class DiagramOffstageEntity:
    id: str
    source_id: str
    kind: str
    source: str
    via: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "kind": self.kind,
            "source": self.source,
            **({"via": self.via} if self.via is not None else {}),
        }


@dataclass(frozen=True)
class DiagramDiagnostic:
    severity: str
    message: str
    line_no: int | None = None

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "message": self.message,
            **({"line_no": self.line_no} if self.line_no is not None else {}),
        }


@dataclass(frozen=True)
class DiagramState:
    diagram_id: str
    diagram_kind: DiagramKind
    stage: DiagramStage
    areas: tuple[DiagramArea, ...] = ()
    levels: tuple[DiagramLevel, ...] = ()
    connectors: tuple[DiagramConnector, ...] = ()
    anchors: tuple[DiagramAnchor, ...] = ()
    set_pieces: tuple[DiagramEntity, ...] = ()
    entities: tuple[DiagramEntity, ...] = ()
    offstage: tuple[DiagramOffstageEntity, ...] = ()
    diagnostics: tuple[DiagramDiagnostic, ...] = ()
    scene_id: str | None = None
    beat_id: str | None = None
    set_id: str | None = None
    format: str = "quince.blocking.diagram_state"
    format_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "format_version": self.format_version,
            "diagram_id": self.diagram_id,
            "diagram_kind": self.diagram_kind,
            **({"scene_id": self.scene_id} if self.scene_id is not None else {}),
            **({"beat_id": self.beat_id} if self.beat_id is not None else {}),
            **({"set_id": self.set_id} if self.set_id is not None else {}),
            "stage": self.stage.to_dict(),
            "areas": [area.to_dict() for area in self.areas],
            "levels": [level.to_dict() for level in self.levels],
            "connectors": [connector.to_dict() for connector in self.connectors],
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "set_pieces": [entity.to_dict() for entity in self.set_pieces],
            "entities": [entity.to_dict() for entity in self.entities],
            "offstage": [entity.to_dict() for entity in self.offstage],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
