from __future__ import annotations

from typing import Protocol


class ProgressReporter(Protocol):
    def start(self, total: int, description: str) -> None:
        raise NotImplementedError

    def advance(self, description: str | None = None) -> None:
        raise NotImplementedError

    def finish(self, description: str | None = None) -> None:
        raise NotImplementedError

