from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from stager.playbook.app_audio_asset import AppAudioAsset
from stager.playbook.app_play import AppPlay
from stager.playbook.app_reading import AppReading
from stager.playbook.app_role import AppRole


@dataclass
class AppManifest:
    play: AppPlay
    reading: AppReading
    roles: list[AppRole] = field(default_factory=list)
    assets: list[AppAudioAsset] = field(default_factory=list)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "play": self.play.to_dict(),
            "reading": self.reading.to_dict(),
            "roles": [role.to_dict() for role in self.roles],
            "assets": [asset.to_dict() for asset in self.assets],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"
