from __future__ import annotations

from dataclasses import dataclass

from stager.scriptwright.production_script import ProductionEntryKind, ProductionScript


@dataclass
class ProductionStagingExporter:
    """Export inline production blocking notes into a staging overlay."""

    def export(self, production: ProductionScript) -> str:
        lines: list[str] = []
        current_anchor: str | None = None
        beat_index = 0
        in_scene_snapshot = False

        def flush_beat() -> None:
            nonlocal current_anchor
            current_anchor = None

        for entry in production.entries:
            if entry.kind != ProductionEntryKind.BLOCKING:
                continue
            text = entry.text.strip()
            if not text:
                continue
            if self._is_scene_directive(text):
                flush_beat()
                if lines:
                    lines.append("")
                lines.append(text)
                beat_index = 0
                in_scene_snapshot = True
                continue
            if self._is_global_staging_directive(text):
                flush_beat()
                lines.append(text)
                continue

            rendered = self._render_blocking_lines(entry.targets, text)
            if in_scene_snapshot and all(self._is_snapshot_placement(line) for line in rendered):
                lines.extend(rendered)
                continue

            in_scene_snapshot = False
            if entry.production_id is None:
                raise RuntimeError(f"Blocking entry at line {entry.line_no} is missing a production id")
            if current_anchor != entry.production_id:
                beat_index += 1
                lines.append("")
                lines.append(f"b{beat_index} @ {entry.production_id}")
                current_anchor = entry.production_id
            lines.extend(rendered)

        text = "\n".join(lines).strip()
        return f"{text}\n" if text else ""

    def _is_scene_directive(self, text: str) -> bool:
        return text.startswith("scene ")

    def _is_global_staging_directive(self, text: str) -> bool:
        first = text.split(maxsplit=1)[0]
        return first in {
            "stage",
            "grid",
            "actor",
            "setup",
            "level",
            "anchor",
            "stair",
            "ramp",
            "lift",
            "piece",
            "set",
            "prop",
        }

    def _render_blocking_lines(self, targets: tuple[str, ...], text: str) -> list[str]:
        if targets == ("*",):
            return [text]
        return [f"{target} {text}" for target in targets]

    def _is_snapshot_placement(self, line: str) -> bool:
        parts = line.split()
        return len(parts) >= 2 and parts[1] in ("@", "offstage")
