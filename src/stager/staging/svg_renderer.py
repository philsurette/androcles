from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from xml.sax.saxutils import escape

from stager.staging.model import Point3D, ResolvedPlacement, ResolvedSnapshot
from stager.staging.svg_icons import StageSvgIconLibrary


@dataclass
class StageSvgRenderer:
    stage_width_px: int = 720
    margin_px: int = 40
    side_panel_px: int = 220
    orientation: Literal["portrait", "landscape"] = "portrait"
    icons: StageSvgIconLibrary = field(default_factory=StageSvgIconLibrary)

    def render(self, snapshot: ResolvedSnapshot) -> str:
        stage = snapshot.stage
        scale = self._scale(stage.width, stage.depth)
        stage_draw_width, stage_draw_height = self._stage_draw_size(stage.width, stage.depth, scale)
        stage_height_px = int(stage_draw_height + 2 * self.margin_px)
        if self.orientation == "portrait":
            total_width = int(stage_draw_width + 2 * self.margin_px)
            total_height = stage_height_px + self.side_panel_px
            side_panel_x = self.margin_px
            side_panel_y = stage_height_px + 28
        else:
            total_width = int(stage_draw_width + 2 * self.margin_px + self.side_panel_px)
            total_height = stage_height_px
            side_panel_x = int(stage_draw_width + 2 * self.margin_px + 20)
            side_panel_y = 30
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{total_height}" '
                f'viewBox="0 0 {total_width} {total_height}" role="img">'
            ),
            "<style>",
            ".stage-boundary{fill:#fafafa;stroke:#222;stroke-width:2}",
            ".grid-line{stroke:#bbb;stroke-width:1}",
            ".area-label{font:12px sans-serif;fill:#555;text-anchor:start}",
            ".anchor{fill:#fff;stroke:#555;stroke-width:1.5}",
            ".set-piece-footprint{fill:#e8e2d0;fill-opacity:.5;stroke:#6b614d;stroke-width:1}",
            ".stage-icon{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}",
            ".actor-circle{fill:#2f6f9f;fill-opacity:.78;stroke:#12384f;stroke-width:1.5}",
            ".actor-label{font:10px sans-serif;font-weight:700;fill:#fff;text-anchor:middle;dominant-baseline:middle}",
            ".icon-set-piece{color:#6b614d}",
            ".icon-prop{color:#7a4b9d}",
            ".label{font:13px sans-serif;fill:#111}",
            ".small{font:11px sans-serif;fill:#333;paint-order:stroke;stroke:#fff;stroke-width:3}",
            ".diagnostic{font:12px sans-serif;fill:#8a3a00}",
            "</style>",
            *self.icons.defs(),
            f'<rect class="stage-boundary" x="{self.margin_px}" y="{self.margin_px}" '
            f'width="{stage_draw_width:g}" height="{stage_draw_height:g}"/>',
        ]
        lines.append('<g class="layer-grid">')
        lines.extend(self._grid_lines(stage.width, stage.depth, scale))
        lines.extend(self._area_labels(snapshot, scale))
        lines.append("</g>")
        lines.append('<g class="layer-scenery">')
        lines.extend(self._anchors(snapshot, scale))
        lines.extend(self._set_pieces(snapshot, scale))
        lines.extend(self._placements(snapshot, scale, kind_filter="set_piece"))
        lines.append("</g>")
        lines.append('<g class="layer-props">')
        lines.extend(self._placements(snapshot, scale, kind_filter="prop"))
        lines.append("</g>")
        lines.append('<g class="layer-actors">')
        lines.extend(self._placements(snapshot, scale))
        lines.append("</g>")
        lines.extend(self._side_panel(snapshot, side_panel_x, side_panel_y))
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def _grid_lines(self, width: float, depth: float, scale: float) -> list[str]:
        lines = []
        for x in (-width / 6, width / 6):
            x1, y1 = self._project(Point3D(x, 0), width, depth, scale)
            x2, y2 = self._project(Point3D(x, depth), width, depth, scale)
            lines.append(f'<line class="grid-line" x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"/>')
        for y in (depth / 3, depth * 2 / 3):
            x1, y1 = self._project(Point3D(-width / 2, y), width, depth, scale)
            x2, y2 = self._project(Point3D(width / 2, y), width, depth, scale)
            lines.append(f'<line class="grid-line" x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"/>')
        return lines

    def _area_labels(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for area_id, area in sorted(snapshot.areas.items()):
            corners = [
                self._project(Point3D(area.center.x - area.width / 2, area.center.y - area.depth / 2), snapshot.stage.width, snapshot.stage.depth, scale),
                self._project(Point3D(area.center.x - area.width / 2, area.center.y + area.depth / 2), snapshot.stage.width, snapshot.stage.depth, scale),
                self._project(Point3D(area.center.x + area.width / 2, area.center.y - area.depth / 2), snapshot.stage.width, snapshot.stage.depth, scale),
                self._project(Point3D(area.center.x + area.width / 2, area.center.y + area.depth / 2), snapshot.stage.width, snapshot.stage.depth, scale),
            ]
            x = min(corner[0] for corner in corners) + 5
            y = min(corner[1] for corner in corners) + 15
            lines.append(f'<text class="area-label" x="{x:g}" y="{y:g}">{escape(area_id)}</text>')
        return lines

    def _anchors(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for anchor_id, anchor in sorted(snapshot.anchors.items()):
            if anchor.at.point is None:
                continue
            x, y = self._project(anchor.at.point, snapshot.stage.width, snapshot.stage.depth, scale)
            lines.append(f'<circle class="anchor" cx="{x:g}" cy="{y:g}" r="5"><title>{escape(anchor_id)}</title></circle>')
            if anchor.at.point.z:
                lines.append(f'<text class="small" x="{x + 7:g}" y="{y + 7:g}">+{anchor.at.point.z:g}</text>')
        return lines

    def _set_pieces(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        placed_set_piece_ids = {
            placement.entity
            for placement in snapshot.placements
            if placement.kind == "set_piece" and not placement.offstage and placement.point is not None
        }
        for set_id, set_piece in sorted(snapshot.set_pieces.items()):
            if set_id in placed_set_piece_ids:
                continue
            if set_piece.at.point is None:
                continue
            x, y = self._project(set_piece.at.point, snapshot.stage.width, snapshot.stage.depth, scale)
            width, depth = set_piece.size or (3.0, 2.0)
            footprint_width, footprint_height = self._footprint_size(width, depth, scale)
            lines.append(
                f'<rect class="set-piece-footprint" x="{x - footprint_width / 2:g}" y="{y - footprint_height / 2:g}" '
                f'width="{footprint_width:g}" height="{footprint_height:g}" rx="2"/>'
            )
            icon_id = self._set_piece_icon_id(set_id, set_piece.kind)
            lines.append(self._icon_use(icon_id, "icon-set-piece", x, y, 32, title=set_id))
            if set_piece.at.point.z:
                lines.append(f'<text class="small" x="{x:g}" y="{y + 43:g}" text-anchor="middle">+{set_piece.at.point.z:g}</text>')
        return lines

    def _placements(self, snapshot: ResolvedSnapshot, scale: float, kind_filter: str | None = None) -> list[str]:
        lines = []
        actor_offsets = self._actor_offsets(snapshot, scale)
        prop_offsets = self._prop_offsets(snapshot, scale)
        prop_slot_indexes = self._prop_slot_indexes(snapshot)
        for index, placement in enumerate(snapshot.placements):
            if placement.offstage or placement.point is None:
                continue
            if kind_filter is not None and placement.kind != kind_filter:
                continue
            if kind_filter is None and placement.kind in ("prop", "set_piece"):
                continue
            if placement.kind == "actor":
                lines.extend(self._actor(snapshot, placement, scale, actor_offsets.get(index, (0.0, 0.0))))
            elif placement.kind == "prop":
                lines.extend(
                    self._prop(
                        snapshot,
                        placement,
                        scale,
                        prop_offsets.get(index, (0.0, 0.0)),
                        prop_slot_indexes.get(index, 0),
                    )
                )
            elif placement.kind == "set_piece":
                lines.extend(self._placed_set_piece(snapshot, placement, scale))
        return lines

    def _actor(
        self,
        snapshot: ResolvedSnapshot,
        placement: ResolvedPlacement,
        scale: float,
        offset: tuple[float, float],
    ) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        x += offset[0]
        y += offset[1]
        actor = snapshot.actors.get(placement.entity)
        label = actor.label if actor is not None else self._default_actor_label(placement.entity)
        title = actor.name if actor is not None else placement.entity
        lines = [
            f'<g class="actor-mark"><title>{escape(title)}</title>',
            f'<circle class="actor-circle" cx="{x:g}" cy="{y:g}" r="13"/>',
            f'<text class="actor-label" x="{x:g}" y="{y + 1:g}">{escape(label)}</text>',
            "</g>",
        ]
        if placement.face:
            lines.append(f'<text class="small" x="{x + 16:g}" y="{y + 18:g}">face {escape(placement.face)}</text>')
        if placement.point.z:
            lines.append(f'<text class="small" x="{x - 10:g}" y="{y - 13:g}">+{placement.point.z:g}</text>')
        return lines

    def _prop(
        self,
        snapshot: ResolvedSnapshot,
        placement: ResolvedPlacement,
        scale: float,
        offset: tuple[float, float],
        slot_index: int,
    ) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        x += offset[0]
        y += offset[1]
        icon_id = self.icons.icon_id(placement.entity, self.icons.default_prop_icon)
        if placement.source in snapshot.set_pieces:
            return self._prop_on_set_piece(snapshot, placement, scale, slot_index, icon_id)
        return [
            self._icon_use(icon_id, "icon-prop", x, y, 24, title=placement.entity),
        ]

    def _prop_on_set_piece(
        self,
        snapshot: ResolvedSnapshot,
        placement: ResolvedPlacement,
        scale: float,
        slot_index: int,
        icon_id: str,
    ) -> list[str]:
        assert placement.point is not None
        set_piece = snapshot.set_pieces[placement.source]
        center_x, center_y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        width, depth = set_piece.size or (3.0, 2.0)
        footprint_width, footprint_height = self._footprint_size(width, depth, scale)
        half_width = footprint_width / 2
        half_depth = footprint_height / 2
        columns = (-0.28, 0.0, 0.28)
        rows = (-0.24, 0.08, 0.34)
        icon_x = center_x + half_width * columns[slot_index % len(columns)]
        icon_y = center_y + half_depth * rows[(slot_index // len(columns)) % len(rows)]
        return [
            self._icon_use(icon_id, "icon-prop", icon_x, icon_y, 22, title=placement.entity),
        ]

    def _placed_set_piece(self, snapshot: ResolvedSnapshot, placement: ResolvedPlacement, scale: float) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        set_piece = snapshot.set_pieces.get(placement.entity)
        icon_id = self._set_piece_icon_id(placement.entity, set_piece.kind if set_piece is not None else None)
        return [
            self._icon_use(icon_id, "icon-set-piece", x, y, 32, title=placement.entity),
        ]

    def _side_panel(self, snapshot: ResolvedSnapshot, x: int, y: int) -> list[str]:
        lines = [
            f'<text class="label" x="{x}" y="{y}">Scene {escape(snapshot.scene_id)}</text>',
            f'<text class="small" x="{x}" y="{y + 20}">Stage: {escape(snapshot.stage.stage_type)}</text>',
        ]
        cursor = y + 48
        offstage = [placement for placement in snapshot.placements if placement.offstage or placement.point is None]
        if offstage:
            lines.append(f'<text class="label" x="{x}" y="{cursor}">Offstage / unknown</text>')
            cursor += 18
            for placement in offstage:
                suffix = f" via {placement.via}" if placement.via else ""
                source = "unknown" if placement.point is None and not placement.offstage else "offstage"
                lines.append(f'<text class="small" x="{x}" y="{cursor}">{escape(placement.entity)}: {source}{escape(suffix)}</text>')
                cursor += 16
        if snapshot.diagnostics:
            cursor += 10
            lines.append(f'<text class="label" x="{x}" y="{cursor}">Diagnostics</text>')
            cursor += 18
            for diagnostic in snapshot.diagnostics:
                lines.append(f'<text class="diagnostic" x="{x}" y="{cursor}">{escape(diagnostic.message[:34])}</text>')
                cursor += 16
        return lines

    def _project(self, point: Point3D, stage_width: float, stage_depth: float, scale: float) -> tuple[float, float]:
        if self.orientation == "portrait":
            return (
                self.margin_px + (stage_depth - point.y) * scale,
                self.margin_px + (point.x + stage_width / 2) * scale,
            )
        return (
            self.margin_px + (point.x + stage_width / 2) * scale,
            self.margin_px + (stage_depth - point.y) * scale,
        )

    def _scale(self, stage_width: float, stage_depth: float) -> float:
        stage_screen_width = stage_depth if self.orientation == "portrait" else stage_width
        return (self.stage_width_px - 2 * self.margin_px) / stage_screen_width

    def _stage_draw_size(self, stage_width: float, stage_depth: float, scale: float) -> tuple[float, float]:
        if self.orientation == "portrait":
            return (stage_depth * scale, stage_width * scale)
        return (stage_width * scale, stage_depth * scale)

    def _footprint_size(self, stage_width: float, stage_depth: float, scale: float) -> tuple[float, float]:
        if self.orientation == "portrait":
            return (stage_depth * scale, stage_width * scale)
        return (stage_width * scale, stage_depth * scale)

    def _icon_use(self, icon_id: str, class_name: str, x: float, y: float, size: int, *, title: str | None = None) -> str:
        offset = size / 2
        use = (
            f'<use class="stage-icon {class_name}" href="#stage-icon-{escape(icon_id)}" '
            f'x="{x - offset:g}" y="{y - offset:g}" width="{size}" height="{size}"/>'
        )
        if title is None:
            return use
        return f'<g><title>{escape(title)}</title>{use}</g>'

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

    def _actor_offsets(self, snapshot: ResolvedSnapshot, scale: float) -> dict[int, tuple[float, float]]:
        grouped: dict[tuple[int, int], list[int]] = {}
        for index, placement in enumerate(snapshot.placements):
            if placement.kind != "actor" or placement.offstage or placement.point is None:
                continue
            x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
            grouped.setdefault((round(x), round(y)), []).append(index)
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

    def _prop_offsets(self, snapshot: ResolvedSnapshot, scale: float) -> dict[int, tuple[float, float]]:
        grouped: dict[tuple[int, int], list[int]] = {}
        for index, placement in enumerate(snapshot.placements):
            if placement.kind != "prop" or placement.offstage or placement.point is None:
                continue
            if placement.source in snapshot.set_pieces:
                continue
            x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
            grouped.setdefault((round(x), round(y)), []).append(index)
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
