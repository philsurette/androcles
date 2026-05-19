from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change_report import ProductionChangeReport
from stager.production_publication.production_version import ProductionVersion
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
        production_version = current.get("production_version")
        if production_version is None:
            legacy_label = current.get("label") or current.get("version")
            detail = f" ({legacy_label})" if legacy_label is not None else ""
            raise RuntimeError(
                f"Legacy production history is not supported{detail}: "
                f"{paths.display_path(self.current_path)}"
            )
        return self.load_version(production_version)

    def current_production_path(self) -> Path | None:
        current = self.current()
        if current is None:
            return None
        return self._version_dir(current.production_version) / "production.md"

    def load_version(self, version: int | str) -> PublishedVersion:
        production_version = self._resolve_version(version)
        manifest_path = self._version_dir(production_version) / "manifest.json"
        return PublishedVersion.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))

    def load_change_report(self, version: int | str) -> ProductionChangeReport | None:
        published = self.load_version(version)
        if published.parent_production_version is None:
            return None
        report_path = (
            self._version_dir(published.production_version)
            / f"changes_from_{published.parent_production_version.history_directory_name}.json"
        )
        if not report_path.exists():
            return None
        return ProductionChangeReport.from_dict(json.loads(report_path.read_text(encoding="utf-8")))

    def list_versions(self) -> list[PublishedVersion]:
        if not self.versions_dir.exists():
            return []
        versions: list[PublishedVersion] = []
        for version_dir in sorted(self.versions_dir.iterdir()):
            if version_dir.is_dir() and (version_dir / "manifest.json").exists():
                data = json.loads((version_dir / "manifest.json").read_text(encoding="utf-8"))
                if data.get("production_version") is None and self._is_legacy_manifest(data):
                    continue
                versions.append(PublishedVersion.from_dict(data))
        return versions

    def forked_sequences(self) -> dict[int, tuple[ProductionVersion, ...]]:
        versions_by_sequence: dict[int, list[ProductionVersion]] = {}
        for version in self.list_versions():
            versions_by_sequence.setdefault(version.version, []).append(version.production_version)
        return {
            sequence: tuple(sorted(production_versions))
            for sequence, production_versions in versions_by_sequence.items()
            if len({production_version.publication_id for production_version in production_versions}) > 1
        }

    def assert_no_forks(self) -> None:
        forks = self.forked_sequences()
        if not forks:
            return
        lines = ["Forked production history detected."]
        for sequence, versions in sorted(forks.items()):
            labels = ", ".join(str(version) for version in versions)
            lines.append(f"  sequence {sequence}: {labels}")
        raise RuntimeError("\n".join(lines))

    def save(
        self,
        *,
        version: PublishedVersion,
        source_path: Path,
        change_report: ProductionChangeReport,
        source_text: str | None = None,
    ) -> Path:
        version_dir = self._version_dir(version.production_version)
        version_dir.mkdir(parents=True, exist_ok=True)
        if source_text is None:
            shutil.copy2(source_path, version_dir / "production.md")
        else:
            (version_dir / "production.md").write_text(source_text, encoding="utf-8")
        (version_dir / "manifest.json").write_text(
            json.dumps(version.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        if change_report.base_version is not None:
            base_version = self._version_for_sequence(change_report.base_version)
            base_name = base_version.history_directory_name if base_version is not None else f"{change_report.base_version:04d}"
            (version_dir / f"changes_from_{base_name}.json").write_text(
                json.dumps(change_report.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.current_path.write_text(
            json.dumps(
                {
                    "production_version": str(version.production_version),
                    "sequence": version.production_version.sequence,
                    "publication_id": version.production_version.publication_id,
                    "parent_production_version": (
                        str(version.parent_production_version)
                        if version.parent_production_version is not None
                        else None
                    ),
                    "label": version.label,
                    "published_at": version.published_at,
                    "change_summary": version.change_summary,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return version_dir

    def restore_source(self, version: int | str) -> Path:
        production_version = self._resolve_version(version)
        source = self._version_dir(production_version) / "production.md"
        if not source.exists():
            raise RuntimeError(f"Unknown published production version: {version}")
        self.paths_config.production_markdown.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, self.paths_config.production_markdown)
        return self.paths_config.production_markdown

    def next_version_number(self) -> int:
        current = self.current()
        return 1 if current is None else current.version + 1

    def next_production_version(self, publication_id: str) -> ProductionVersion:
        current = self.current()
        parent = current.production_version if current is not None else None
        return ProductionVersion.next_after(parent, publication_id)

    def _version_dir(self, version: ProductionVersion) -> Path:
        return self.versions_dir / version.history_directory_name

    def _resolve_version(self, version: int | str) -> ProductionVersion:
        if isinstance(version, int):
            resolved = self._version_for_sequence(version)
            if resolved is None:
                raise RuntimeError(f"Unknown published production version: {version}")
            return resolved
        label = version.strip()
        if label.startswith("v") and label[1:].isdigit():
            raise RuntimeError(f"Legacy production version labels are not supported: {version}")
        if "@" in label:
            return ProductionVersion.parse(label)
        if "-" in label:
            sequence_text, _, publication_id = label.partition("-")
            return ProductionVersion(int(sequence_text), publication_id)
        if label.isdigit():
            resolved = self._version_for_sequence(int(label))
            if resolved is None:
                raise RuntimeError(f"Unknown published production version: {version}")
            return resolved
        raise RuntimeError(f"Unknown published production version: {version}")

    def _version_for_sequence(self, sequence: int) -> ProductionVersion | None:
        matches = [version.production_version for version in self.list_versions() if version.version == sequence]
        if not matches:
            return None
        if len(matches) > 1:
            raise RuntimeError(f"Forked production history has multiple versions for sequence {sequence}")
        return matches[0]

    def _is_legacy_manifest(self, data: dict) -> bool:
        label = data.get("label")
        return isinstance(label, str) and label.startswith("v") and label[1:].isdigit()
