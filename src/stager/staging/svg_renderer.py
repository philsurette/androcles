from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from stager.staging.model import Point3D, ResolvedPlacement, ResolvedSnapshot


@dataclass
class StageSvgRenderer:
    stage_width_px: int = 720
    margin_px: int = 40
    side_panel_px: int = 220

    def render(self, snapshot: ResolvedSnapshot) -> str:
        stage = snapshot.stage
        scale = (self.stage_width_px - 2 * self.margin_px) / stage.width
        stage_height_px = int(stage.depth * scale + 2 * self.margin_px)
        total_width = self.stage_width_px + self.side_panel_px
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{stage_height_px}" '
                f'viewBox="0 0 {total_width} {stage_height_px}" role="img">'
            ),
            "<style>",
            ".stage-boundary{fill:#fafafa;stroke:#222;stroke-width:2}",
            ".grid-line{stroke:#bbb;stroke-width:1}",
            ".area-label{font:12px sans-serif;fill:#555;text-anchor:middle}",
            ".anchor{fill:#fff;stroke:#555;stroke-width:1.5}",
            ".set-piece{fill:#e8e2d0;stroke:#6b614d;stroke-width:1.5}",
            ".actor{fill:#2f6f9f;stroke:#12384f;stroke-width:1.5}",
            ".prop{fill:#7a4b9d;font:12px sans-serif}",
            ".label{font:13px sans-serif;fill:#111}",
            ".small{font:11px sans-serif;fill:#333}",
            ".diagnostic{font:12px sans-serif;fill:#8a3a00}",
            "</style>",
            f'<rect class="stage-boundary" x="{self.margin_px}" y="{self.margin_px}" '
            f'width="{stage.width * scale:g}" height="{stage.depth * scale:g}"/>',
        ]
        lines.extend(self._grid_lines(stage.width, stage.depth, scale))
        lines.extend(self._area_labels(snapshot, scale))
        lines.extend(self._anchors(snapshot, scale))
        lines.extend(self._set_pieces(snapshot, scale))
        lines.extend(self._placements(snapshot, scale))
        lines.extend(self._side_panel(snapshot, self.stage_width_px + 20, 30))
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def _grid_lines(self, width: float, depth: float, scale: float) -> list[str]:
        lines = []
        for x in (-width / 6, width / 6):
            sx, _ = self._project(Point3D(x, 0), width, depth, scale)
            lines.append(f'<line class="grid-line" x1="{sx:g}" y1="{self.margin_px:g}" x2="{sx:g}" y2="{self.margin_px + depth * scale:g}"/>')
        for y in (depth / 3, depth * 2 / 3):
            _, sy = self._project(Point3D(0, y), width, depth, scale)
            lines.append(f'<line class="grid-line" x1="{self.margin_px:g}" y1="{sy:g}" x2="{self.margin_px + width * scale:g}" y2="{sy:g}"/>')
        return lines

    def _area_labels(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for area_id, area in sorted(snapshot.areas.items()):
            x, y = self._project(area.center, snapshot.stage.width, snapshot.stage.depth, scale)
            lines.append(f'<text class="area-label" x="{x:g}" y="{y:g}">{escape(area_id)}</text>')
        return lines

    def _anchors(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for anchor_id, anchor in sorted(snapshot.anchors.items()):
            if anchor.at.point is None:
                continue
            x, y = self._project(anchor.at.point, snapshot.stage.width, snapshot.stage.depth, scale)
            lines.append(f'<circle class="anchor" cx="{x:g}" cy="{y:g}" r="5"/>')
            lines.append(f'<text class="small" x="{x + 7:g}" y="{y - 7:g}">{escape(anchor_id)}</text>')
            if anchor.at.point.z:
                lines.append(f'<text class="small" x="{x + 7:g}" y="{y + 7:g}">+{anchor.at.point.z:g}</text>')
        return lines

    def _set_pieces(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for set_id, set_piece in sorted(snapshot.set_pieces.items()):
            if set_piece.at.point is None:
                continue
            x, y = self._project(set_piece.at.point, snapshot.stage.width, snapshot.stage.depth, scale)
            width, depth = set_piece.size or (3.0, 2.0)
            lines.append(
                f'<rect class="set-piece" x="{x - width * scale / 2:g}" y="{y - depth * scale / 2:g}" '
                f'width="{width * scale:g}" height="{depth * scale:g}" rx="2"/>'
            )
            lines.append(f'<text class="small" x="{x:g}" y="{y:g}" text-anchor="middle">{escape(set_id)}</text>')
            if set_piece.at.point.z:
                lines.append(f'<text class="small" x="{x:g}" y="{y + 14:g}" text-anchor="middle">+{set_piece.at.point.z:g}</text>')
        return lines

    def _placements(self, snapshot: ResolvedSnapshot, scale: float) -> list[str]:
        lines = []
        for placement in snapshot.placements:
            if placement.offstage or placement.point is None:
                continue
            if placement.kind == "actor":
                lines.extend(self._actor(snapshot, placement, scale))
            elif placement.kind == "prop":
                lines.extend(self._prop(snapshot, placement, scale))
            elif placement.kind == "set_piece":
                lines.extend(self._placed_set_piece(snapshot, placement, scale))
        return lines

    def _actor(self, snapshot: ResolvedSnapshot, placement: ResolvedPlacement, scale: float) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        lines = [
            f'<circle class="actor" cx="{x:g}" cy="{y:g}" r="9"/>',
            f'<text class="label" x="{x + 12:g}" y="{y + 4:g}">{escape(placement.entity)}</text>',
        ]
        if placement.face:
            lines.append(f'<text class="small" x="{x + 12:g}" y="{y + 18:g}">face {escape(placement.face)}</text>')
        if placement.point.z:
            lines.append(f'<text class="small" x="{x - 10:g}" y="{y - 13:g}">+{placement.point.z:g}</text>')
        return lines

    def _prop(self, snapshot: ResolvedSnapshot, placement: ResolvedPlacement, scale: float) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        return [
            f'<text class="prop" x="{x + 6:g}" y="{y + 18:g}">◆ {escape(placement.entity)}</text>',
        ]

    def _placed_set_piece(self, snapshot: ResolvedSnapshot, placement: ResolvedPlacement, scale: float) -> list[str]:
        assert placement.point is not None
        x, y = self._project(placement.point, snapshot.stage.width, snapshot.stage.depth, scale)
        return [
            f'<rect class="set-piece" x="{x - 18:g}" y="{y - 10:g}" width="36" height="20" rx="2"/>',
            f'<text class="small" x="{x:g}" y="{y + 4:g}" text-anchor="middle">{escape(placement.entity)}</text>',
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
        return (
            self.margin_px + (point.x + stage_width / 2) * scale,
            self.margin_px + (stage_depth - point.y) * scale,
        )
