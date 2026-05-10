from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CueSelection:
    speaker: str
    source_role: str
    text: str
    audio_path: Path
