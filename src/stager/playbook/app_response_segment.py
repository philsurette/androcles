from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stager.playbook.app_audio_asset import AppAudioAsset


@dataclass
class AppResponseSegment:
    id: str
    owners: list[str]
    text: str
    audio: AppAudioAsset
    segment_id: str | None = None
    content_hash: str | None = None
    simultaneous: bool = False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "owners": list(self.owners),
            "text": self.text,
            "audio": self.audio.to_dict(),
        }
        if self.segment_id is not None:
            data["segment_id"] = self.segment_id
        if self.content_hash is not None:
            data["content_hash"] = self.content_hash
        if self.simultaneous:
            data["simultaneous"] = True
        return data
