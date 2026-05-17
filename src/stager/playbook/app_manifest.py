from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from stager.playbook.app_audio_asset import AppAudioAsset
from stager.playbook.app_context_block import AppContextBlock
from stager.playbook.app_play import AppPlay
from stager.playbook.app_production import AppProduction
from stager.playbook.app_reading import AppReading
from stager.playbook.app_role import AppRole
from stager.playbook.app_section import AppSection


@dataclass
class AppManifestBuild:
    buildId: str
    buildTimestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "buildId": self.buildId,
            "buildTimestamp": self.buildTimestamp,
        }


@dataclass
class AppManifest:
    play: AppPlay
    reading: AppReading
    build: AppManifestBuild
    production: AppProduction
    roles: list[AppRole] = field(default_factory=list)
    context: list[AppContextBlock] = field(default_factory=list)
    sections: list[AppSection] = field(default_factory=list)
    assets: list[AppAudioAsset] = field(default_factory=list)
    schema_version: int = 1
    format_version: str = "1.0.0"
    package_type: str = "playbook"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "format_version": self.format_version,
            "package_type": self.package_type,
            "production": self.production.to_dict(),
            "play": self.play.to_dict(),
            "reading": self.reading.to_dict(),
            "build": self.build.to_dict(),
            "sections": [section.to_dict() for section in self.sections],
            "context": [context_block.to_dict() for context_block in self.context],
            "roles": [role.to_dict() for role in self.roles],
            "assets": [asset.to_dict() for asset in self.assets],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"
