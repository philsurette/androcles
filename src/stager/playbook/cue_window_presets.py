from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from stager.shared import paths


@dataclass
class CueWindowPresets:
    preset_path: Path = (
        paths.project_root() / "planning" / "specs" / "cue_window_presets.json"
    )

    def timed_windows_ms(self) -> list[int]:
        data = json.loads(self.preset_path.read_text(encoding="utf-8"))
        presets: list[dict[str, Any]] = data["cue_window_presets"]
        return [
            int(preset["window_ms"])
            for preset in presets
            if preset["window_ms"] is not None and preset["window_ms"] > 0
        ]
