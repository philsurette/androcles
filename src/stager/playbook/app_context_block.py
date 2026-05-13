from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stager.playbook.app_audio_asset import AppAudioAsset


@dataclass
class AppContextBlock:
    id: str
    part_id: int | None
    block_id: str
    kind: str
    speaker: str
    text: str
    audio: AppAudioAsset | None
    content_hash: str | None = None
    targets: list[str] | None = None
    placement: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "part_id": self.part_id,
            "block_id": self.block_id,
            "kind": self.kind,
            "speaker": self.speaker,
            "text": self.text,
        }
        if self.audio is not None:
            data["audio"] = self.audio.to_dict()
        if self.content_hash is not None:
            data["content_hash"] = self.content_hash
        if self.targets is not None:
            data["targets"] = list(self.targets)
        if self.placement is not None:
            data["placement"] = self.placement
        return data
