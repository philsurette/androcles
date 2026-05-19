from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from xml.sax.saxutils import escape

from stager.staging.diagram_state import DiagramEntity, DiagramSize, DiagramState
from stager.staging.model import Point3D
from stager.staging.svg_icons import StageSvgIconLibrary


@dataclass
class StageSvgRenderer:
    stage_width_px: int = 720
    margin_px: int = 40
    side_panel_px: int = 220
    orientation: Literal["portrait", "landscape"] = "portrait"
    icons: StageSvgIconLibrary = field(default_factory=StageSvgIconLibrary)

    def render(self, diagram: DiagramState) -> str:
        stage = diagram.stage
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
            ".movement-arrow{stroke:#333;stroke-width:2;stroke-opacity:.38;fill:none;stroke-linecap:round;stroke-dasharray:5 4}",
            ".anchor{fill:#fff;stroke:#555;stroke-width:1.5}",
            ".level-surface{fill:#d9edf7;fill-opacity:.34;stroke:#2f6f9f;stroke-width:2;stroke-dasharray:7 4}",
            ".connector{stroke:#6b614d;stroke-width:2;stroke-dasharray:5 4;fill:none}",
            ".stair-footprint{fill:#6b614d;fill-opacity:.08;stroke:none}",
            ".stair-tread{stroke-width:2;stroke-linecap:round}",
            ".set-piece-footprint{fill:#e8e2d0;fill-opacity:.5;stroke-width:1}",
            ".stage-icon{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}",
            ".actor-circle{fill-opacity:.86;stroke-width:1.5}",
            ".actor-label{font:10px sans-serif;font-weight:700;fill:#111;text-anchor:middle;dominant-baseline:middle}",
            ".label{font:13px sans-serif;fill:#111}",
            ".small{font:11px sans-serif;fill:#333;paint-order:stroke;stroke:#fff;stroke-width:3}",
            ".diagnostic{font:12px sans-serif;fill:#8a3a00}",
            "</style>",
            '<defs><marker id="movement-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M3,0 L7,4 L3,8" fill="none" stroke="#333" stroke-opacity=".38" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
            *self.icons.defs(),
            f'<rect class="stage-boundary" x="{self.margin_px}" y="{self.margin_px}" '
            f'width="{stage_draw_width:g}" height="{stage_draw_height:g}"/>',
        ]
        lines.append('<g class="layer-grid">')
        lines.extend(self._grid_lines(stage.width, stage.depth, scale))
        lines.extend(self._area_labels(diagram, scale))
        lines.append("</g>")
        lines.append('<g class="layer-scenery">')
        lines.extend(self._levels(diagram, scale))
        lines.extend(self._anchors(diagram, scale))
        lines.extend(self._connectors(diagram, scale))
        lines.extend(self._set_pieces(diagram, scale))
        lines.extend(self._placements(diagram, scale, kind_filter="set_piece"))
        lines.append("</g>")
        lines.append('<g class="layer-props">')
        lines.extend(self._placements(diagram, scale, kind_filter="prop"))
        lines.append("</g>")
        lines.append('<g class="layer-actors">')
        lines.extend(self._placements(diagram, scale))
        lines.append("</g>")
        lines.extend(self._side_panel(diagram, side_panel_x, side_panel_y))
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

    def _levels(self, diagram: DiagramState, scale: float) -> list[str]:
        lines = []
        for level in diagram.levels:
            x, y = self._project(level.point, diagram.stage.width, diagram.stage.depth, scale)
            width = level.width
            depth = level.depth
            footprint_width, footprint_height = self._footprint_size(width, depth, scale)
            lines.append(
                f'<rect class="level-surface" x="{x - footprint_width / 2:g}" y="{y - footprint_height / 2:g}" '
                f'width="{footprint_width:g}" height="{footprint_height:g}" rx="2">'
                f'<title>{escape(level.title)}</title></rect>'
            )
            if level.label:
                lines.append(f'<text class="small" x="{x:g}" y="{y - footprint_height / 2 + 16:g}" text-anchor="middle">{escape(level.label)}</text>')
        return lines

    def _connectors(self, diagram: DiagramState, scale: float) -> list[str]:
        lines = []
        for connector in diagram.connectors:
            x1, y1 = self._project(connector.start, diagram.stage.width, diagram.stage.depth, scale)
            x2, y2 = self._project(connector.end, diagram.stage.width, diagram.stage.depth, scale)
            if connector.kind == "stair":
                lines.extend(self._stair_connector(connector, x1, y1, x2, y2))
            else:
                lines.append(
                    f'<line class="connector" x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}">'
                    f'<title>{escape(connector.title)}</title></line>'
                )
            if connector.label is not None:
                label_x = (x1 + x2) / 2
                label_y = (y1 + y2) / 2 - 6
                lines.append(
                    f'<text class="small" x="{label_x:g}" y="{label_y:g}" text-anchor="middle">'
                    f'{connector.label}</text>'
                )
        return lines

    def _stair_connector(self, connector, x1: float, y1: float, x2: float, y2: float) -> list[str]:
        if connector.start.z <= connector.end.z:
            bottom = (x1, y1, connector.start.z)
            top = (x2, y2, connector.end.z)
        else:
            bottom = (x2, y2, connector.end.z)
            top = (x1, y1, connector.start.z)
        bottom_x, bottom_y, bottom_z = bottom
        top_x, top_y, top_z = top
        dx = top_x - bottom_x
        dy = top_y - bottom_y
        distance = (dx * dx + dy * dy) ** 0.5
        if distance == 0:
            return []
        normal_x = -dy / distance
        normal_y = dx / distance
        tread_count = max(4, min(9, round(distance / 32)))
        lines = [f'<g class="stair-connector"><title>{escape(connector.title)}</title>']
        top_width = 36
        bottom_width = top_width * 0.2
        footprint_half_top = top_width / 2 + 4
        footprint_half_bottom = bottom_width / 2 + 4
        points = [
            (bottom_x - normal_x * footprint_half_bottom, bottom_y - normal_y * footprint_half_bottom),
            (top_x - normal_x * footprint_half_top, top_y - normal_y * footprint_half_top),
            (top_x + normal_x * footprint_half_top, top_y + normal_y * footprint_half_top),
            (bottom_x + normal_x * footprint_half_bottom, bottom_y + normal_y * footprint_half_bottom),
        ]
        point_text = " ".join(f"{point_x:g},{point_y:g}" for point_x, point_y in points)
        lines.append(f'<polygon class="stair-footprint" points="{point_text}"/>')
        bottom_color = self._z_stroke(bottom_z)
        top_color = self._z_stroke(top_z)
        for index in range(tread_count - 1):
            ratio = index / (tread_count - 1) if tread_count > 1 else 1
            center_x = bottom_x + dx * ratio
            center_y = bottom_y + dy * ratio
            length = top_width * (0.2 + 0.8 * ratio)
            half = length / 2
            color = self._mix_hex(bottom_color, top_color, ratio)
            lines.append(
                f'<line class="stair-tread" x1="{center_x - normal_x * half:g}" y1="{center_y - normal_y * half:g}" '
                f'x2="{center_x + normal_x * half:g}" y2="{center_y + normal_y * half:g}" stroke="{color}"/>'
            )
        lines.append("</g>")
        return lines

    def _area_labels(self, diagram: DiagramState, scale: float) -> list[str]:
        lines = []
        for area in diagram.areas:
            corners = [
                self._project(Point3D(area.center.x - area.width / 2, area.center.y - area.depth / 2), diagram.stage.width, diagram.stage.depth, scale),
                self._project(Point3D(area.center.x - area.width / 2, area.center.y + area.depth / 2), diagram.stage.width, diagram.stage.depth, scale),
                self._project(Point3D(area.center.x + area.width / 2, area.center.y - area.depth / 2), diagram.stage.width, diagram.stage.depth, scale),
                self._project(Point3D(area.center.x + area.width / 2, area.center.y + area.depth / 2), diagram.stage.width, diagram.stage.depth, scale),
            ]
            x = min(corner[0] for corner in corners) + 5
            y = min(corner[1] for corner in corners) + 15
            lines.append(f'<text class="area-label" x="{x:g}" y="{y:g}">{escape(area.id)}</text>')
        return lines

    def _anchors(self, diagram: DiagramState, scale: float) -> list[str]:
        lines = []
        for anchor in diagram.anchors:
            x, y = self._project(anchor.point, diagram.stage.width, diagram.stage.depth, scale)
            stroke = self._elevation_stroke(anchor.elevation)
            fill = self._elevation_fill(anchor.elevation)
            lines.append(
                f'<circle class="anchor" cx="{x:g}" cy="{y:g}" r="5" '
                f'style="fill:{fill};stroke:{stroke}"><title>{escape(anchor.title)}</title></circle>'
            )
            if anchor.point.z:
                lines.append(f'<text class="small" x="{x + 7:g}" y="{y + 7:g}">+{anchor.point.z:g}</text>')
        return lines

    def _set_pieces(self, diagram: DiagramState, scale: float) -> list[str]:
        lines = []
        for set_piece in diagram.set_pieces:
            if set_piece.point is None:
                continue
            x, y = self._project(set_piece.point, diagram.stage.width, diagram.stage.depth, scale)
            size = set_piece.size or self._default_entity_size()
            width = size.width
            depth = size.depth
            footprint_width, footprint_height = self._footprint_size(width, depth, scale)
            stroke = self._elevation_stroke(set_piece.elevation)
            lines.append(
                f'<rect class="set-piece-footprint" x="{x - footprint_width / 2:g}" y="{y - footprint_height / 2:g}" '
                f'width="{footprint_width:g}" height="{footprint_height:g}" rx="2" style="stroke:{stroke}"/>'
            )
            lines.append(self._icon_use(set_piece.icon or self.icons.default_set_piece_icon, "icon-set-piece", x, y, 32, title=set_piece.title, color=stroke))
            if set_piece.point.z:
                lines.append(f'<text class="small" x="{x:g}" y="{y + 43:g}" text-anchor="middle">+{set_piece.point.z:g}</text>')
        return lines

    def _placements(self, diagram: DiagramState, scale: float, kind_filter: str | None = None) -> list[str]:
        lines = []
        for entity in diagram.entities:
            if not entity.visible or entity.point is None:
                continue
            if kind_filter is not None and entity.kind != kind_filter:
                continue
            if kind_filter is None and entity.kind in ("prop", "set_piece"):
                continue
            if entity.kind == "actor":
                lines.extend(self._actor(diagram, entity, scale))
            elif entity.kind == "prop":
                lines.extend(self._prop(diagram, entity, scale))
            elif entity.kind == "set_piece":
                lines.extend(self._placed_set_piece(diagram, entity, scale))
        return lines

    def _actor(
        self,
        diagram: DiagramState,
        entity: DiagramEntity,
        scale: float,
    ) -> list[str]:
        assert entity.point is not None
        x, y = self._project(entity.point, diagram.stage.width, diagram.stage.depth, scale)
        x += entity.offset.x
        y += entity.offset.y
        fill = self._elevation_fill(entity.elevation)
        stroke = self._elevation_stroke(entity.elevation)
        lines = [
            *self._movement_arrow(diagram, entity, scale, x, y),
            *self._next_movement_arrow(diagram, entity, scale, x, y),
            f'<g class="actor-mark"><title>{escape(entity.title)}</title>',
            f'<circle class="actor-circle" cx="{x:g}" cy="{y:g}" r="13" style="fill:{fill};stroke:{stroke}"/>',
            f'<text class="actor-label" x="{x:g}" y="{y + 1:g}">{escape(entity.label or entity.source_id)}</text>',
            "</g>",
        ]
        if entity.face:
            lines.append(f'<text class="small" x="{x + 16:g}" y="{y + 18:g}">face {escape(entity.face)}</text>')
        if entity.point.z:
            lines.append(f'<text class="small" x="{x - 10:g}" y="{y - 13:g}">+{entity.point.z:g}</text>')
        return lines

    def _movement_arrow(
        self,
        diagram: DiagramState,
        entity: DiagramEntity,
        scale: float,
        target_x: float,
        target_y: float,
    ) -> list[str]:
        if entity.movement_from is None or entity.point is None:
            return []
        origin_x, origin_y = self._project(entity.movement_from, diagram.stage.width, diagram.stage.depth, scale)
        dx = target_x - origin_x
        dy = target_y - origin_y
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < 1:
            return []
        unit_x = dx / distance
        unit_y = dy / distance
        arrow_length = min(32.4, max(16.8, distance * 0.24))
        end_x = target_x - unit_x * 15
        end_y = target_y - unit_y * 15
        start_x = end_x - unit_x * arrow_length
        start_y = end_y - unit_y * arrow_length
        title = f"{entity.source_id} moved from {entity.movement_from_source}" if entity.movement_from_source else f"{entity.source_id} moved"
        return [
            f'<line class="movement-arrow" x1="{start_x:g}" y1="{start_y:g}" x2="{end_x:g}" y2="{end_y:g}" '
            f'marker-end="url(#movement-arrowhead)"><title>{escape(title)}</title></line>'
        ]

    def _next_movement_arrow(
        self,
        diagram: DiagramState,
        entity: DiagramEntity,
        scale: float,
        start_x: float,
        start_y: float,
    ) -> list[str]:
        if entity.movement_to is None or entity.point is None:
            return []
        destination_x, destination_y = self._project(entity.movement_to, diagram.stage.width, diagram.stage.depth, scale)
        dx = destination_x - start_x
        dy = destination_y - start_y
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < 1:
            return []
        unit_x = dx / distance
        unit_y = dy / distance
        arrow_length = min(32.4, max(16.8, distance * 0.24))
        shaft_start_x = start_x + unit_x * 15
        shaft_start_y = start_y + unit_y * 15
        end_x = shaft_start_x + unit_x * arrow_length
        end_y = shaft_start_y + unit_y * arrow_length
        title = f"{entity.source_id} moves next to {entity.movement_to_source}" if entity.movement_to_source else f"{entity.source_id} moves next"
        return [
            f'<line class="movement-arrow" x1="{shaft_start_x:g}" y1="{shaft_start_y:g}" x2="{end_x:g}" y2="{end_y:g}" '
            f'marker-end="url(#movement-arrowhead)"><title>{escape(title)}</title></line>'
        ]

    def _prop(
        self,
        diagram: DiagramState,
        entity: DiagramEntity,
        scale: float,
    ) -> list[str]:
        assert entity.point is not None
        x, y = self._project(entity.point, diagram.stage.width, diagram.stage.depth, scale)
        x += entity.offset.x
        y += entity.offset.y
        icon_id = entity.icon or self.icons.default_prop_icon
        set_piece = self._set_piece_entity(diagram, entity.source)
        if set_piece is not None:
            return self._prop_on_set_piece(diagram, entity, scale, icon_id, set_piece)
        return [
            self._icon_use(icon_id, "icon-prop", x, y, 24, title=entity.title, color=self._elevation_stroke(entity.elevation)),
        ]

    def _prop_on_set_piece(
        self,
        diagram: DiagramState,
        entity: DiagramEntity,
        scale: float,
        icon_id: str,
        set_piece: DiagramEntity,
    ) -> list[str]:
        assert entity.point is not None
        center_x, center_y = self._project(entity.point, diagram.stage.width, diagram.stage.depth, scale)
        size = set_piece.size or self._default_entity_size()
        width = size.width
        depth = size.depth
        footprint_width, footprint_height = self._footprint_size(width, depth, scale)
        half_width = footprint_width / 2
        half_depth = footprint_height / 2
        columns = (-0.28, 0.0, 0.28)
        rows = (-0.24, 0.08, 0.34)
        slot_index = entity.slot_index or 0
        icon_x = center_x + half_width * columns[slot_index % len(columns)]
        icon_y = center_y + half_depth * rows[(slot_index // len(columns)) % len(rows)]
        return [
            self._icon_use(icon_id, "icon-prop", icon_x, icon_y, 22, title=entity.title, color=self._elevation_stroke(entity.elevation)),
        ]

    def _placed_set_piece(self, diagram: DiagramState, entity: DiagramEntity, scale: float) -> list[str]:
        assert entity.point is not None
        x, y = self._project(entity.point, diagram.stage.width, diagram.stage.depth, scale)
        return [
            self._icon_use(entity.icon or self.icons.default_set_piece_icon, "icon-set-piece", x, y, 32, title=entity.title, color=self._elevation_stroke(entity.elevation)),
        ]

    def _side_panel(self, diagram: DiagramState, x: int, y: int) -> list[str]:
        lines = [
            f'<text class="label" x="{x}" y="{y}">Scene {escape(diagram.diagram_id.removeprefix("scene:"))}</text>',
            f'<text class="small" x="{x}" y="{y + 20}">Stage: {escape(diagram.stage.stage_type)}</text>',
        ]
        cursor = y + 48
        if diagram.set_id is not None:
            lines.append(f'<text class="small" x="{x}" y="{cursor}">Set: {escape(diagram.set_id)}</text>')
            cursor += 20
        if diagram.offstage:
            lines.append(f'<text class="label" x="{x}" y="{cursor}">Offstage / unknown</text>')
            cursor += 18
            for entity in diagram.offstage:
                suffix = f" via {entity.via}" if entity.via else ""
                lines.append(f'<text class="small" x="{x}" y="{cursor}">{escape(entity.source_id)}: {escape(entity.source)}{escape(suffix)}</text>')
                cursor += 16
        if diagram.diagnostics:
            cursor += 10
            lines.append(f'<text class="label" x="{x}" y="{cursor}">Diagnostics</text>')
            cursor += 18
            for diagnostic in diagram.diagnostics:
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

    def _icon_use(
        self,
        icon_id: str,
        class_name: str,
        x: float,
        y: float,
        size: int,
        *,
        title: str | None = None,
        color: str | None = None,
    ) -> str:
        offset = size / 2
        style = f' style="color:{color}"' if color is not None else ""
        use = (
            f'<use class="stage-icon {class_name}" href="#stage-icon-{escape(icon_id)}"{style} '
            f'x="{x - offset:g}" y="{y - offset:g}" width="{size}" height="{size}"/>'
        )
        if title is None:
            return use
        return f'<g><title>{escape(title)}</title>{use}</g>'

    def _set_piece_entity(self, diagram: DiagramState, source_id: str) -> DiagramEntity | None:
        for entity in (*diagram.set_pieces, *diagram.entities):
            if entity.kind == "set_piece" and entity.source_id == source_id:
                return entity
        return None

    def _default_entity_size(self):
        return DiagramSize(width=3.0, depth=2.0)

    def _elevation_fill(self, elevation: str) -> str:
        if elevation == "elevated":
            return "#d9edf7"
        if elevation == "below":
            return "#f4e3ff"
        return "#e6e6e6"

    def _elevation_stroke(self, elevation: str) -> str:
        if elevation == "elevated":
            return "#2f6f9f"
        if elevation == "below":
            return "#7a4b9d"
        return "#555555"

    def _z_stroke(self, z: float) -> str:
        if z > 0:
            return self._elevation_stroke("elevated")
        if z < 0:
            return self._elevation_stroke("below")
        return self._elevation_stroke("deck")

    def _mix_hex(self, start: str, end: str, ratio: float) -> str:
        start_rgb = self._hex_to_rgb(start)
        end_rgb = self._hex_to_rgb(end)
        mixed = tuple(round(start_rgb[index] + (end_rgb[index] - start_rgb[index]) * ratio) for index in range(3))
        return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        value = value.removeprefix("#")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
