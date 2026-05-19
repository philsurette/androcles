from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from stager.production_publication.production_version import ProductionVersion
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths


@dataclass(frozen=True)
class AudioPlayBuildManifest:
    build_timestamp: str
    production_source: str
    production_version: str | None
    audio_format: str
    audio_source: str
    paths: tuple[str, ...]
    part: str | None = None
    voice_profiles: bool = False
    voice_actor: str | None = None
    normalized: bool = False

    def to_dict(self) -> dict:
        return {
            "build": {
                "buildTimestamp": self.build_timestamp,
            },
            "production": {
                "source": self.production_source,
                "version": self.production_version,
            },
            "options": {
                "part": self.part,
                "audioFormat": self.audio_format,
                "audioSource": self.audio_source,
                "voiceProfiles": self.voice_profiles,
                "voiceActor": self.voice_actor,
                "normalized": self.normalized,
            },
            "paths": list(self.paths),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"


@dataclass(frozen=True)
class AudioPlayBuildManifestWriter:
    paths_config: paths.PathConfig

    @property
    def manifest_path(self) -> Path:
        return self.paths_config.audio_play_dir / "audioplay_manifest.json"

    def write(
        self,
        *,
        out_paths: tuple[Path, ...],
        part: str | None,
        audio_format: str,
        audio_source: str,
        voice_profiles: bool,
        voice_actor: str | None,
        normalized: bool,
    ) -> Path:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = AudioPlayBuildManifest(
            build_timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            production_source=self._production_source(),
            production_version=self._production_version(),
            part=part,
            audio_format=audio_format,
            audio_source=audio_source,
            voice_profiles=voice_profiles,
            voice_actor=voice_actor,
            normalized=normalized,
            paths=tuple(paths.display_path(path) for path in out_paths),
        )
        self.manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        return self.manifest_path

    def _production_source(self) -> str:
        try:
            current_path = ProductionVersionStore(self.paths_config).current_production_path()
        except RuntimeError:
            return "working"
        if current_path is not None and self.paths_config.production_markdown.resolve() == current_path.resolve():
            return "published"
        return "working"

    def _production_version(self) -> str | None:
        if not self.paths_config.production_markdown.exists():
            return None
        metadata = ProductionScriptParser(self.paths_config.production_markdown).parse_path().metadata
        value = metadata.get("production_version")
        if value is None:
            return None
        return str(ProductionVersion.parse(value))
