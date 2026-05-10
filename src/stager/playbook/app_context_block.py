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
    audio: AppAudioAsset

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "block_id": self.block_id,
            "kind": self.kind,
            "speaker": self.speaker,
            "text": self.text,
            "audio": self.audio.to_dict(),
        }
