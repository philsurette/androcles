from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change_report import ProductionChangeReport
from stager.shared import paths


@dataclass
class ProductionVersionStore:
    paths_config: paths.PathConfig

    @property
    def history_dir(self) -> Path:
        return self.paths_config.build_dir / "production-history"

    @property
    def versions_dir(self) -> Path:
        return self.history_dir / "versions"

    @property
    def current_path(self) -> Path:
        return self.history_dir / "current.json"

    def current(self) -> PublishedVersion | None:
        if not self.current_path.exists():
            return None
        current = json.loads(self.current_path.read_text(encoding="utf-8"))
        return self.load_version(current["version"])

    def load_version(self, version: int | str) -> PublishedVersion:
        version_no = self._version_number(version)
        manifest_path = self._version_dir(version_no) / "manifest.json"
        return PublishedVersion.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))

    def list_versions(self) -> list[PublishedVersion]:
        if not self.versions_dir.exists():
            return []
        versions: list[PublishedVersion] = []
        for version_dir in sorted(self.versions_dir.iterdir()):
            if version_dir.is_dir() and (version_dir / "manifest.json").exists():
                versions.append(
                    PublishedVersion.from_dict(
                        json.loads((version_dir / "manifest.json").read_text(encoding="utf-8"))
                    )
                )
        return versions

    def save(
        self,
        *,
        version: PublishedVersion,
        source_path: Path,
        change_report: ProductionChangeReport,
    ) -> Path:
        version_dir = self._version_dir(version.version)
        version_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, version_dir / "production.md")
        (version_dir / "manifest.json").write_text(
            json.dumps(version.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        if change_report.base_version is not None:
            (version_dir / f"changes_from_v{change_report.base_version:04d}.json").write_text(
                json.dumps(change_report.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.current_path.write_text(
            json.dumps(
                {
                    "version": version.version,
                    "label": version.label,
                    "published_at": version.published_at,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return version_dir

    def restore_source(self, version: int | str) -> Path:
        version_no = self._version_number(version)
        source = self._version_dir(version_no) / "production.md"
        if not source.exists():
            raise RuntimeError(f"Unknown published production version: {version}")
        self.paths_config.production_markdown.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, self.paths_config.production_markdown)
        return self.paths_config.production_markdown

    def next_version_number(self) -> int:
        current = self.current()
        return 1 if current is None else current.version + 1

    def _version_dir(self, version: int) -> Path:
        return self.versions_dir / f"v{version:04d}"

    def _version_number(self, version: int | str) -> int:
        if isinstance(version, int):
            return version
        label = version.strip()
        if label.startswith("v"):
            label = label[1:]
        return int(label)
