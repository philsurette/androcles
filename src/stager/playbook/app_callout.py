from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stager.playbook.app_audio_asset import AppAudioAsset


@dataclass
class AppCallout:
    speaker: str
    audio: AppAudioAsset

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "audio": self.audio.to_dict(),
        }

