from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlaybookAudioWorkItem:
    source_path: Path
    role: str
    segment_id: str
    category: str

