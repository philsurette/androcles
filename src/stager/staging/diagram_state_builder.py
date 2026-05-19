from __future__ import annotations

from dataclasses import dataclass

from stager.staging.diagram_state import (
    DiagramAnchor,
    DiagramArea,
    DiagramConnector,
    DiagramDiagnostic,
    DiagramEntity,
    DiagramKind,
    DiagramLevel,
    DiagramOffstageEntity,
    DiagramOffset,
    DiagramSize,
    DiagramStage,
    DiagramState,
)
from stager.staging.model import ResolvedSnapshot
from stager.staging.svg_icons import StageSvgIconLibrary


@dataclass
class DiagramStateBuilder:
    icons: StageSvgIconLibrary

    def __init__(self, icons: StageSvgIconLibrary | None = None) -> None:
        self.icons = icons or StageSvgIconLibrary()

    def build(self, snapshot: ResolvedSnapshot, *, diagram_kind: DiagramKind | None = None) -> DiagramState:
        kind = diagram_kind or self._diagram_kind(snapshot)
        placed_set_piece_ids = {
            placement.entity
            for placement in snapshot.placements
            if placement.kind == "set_piece" and not placement.offstage and placement.point is not None
        }
        return DiagramState(
            diagram_id=self._diagram_id(snapshot, kind),
            diagram_kind=kind,
            scene_id=self._scene_id(snapshot, kind),
            beat_id=self._beat_id(snapshot),
            set_id=snapshot.set_id,
            stage=DiagramStage(
                stage_type=snapshot.stage.stage_type,
                width=snapshot.stage.width,
                depth=snapshot.stage.depth,
                units=snapshot.stage.units,
                audience=snapshot.stage.audience,
                measured=snapshot.stage.measured,
            ),
            areas=tuple(
                DiagramArea(
                    id=area.id,
                    center=area.center,
                    width=area.width,
                    depth=area.depth,
                    aliases=area.aliases,
                )
                for _, area in sorted(snapshot.areas.items())
            ),
            levels=tuple(self._level(level_id, level) for level_id, level in sorted(snapshot.levels.items()) if level.at is not None and level.at.point is not None and level.size is not None),
            connectors=tuple(self._connector(connector_id, connector) for connector_id, connector in sorted(snapshot.connectors.items()) if connector.start.point is not None and connector.end.point is not None),
            anchors=tuple(self._anchor(anchor_id, anchor) for anchor_id, anchor in sorted(snapshot.anchors.items()) if anchor.at.point is not None),
            set_pieces=tuple(self._set_piece(set_id, set_piece) for set_id, set_piece in sorted(snapshot.set_pieces.items()) if set_id not in placed_set_piece_ids and set_piece.at.point is not None),
            entities=tuple(self._entities(snapshot)),
            offstage=tuple(self._offstage(snapshot)),
            diagnostics=tuple(
                DiagramDiagnostic(
                    severity=diagnostic.severity,
                    message=diagnostic.message,
                    line_no=diagnostic.line_no,
                )
                for diagnostic in snapshot.diagnostics
            ),
        )

    def _level(self, level_id, level) -> DiagramLevel:
        assert level.at is not None
        assert level.at.point is not None
        assert level.size is not None
        return DiagramLevel(
            id=level_id,
            point=level.at.point,
            width=level.size[0],
            depth=level.size[1],
            title=f"{level_id} +{level.z:g}",
            label=f"{level_id} +{level.z:g}" if level.z else None,
            elevation=self._elevation(level.at.point.z),
        )

    def _connector(self, connector_id, connector) -> DiagramConnector:
        assert connector.start.point is not None
        assert connector.end.point is not None
        label = None
        if connector.start.point.z != connector.end.point.z:
            label = f"{connector.kind} {connector.start.point.z:g}->{connector.end.point.z:g}"
        return DiagramConnector(
            id=connector_id,
            kind=connector.kind,
            start=connector.start.point,
            end=connector.end.point,
            title=f"{connector_id} {connector.kind}",
            label=label,
        )

    def _anchor(self, anchor_id, anchor) -> DiagramAnchor:
        assert anchor.at.point is not None
        return DiagramAnchor(
            id=anchor_id,
            point=anchor.at.point,
            kind=anchor.kind,
            title=anchor_id,
            elevation=self._elevation(anchor.at.point.z),
        )

    def _set_piece(self, set_id, set_piece) -> DiagramEntity:
        assert set_piece.at.point is not None
        icon_id = self._set_piece_icon_id(set_id, set_piece.kind)
        width, depth = set_piece.size or (3.0, 2.0)
        return DiagramEntity(
            id=f"set_piece:{set_id}",
            source_id=set_id,
            kind="set_piece",
            layer="scenery",
            point=set_piece.at.point,
            source=set_piece.at.source,
            title=set_id,
            icon=icon_id,
            elevation=self._elevation(set_piece.at.point.z),
            size=DiagramSize(width=width, depth=depth),
            fixed=set_piece.fixed,
            movable=set_piece.movable,
        )

    def _entities(self, snapshot: ResolvedSnapshot) -> list[DiagramEntity]:
        entities = []
        actor_offsets = self._actor_offsets(snapshot)
        prop_offsets = self._prop_offsets(snapshot)
        prop_slot_indexes = self._prop_slot_indexes(snapshot)
        for index, placement in enumerate(snapshot.placements):
            if placement.offstage or placement.point is None:
                continue
            if placement.kind == "actor":
                actor = snapshot.actors.get(placement.entity)
                label = actor.label if actor is not None else self._default_actor_label(placement.entity)
                title = actor.name if actor is not None else placement.entity
                entities.append(
                    DiagramEntity(
                        id=f"actor:{placement.entity}",
                        source_id=placement.entity,
                        kind="actor",
                        layer="actors",
                        point=placement.point,
                        source=placement.source,
                        title=title,
                        movement_from=placement.origin_point,
                        movement_from_source=placement.origin_source,
                        movement_to=placement.next_point,
                        movement_to_source=placement.next_source,
                        label=label,
                        face=placement.face,
                        elevation=self._elevation(placement.point.z),
                        offset=self._offset(actor_offsets.get(index, (0.0, 0.0))),
                    )
                )
            elif placement.kind == "prop":
                entities.append(
                    DiagramEntity(
                        id=f"prop:{placement.entity}",
                        source_id=placement.entity,
                        kind="prop",
                        layer="props",
                        point=placement.point,
                        source=placement.source,
                        title=placement.entity,
                        icon=self.icons.icon_id(placement.entity, self.icons.default_prop_icon),
                        elevation=self._elevation(placement.point.z),
                        offset=self._offset(prop_offsets.get(index, (0.0, 0.0))),
                        slot_index=prop_slot_indexes.get(index),
                    )
                )
            elif placement.kind == "set_piece":
                set_piece = snapshot.set_pieces.get(placement.entity)
                icon_id = self._set_piece_icon_id(placement.entity, set_piece.kind if set_piece is not None else None)
                size = None
                fixed = False
                movable = False
                if set_piece is not None:
                    width, depth = set_piece.size or (3.0, 2.0)
                    size = DiagramSize(width=width, depth=depth)
                    fixed = set_piece.fixed
                    movable = set_piece.movable
                entities.append(
                    DiagramEntity(
                        id=f"set_piece:{placement.entity}",
                        source_id=placement.entity,
                        kind="set_piece",
                        layer="scenery",
                        point=placement.point,
                        source=placement.source,
                        title=placement.entity,
                        icon=icon_id,
                        elevation=self._elevation(placement.point.z),
                        size=size,
                        fixed=fixed,
                        movable=movable,
                    )
                )
        return entities

    def _offstage(self, snapshot: ResolvedSnapshot) -> list[DiagramOffstageEntity]:
        offstage = []
        for placement in snapshot.placements:
            if not placement.offstage and placement.point is not None:
                continue
            source = "unknown" if placement.point is None and not placement.offstage else "offstage"
            offstage.append(
                DiagramOffstageEntity(
                    id=f"{placement.kind}:{placement.entity}",
                    source_id=placement.entity,
                    kind=placement.kind,
                    source=source,
                    via=placement.via,
                )
            )
        return offstage

    def _diagram_kind(self, snapshot: ResolvedSnapshot) -> DiagramKind:
        if snapshot.scene_id == "stage":
            return "stage"
        if snapshot.scene_id.startswith("set:"):
            return "set"
        if "@" in snapshot.scene_id:
            return "beat"
        return "scene"

    def _diagram_id(self, snapshot: ResolvedSnapshot, kind: DiagramKind) -> str:
        if kind == "stage":
            return "stage"
        if kind == "set":
            return f"set:{snapshot.set_id}"
        if kind == "beat":
            return f"scene:{snapshot.scene_id}"
        return f"scene:{snapshot.scene_id}"

    def _scene_id(self, snapshot: ResolvedSnapshot, kind: DiagramKind) -> str | None:
        if kind in ("stage", "set"):
            return None
        return snapshot.scene_id.split("@", 1)[0]

    def _beat_id(self, snapshot: ResolvedSnapshot) -> str | None:
        if "@" not in snapshot.scene_id:
            return None
        return snapshot.scene_id.split("@", 1)[1]

    def _set_piece_icon_id(self, entity: str, kind: str | None) -> str:
        entity_icon = self.icons.icon_id(entity, "")
        if entity_icon:
            return entity_icon
        return self.icons.icon_id(kind, self.icons.default_set_piece_icon)

    def _default_actor_label(self, entity: str) -> str:
        compact = "".join(character for character in entity if character.isalnum()).upper()
        if len(compact) >= 2:
            return compact[:2]
        return compact.ljust(2, "?")

    def _elevation(self, z: float) -> str:
        if z > 0:
            return "elevated"
        if z < 0:
            return "below"
        return "deck"

    def _actor_offsets(self, snapshot: ResolvedSnapshot) -> dict[int, tuple[float, float]]:
        grouped: dict[tuple[float, float, float], list[int]] = {}
        for index, placement in enumerate(snapshot.placements):
            if placement.kind != "actor" or placement.offstage or placement.point is None:
                continue
            grouped.setdefault((placement.point.x, placement.point.y, placement.point.z), []).append(index)
        offsets = {}
        pattern = [
            (0.0, 0.0),
            (18.0, 0.0),
            (-18.0, 0.0),
            (0.0, 18.0),
            (0.0, -18.0),
            (18.0, 18.0),
            (-18.0, 18.0),
            (18.0, -18.0),
            (-18.0, -18.0),
        ]
        for indexes in grouped.values():
            for offset_index, placement_index in enumerate(indexes):
                offsets[placement_index] = pattern[offset_index % len(pattern)]
        return offsets

    def _prop_offsets(self, snapshot: ResolvedSnapshot) -> dict[int, tuple[float, float]]:
        grouped: dict[tuple[float, float, float], list[int]] = {}
        for index, placement in enumerate(snapshot.placements):
            if placement.kind != "prop" or placement.offstage or placement.point is None:
                continue
            if placement.source in snapshot.set_pieces:
                continue
            grouped.setdefault((placement.point.x, placement.point.y, placement.point.z), []).append(index)
        offsets = {}
        for indexes in grouped.values():
            for offset_index, placement_index in enumerate(indexes):
                offsets[placement_index] = (0.0, offset_index * 14.0)
        return offsets

    def _prop_slot_indexes(self, snapshot: ResolvedSnapshot) -> dict[int, int]:
        grouped: dict[str, list[int]] = {}
        for index, placement in enumerate(snapshot.placements):
            if placement.kind != "prop" or placement.offstage or placement.point is None:
                continue
            if placement.source in snapshot.set_pieces:
                grouped.setdefault(placement.source, []).append(index)
        slot_indexes = {}
        for indexes in grouped.values():
            for slot_index, placement_index in enumerate(indexes):
                slot_indexes[placement_index] = slot_index
        return slot_indexes

    def _offset(self, value: tuple[float, float]) -> DiagramOffset:
        return DiagramOffset(x=value[0], y=value[1])
