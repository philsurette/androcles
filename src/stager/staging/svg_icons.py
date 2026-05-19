from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class StageSvgIconLibrary:
    default_actor_icon: str = "actor"
    default_set_piece_icon: str = "prop"
    default_prop_icon: str = "prop"

    def defs(self) -> list[str]:
        lines = ["<defs>"]
        for icon_id, body in sorted(self._symbols().items()):
            lines.append(f'<symbol id="stage-icon-{icon_id}" viewBox="0 0 24 24">{body}</symbol>')
        lines.append("</defs>")
        return lines

    def catalog_svg(self, *, columns: int = 6, cell_width: int = 150, cell_height: int = 108) -> str:
        icon_ids = sorted(self._symbols())
        rows = (len(icon_ids) + columns - 1) // columns
        width = columns * cell_width
        height = rows * cell_height
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            "<style>",
            ".cell{fill:#fff;stroke:#ddd;stroke-width:1}",
            ".icon{fill:none;stroke:#222;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}",
            ".label{font:12px sans-serif;fill:#111;text-anchor:middle}",
            "</style>",
            *self.defs(),
        ]
        for index, icon_id in enumerate(icon_ids):
            col = index % columns
            row = index // columns
            x = col * cell_width
            y = row * cell_height
            icon_x = x + cell_width / 2 - 18
            icon_y = y + 18
            lines.append(f'<rect class="cell" x="{x}" y="{y}" width="{cell_width}" height="{cell_height}"/>')
            lines.append(f'<use class="icon" href="#stage-icon-{escape(icon_id)}" x="{icon_x:g}" y="{icon_y:g}" width="36" height="36"/>')
            lines.append(f'<text class="label" x="{x + cell_width / 2:g}" y="{y + 78:g}">{escape(icon_id)}</text>')
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def icon_id(self, name: str | None, fallback: str) -> str:
        if name is None:
            return fallback
        candidate = self._normalize(name)
        if candidate in self._symbols():
            return candidate
        return self._ALIASES.get(candidate, fallback)

    def has_icon(self, name: str) -> bool:
        return self.icon_id(name, "") != ""

    def _normalize(self, name: str) -> str:
        return name.strip().lower().replace("_", "-")

    def _symbols(self) -> dict[str, str]:
        return self._SYMBOLS

    _ALIASES = {
        "furniture": "table",
        "set": "prop",
        "set-piece": "prop",
        "light": "practical-light",
        "weapon": "sword",
        "recorder": "radio",
        "tape-recorder": "radio",
    }

    _SYMBOLS = {
        "actor": '<circle cx="12" cy="7" r="3"/><path d="M12 10v8M8 14h8M9 22l3-4 3 4"/>',
        "actor-group": '<circle cx="8" cy="8" r="2.5"/><circle cx="16" cy="8" r="2.5"/><path d="M8 11v7M16 11v7M5 15h14"/>',
        "animal": '<path d="M5 15l3-5h7l4 5-2 3H7z"/><circle cx="9" cy="9" r="1"/><path d="M15 10l3-3M7 18l-2 3M17 18l2 3"/>',
        "bag": '<path d="M7 9h10l2 11H5z"/><path d="M9 9a3 3 0 0 1 6 0"/>',
        "basket": '<path d="M5 10h14l-2 10H7z"/><path d="M8 10a4 4 0 0 1 8 0M8 14h8M9 18h6"/>',
        "bed": '<path d="M4 8v11M20 12v7M4 14h16M7 10h5v4H7z"/>',
        "bell": '<path d="M8 17h8l-1-6a3 3 0 0 0-6 0z"/><path d="M10 20h4M12 7V4"/>',
        "bench": '<path d="M5 10h14v4H5zM7 14v6M17 14v6"/>',
        "book": '<path d="M5 5h7v15H5zM12 5h7v15h-7"/><path d="M8 8h2M15 8h2"/>',
        "bottle": '<path d="M10 4h4v5l2 3v8H8v-8l2-3z"/><path d="M10 7h4"/>',
        "box": '<path d="M5 9l7-4 7 4v9l-7 4-7-4z"/><path d="M5 9l7 4 7-4M12 13v9"/>',
        "cabinet": '<rect x="6" y="4" width="12" height="17"/><path d="M12 4v17M9 12h.5M14.5 12h.5"/>',
        "candle": '<path d="M10 9h4v10h-4z"/><path d="M12 3c3 3-2 4 0 6 2-2 3-4 0-6zM8 20h8"/>',
        "cane": '<path d="M14 5a3 3 0 0 0-6 0M8 5v16"/>',
        "chair": '<path d="M8 5h8v8H8zM7 13h10M9 13v7M15 13v7"/>',
        "chest": '<path d="M5 9h14v11H5z"/><path d="M7 9a5 5 0 0 1 10 0M5 13h14M12 13v3"/>',
        "cloak": '<path d="M12 4l5 5-2 12H9L7 9z"/><path d="M9 8h6"/>',
        "cloth": '<path d="M5 7c4-3 10 3 14 0v12c-4 3-10-3-14 0z"/>',
        "crate": '<path d="M5 5h14v14H5zM5 5l14 14M19 5L5 19"/>',
        "crown": '<path d="M5 17l1-10 5 5 3-7 4 7 4-5-2 10zM6 20h14"/>',
        "cue-point": '<circle cx="12" cy="12" r="8"/><path d="M12 7v6l4 3"/>',
        "cup": '<path d="M7 5h10v8a5 5 0 0 1-10 0z"/><path d="M17 8h2a2 2 0 0 1 0 4h-2M8 20h8"/>',
        "dagger": '<path d="M8 16l5-8 6-5-3 7-6 8z"/><path d="M6 14l5 5M4 21l4-4"/>',
        "desk": '<path d="M4 8h16v5H4zM6 13v7M18 13v7M9 13v4h6v-4"/>',
        "dummy": '<circle cx="12" cy="6" r="3"/><path d="M12 9v11M8 13h8M9 20h6"/>',
        "flag": '<path d="M7 4v17M7 5h11l-2 4 2 4H7"/>',
        "flower": '<circle cx="12" cy="9" r="2"/><circle cx="9" cy="9" r="2"/><circle cx="15" cy="9" r="2"/><path d="M12 11v9M12 16c-3-2-5-1-6 2M12 16c3-2 5-1 6 2"/>',
        "food": '<path d="M5 13a7 7 0 0 1 14 0zM4 16h16M8 6v4M12 5v5M16 6v4"/>',
        "handoff": '<path d="M5 15h6l2 2h6M7 11l4 4M17 11l-4 4"/><circle cx="12" cy="12" r="2"/>',
        "hat": '<path d="M5 16h14M8 16l2-8h4l2 8"/>',
        "hazard": '<path d="M12 4l9 16H3z"/><path d="M12 9v5M12 17v1"/>',
        "instrument": '<path d="M9 5v11a3 3 0 1 1-2-2.8V5zM9 5h8v9a3 3 0 1 1-2-2.8V5"/>',
        "key": '<circle cx="8" cy="12" r="4"/><path d="M12 12h8M17 12v3M20 12v2"/>',
        "lamp": '<path d="M9 4h6l3 7H6zM12 11v8M8 20h8"/>',
        "lantern": '<path d="M8 9h8v10H8zM10 9V6h4v3M10 13h4M12 13v4M9 21h6"/>',
        "letter": '<path d="M4 7h16v11H4zM4 7l8 7 8-7"/>',
        "mask": '<path d="M5 8c4-4 10-4 14 0v6c-2 5-5 6-7 6s-5-1-7-6z"/><path d="M8 12h3M13 12h3M10 16h4"/>',
        "music-stand": '<path d="M8 5h8l-1 8H9zM12 13v8M8 21h8"/>',
        "newspaper": '<path d="M5 5h14v14H5zM8 8h8M8 11h8M8 14h4M14 14h2"/>',
        "piano": '<path d="M4 7h16v10H4zM6 17v3M18 17v3M6 12h12M8 12v5M10 12v5M12 12v5M14 12v5M16 12v5"/>',
        "pistol": '<path d="M5 9h11l3 3h-7l-2 6H7l1-6H5z"/>',
        "practical-light": '<circle cx="12" cy="10" r="5"/><path d="M9 17h6M10 20h4M5 10H3M21 10h-2M12 3V1"/>',
        "preset": '<path d="M6 5h12v14H6z"/><path d="M9 9h6M9 12h6M9 15h3"/>',
        "prop": '<path d="M12 3l9 9-9 9-9-9z"/><path d="M8 12h8"/>',
        "puppet": '<circle cx="12" cy="8" r="4"/><path d="M8 4l-2-2M16 4l2-2M12 12v8M8 15h8"/>',
        "radio": '<rect x="5" y="9" width="14" height="10" rx="2"/><path d="M8 9l8-5M8 14h5M16 14h.5M16 17h.5"/>',
        "rifle": '<path d="M4 13h12l4-4M7 13l-2 4M14 13l2 4"/>',
        "rope": '<path d="M6 12c0-5 12-5 12 0s-12 5-12 0z"/><path d="M8 12c0 2 8 2 8 0"/>',
        "screen": '<path d="M5 5h14v14H5zM9 5v14M15 5v14"/>',
        "shield": '<path d="M12 4l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V7z"/>',
        "small-table": '<circle cx="12" cy="9" r="5"/><path d="M9 14l-2 6M15 14l2 6M12 14v6"/>',
        "smoke-source": '<path d="M7 19h10M8 16h8"/><path d="M9 14c-4-4 4-4 0-8M13 14c-4-4 4-4 0-8M17 14c-4-4 4-4 0-8"/>',
        "sofa": '<path d="M6 11V8a3 3 0 0 1 3-3h6a3 3 0 0 1 3 3v3M4 12h16v6H4zM6 18v2M18 18v2"/>',
        "spike-mark": '<path d="M4 12h16M12 4v16M7 7l10 10M17 7L7 17"/>',
        "staff": '<path d="M12 3v18M9 6a3 3 0 0 1 6 0"/>',
        "stool": '<circle cx="12" cy="8" r="5"/><path d="M9 13l-3 7M15 13l3 7M12 13v7"/>',
        "storage": '<path d="M5 8h14v12H5zM7 5h10v3M9 12h6"/>',
        "strike": '<path d="M5 19L19 5M7 5h12v12"/>',
        "sword": '<path d="M8 16l7-10 7-4-4 8-8 8z"/><path d="M6 14l6 6M3 21l5-5"/>',
        "table": '<path d="M4 8h16v5H4zM7 13v7M17 13v7"/>',
        "telephone": '<path d="M7 7c3-3 7-3 10 0l-2 3c-2-1-4-1-6 0z"/><path d="M8 12h8l2 7H6z"/>',
        "tray": '<path d="M5 15h14M8 15a4 4 0 0 1 8 0M12 9v2"/>',
        "umbrella": '<path d="M4 12a8 8 0 0 1 16 0zM12 12v7a2 2 0 0 0 4 0"/>',
    }
