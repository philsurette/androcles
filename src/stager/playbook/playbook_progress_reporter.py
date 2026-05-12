from __future__ import annotations

from typing import Protocol


class PlaybookProgressReporter(Protocol):
    def start_audio_packaging(self, total: int) -> None:
        raise NotImplementedError

    def audio_packaged(self, role: str, segment_id: str, category: str) -> None:
        raise NotImplementedError

    def finish_audio_packaging(self) -> None:
        raise NotImplementedError

