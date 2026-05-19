from __future__ import annotations

from dataclasses import dataclass, replace

from stager.staging.diagnostics import StagingDiagnostic
from stager.staging.model import (
    AnchorDefinition,
    AreaDefinition,
    Point3D,
    ResolvedPlacement,
    ResolvedSnapshot,
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
    def resolve_snapshot(self, document: StagingDocument, scene_id: str) -> ResolvedSnapshot:
        diagnostics = list(document.diagnostics)
        areas = self._areas(document)
        snapshot = document.snapshots.get(scene_id)
        if snapshot is None:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown scene snapshot {scene_id!r}"))
            placements = ()
        else:
            placements = tuple(self._resolve_placement(document, areas, placement, diagnostics) for placement in snapshot.placements)
        return ResolvedSnapshot(
            scene_id=scene_id,
            stage=document.stage,
            areas=areas,
            anchors=self._resolved_anchors(document, areas, diagnostics),
            actors=document.actors,
            set_pieces=self._resolved_set_pieces(document, areas, diagnostics),
            placements=placements,
            diagnostics=tuple(diagnostics),
        )

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
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, AnchorDefinition]:
        return {
            key: replace(anchor, at=self._resolve_source(document, areas, anchor.at, diagnostics))
            for key, anchor in document.anchors.items()
        }

    def _resolved_set_pieces(
        self,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        diagnostics: list[StagingDiagnostic],
    ) -> dict[str, SetPieceDefinition]:
        return {
            key: replace(set_piece, at=self._resolve_source(document, areas, set_piece.at, diagnostics))
            for key, set_piece in document.set_pieces.items()
        }

    def _resolve_placement(
        self,
        document: StagingDocument,
        areas: dict[str, AreaDefinition],
        placement,
        diagnostics: list[StagingDiagnostic],
    ) -> ResolvedPlacement:
        kind = self._entity_kind(document, placement.entity)
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
        location = self._resolve_source(document, areas, placement.location, diagnostics, line_no=placement.line_no)
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
            face=placement.face,
            line_no=placement.line_no,
        )

    def _resolve_source(
        self,
        document: StagingDocument,
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
        if source_id in document.anchors:
            anchor = document.anchors[source_id]
            return self._resolve_source(document, areas, anchor.at, diagnostics, line_no=line_no)
        if source_id in document.set_pieces:
            set_piece = document.set_pieces[source_id]
            return self._resolve_source(document, areas, set_piece.at, diagnostics, line_no=line_no)
        if source_id in document.props:
            prop = document.props[source_id]
            return self._resolve_source(document, areas, prop.preset, diagnostics, line_no=line_no)
        diagnostics.append(StagingDiagnostic("warning", f"Unknown location reference {source.source!r}", line_no))
        return source

    def _entity_kind(self, document: StagingDocument, entity: str) -> str:
        if entity in document.set_pieces:
            return "set_piece"
        if entity in document.props or not entity.isupper():
            return "prop"
        return "actor"
