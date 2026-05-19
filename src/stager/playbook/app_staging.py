from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AppStaging:
    included: bool
    format: str
    format_version: str
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "included": self.included,
            "format": self.format,
            "format_version": self.format_version,
            "manifest_path": self.manifest_path,
        }
