from __future__ import annotations

from dataclasses import dataclass, replace

from stager.staging.diagnostics import StagingDiagnostic
from stager.staging.model import (
    AnchorDefinition,
    AreaDefinition,
    ConnectorDefinition,
    LevelDefinition,
    Point3D,
    ResolvedPlacement,
    ResolvedSnapshot,
    ScenicSetDefinition,
    SetPieceDefinition,
    SourceLocation,
    StagingDocument,
)


AREA_ALIASES = {
    "USL": "UL",
    "USC": "UC",
    "USR": "UR",
    "CSL": "CL",
    "CSC": "C",
    "CSR": "CR",
    "DSL": "DL",
    "DSC": "DC",
    "DSR": "DR",
}


@dataclass
class StagingResolver:
    def resolve_stage(self, document: StagingDocument) -> ResolvedSnapshot:
        diagnostics = list(document.diagnostics)
        areas = self._areas(document)
        return ResolvedSnapshot(
            scene_id="stage",
            stage=document.stage,
            areas=areas,
            set_id=None,
            anchors={},
            actors=document.actors,
            connectors={},
            levels={},
            set_pieces={},
            placements=(),
            diagnostics=tuple(diagnostics),
        )

    def resolve_set(self, document: StagingDocument, set_id: str) -> ResolvedSnapshot:
        diagnostics = list(document.diagnostics)
        areas = self._areas(document)
        scenic_set = self._scenic_set(document, set_id, diagnostics)
        return ResolvedSnapshot(
            scene_id=f"set:{set_id}",
            stage=document.stage,
            areas=areas,
            set_id=set_id,
            anchors=self._resolved_anchors(scenic_set, document, areas, diagnostics),
            actors=document.actors,
            connectors=self._resolved_connectors(scenic_set, document, areas, diagnostics),
            levels=self._resolved_levels(scenic_set, document, areas, diagnostics),
            set_pieces=self._resolved_set_pieces(scenic_set, document, areas, diagnostics),
            placements=(),
            diagnostics=tuple(diagnostics),
        )

    def resolve_snapshot(self, document: StagingDocument, scene_id: str) -> ResolvedSnapshot:
        diagnostics = list(document.diagnostics)
        areas = self._areas(document)
        snapshot = document.snapshots.get(scene_id)
        if snapshot is None:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown scene snapshot {scene_id!r}"))
            set_id = "default"
            scenic_set = self._scenic_set(document, set_id, diagnostics)
            placements = ()
        else:
            set_id = snapshot.set_id
            scenic_set = self._scenic_set(document, set_id, diagnostics)
            placements = tuple(self._resolve_placement(document, scenic_set, areas, placement, diagnostics) for placement in snapshot.placements)
        return ResolvedSnapshot(
            scene_id=scene_id,
            stage=document.stage,
            areas=areas,
            set_id=set_id,
            anchors=self._resolved_anchors(scenic_set, document, areas, diagnostics),
            actors=document.actors,
            connectors=self._resolved_connectors(scenic_set, document, areas, diagnostics),
            levels=self._resolved_levels(scenic_set, document, areas, diagnostics),
            set_pieces=self._resolved_set_pieces(scenic_set, document, areas, diagnostics),
            placements=placements,
            diagnostics=tuple(diagnostics),
        )

    def _scenic_set(
        self,
        document: StagingDocument,
        set_id: str,
        diagnostics: list[StagingDiagnostic],
    ) -> ScenicSetDefinition:
        scenic_set = document.sets.get(set_id)
        if scenic_set is not None:
            return scenic_set
        if set_id == "default":
            return ScenicSetDefinition(id=set_id)
        diagnostics.append(StagingDiagnostic("warning", f"Unknown set {set_id!r}"))
        return ScenicSetDefinition(id=set_id)

    def _areas(self, document: StagingDocument) -> dict[str, AreaDefinition]:
        if document.grid_standard != 9:
            return {}
        stage = document.stage
        col_width = stage.width / 3
        row_depth = stage.depth / 3
        x_positions = {
            "L": -stage.width / 3,
            "C": 0.0,
            "R": stage.width / 3,
        }
        y_positions = {
            "D": stage.depth / 6,
            "C": stage.depth / 2,
            "U": stage.depth * 5 / 6,
        }
        aliases_by_area = {}
        for alias, target in AREA_ALIASES.items():
            aliases_by_area.setdefault(target, []).append(alias)
        areas = {}
        for row in ("D", "C", "U"):
            for col in ("L", "C", "R"):
                area_id = "C" if row == "C" and col == "C" else row + col
                areas[area_id] = AreaDefinition(
                    id=area_id,
                    center=Point3D(x_positions[col], y_positions[row], 0.0),
                    width=col_width,
                    depth=row_depth,
                    aliases=tuple(sorted(aliases_by_area.get(area_id, []))),
                )
        return areas

    def _resolved_anchors(
        self,
        scenic_set: ScenicSetDefinition,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, AnchorDefinition]:
        return {
            key: replace(anchor, at=self._resolve_source(document, scenic_set, areas, anchor.at, diagnostics))
            for key, anchor in scenic_set.anchors.items()
        }

    def _resolved_set_pieces(
        self,
        scenic_set: ScenicSetDefinition,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, SetPieceDefinition]:
        return {
            key: replace(set_piece, at=self._resolve_source(document, scenic_set, areas, set_piece.at, diagnostics))
            for key, set_piece in scenic_set.set_pieces.items()
        }

    def _resolved_connectors(
        self,
        scenic_set: ScenicSetDefinition,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, ConnectorDefinition]:
        resolved = {}
        for key, connector in scenic_set.connectors.items():
            start = self._resolve_source(document, scenic_set, areas, connector.start, diagnostics)
            end = self._resolve_source(document, scenic_set, areas, connector.end, diagnostics)
            if start.point is None:
                diagnostics.append(StagingDiagnostic("warning", f"Unresolved connector start {connector.start.source!r} for {key}"))
            if end.point is None:
                diagnostics.append(StagingDiagnostic("warning", f"Unresolved connector end {connector.end.source!r} for {key}"))
            resolved[key] = replace(connector, start=start, end=end)
        return resolved

    def _resolved_levels(
        self,
        scenic_set: ScenicSetDefinition,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, LevelDefinition]:
        resolved = {}
        for key, level in scenic_set.levels.items():
            if level.at is None:
                resolved[key] = level
                continue
            at = self._resolve_source(document, scenic_set, areas, level.at, diagnostics)
            if at.point is None:
                diagnostics.append(StagingDiagnostic("warning", f"Unresolved level location {level.at.source!r} for {key}"))
            resolved[key] = replace(level, at=at)
        return resolved

    def _resolve_placement(
        self,
        document: StagingDocument,
        scenic_set: ScenicSetDefinition,
        areas: dict[str, AreaDefinition],
        placement,
        diagnostics: list[StagingDiagnostic],
    ) -> ResolvedPlacement:
        kind = self._entity_kind(scenic_set, placement.entity)
        if placement.offstage:
            return ResolvedPlacement(
                entity=placement.entity,
                kind=kind,
                source="offstage",
                offstage=True,
                via=placement.via,
                line_no=placement.line_no,
            )
        if placement.location is None:
            diagnostics.append(StagingDiagnostic("warning", f"Missing location for {placement.entity}", placement.line_no))
            return ResolvedPlacement(entity=placement.entity, kind=kind, source="unknown", line_no=placement.line_no)
        location = self._resolve_source(document, scenic_set, areas, placement.location, diagnostics, line_no=placement.line_no)
        origin = None
        if placement.origin is not None:
            origin = self._resolve_source(document, scenic_set, areas, placement.origin, diagnostics, line_no=placement.line_no)
        next_location = None
        if placement.next_location is not None:
            next_location = self._resolve_source(document, scenic_set, areas, placement.next_location, diagnostics, line_no=placement.line_no)
        if location.point is None:
            diagnostics.append(
                StagingDiagnostic(
                    "warning",
                    f"Unresolved location {location.source!r} for {placement.entity}",
                    placement.line_no,
                )
            )
        return ResolvedPlacement(
            entity=placement.entity,
            kind=kind,
            source=placement.location.source,
            point=location.point,
            origin_source=placement.origin.source if placement.origin is not None else None,
            origin_point=origin.point if origin is not None else None,
            next_source=placement.next_location.source if placement.next_location is not None else None,
            next_point=next_location.point if next_location is not None else None,
            face=placement.face,
            line_no=placement.line_no,
        )

    def _resolve_source(
        self,
        document: StagingDocument,
        scenic_set: ScenicSetDefinition,
        areas: dict[str, AreaDefinition],
        source: SourceLocation,
        diagnostics: list[StagingDiagnostic],
        line_no: int | None = None,
    ) -> SourceLocation:
        if source.point is not None:
            return source
        source_id = AREA_ALIASES.get(source.source, source.source)
        if source_id in areas:
            return SourceLocation(source=source.source, point=areas[source_id].center)
        if source_id in scenic_set.anchors:
            anchor = scenic_set.anchors[source_id]
            return self._resolve_source(document, scenic_set, areas, anchor.at, diagnostics, line_no=line_no)
        if source_id in scenic_set.set_pieces:
            set_piece = scenic_set.set_pieces[source_id]
            return self._resolve_source(document, scenic_set, areas, set_piece.at, diagnostics, line_no=line_no)
        if source_id in scenic_set.props:
            prop = scenic_set.props[source_id]
            return self._resolve_source(document, scenic_set, areas, prop.preset, diagnostics, line_no=line_no)
        diagnostics.append(StagingDiagnostic("warning", f"Unknown location reference {source.source!r}", line_no))
        return source

    def _entity_kind(self, scenic_set: ScenicSetDefinition, entity: str) -> str:
        if entity in scenic_set.set_pieces:
            return "set_piece"
        if entity in scenic_set.props or not entity.isupper():
            return "prop"
        return "actor"
