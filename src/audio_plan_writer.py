from dataclasses import dataclass, field
from audio_plan import AudioPlan
from pathlib import Path
from typing import List
from clip import *
from chapter import Chapter
@dataclass
class AudioPlanWriter:
    plan: AudioPlan
    def write(self, path: Path) -> None:
        """Persist plan items to a text file for inspection."""
        lines: List[str] = []
        for item in self.plan.items:
            mins = item.offset_ms // 60000
            secs_ms = item.offset_ms % 60000
            prefix = f"{mins:02d}:{secs_ms/1000:06.3f} "
            if isinstance(item, (CalloutClip, SegmentClip, Silence)):
                lines.append(prefix + str(item))
            elif isinstance(item, Chapter):
                suffix = f" {item.title}" if item.title else ""
                lines.append(f"{prefix}[chapter]{suffix}")
        content = "\n".join(lines)
        if content:
            content += "\n"
        path.write_text(content, encoding="utf-8")  