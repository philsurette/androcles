from __future__ import annotations

from typing import Protocol


class RecordingRequestProgressReporter(Protocol):
    def start_item_building(self, total: int) -> None:
        raise NotImplementedError

    def item_built(self, item_id: str, sequence: int) -> None:
        raise NotImplementedError

    def finish_item_building(self) -> None:
        raise NotImplementedError

