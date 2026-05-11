from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from audacity_ctl.audacity import Audacity
from audacity_ctl.project import AudacityProject

from stager.shared import paths


@dataclass
class AudacityRecordingExporter:
    """Export Audacity projects in a play's recordings folder to WAV files."""

    paths: paths.PathConfig = field(default_factory=paths.current)
    export_extension: str = "wav"
    audacity: Audacity | None = None
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self.export_extension = self.export_extension.lstrip(".")
        if self.audacity is None:
            self.audacity = Audacity()

    def export_recordings(self, *, force: bool = False, role: str | None = None) -> None:
        recordings_dir = self.paths.recordings_dir
        self._logger.info(
            "Checking Audacity exports in %s",
            paths.display_path(recordings_dir),
        )
        exported: list[Path] = []
        skipped: list[Path] = []
        errors: list[tuple[Path, Exception]] = []
        try:
            aup3_paths = self._collect_projects(recordings_dir=recordings_dir, role=role)
            if not aup3_paths:
                self._logger.info("No Audacity projects found in %s", paths.display_path(recordings_dir))
                return
            exportable_projects: list[AudacityProject] = []
            for aup3_path in aup3_paths:
                project = AudacityProject(
                    path=aup3_path,
                    export_extension=self.export_extension,
                )
                if not force and project.export_is_up_to_date():
                    skipped.append(aup3_path)
                else:
                    exportable_projects.append(project)
            if not exportable_projects:
                self._logger.info("All exports are up to date")
                return
            with self.audacity.open() as client:
                for project in exportable_projects:
                    try:
                        with client.open_project(project=project):
                            client.export_project()
                        exported.append(project.path)
                    except RuntimeError as exc:
                        errors.append((project.path, exc))
                        self._logger.error("Unable to export %s", paths.display_path(project.path))
                        raise
        finally:
            self._log_summary(
                exported=exported,
                skipped=skipped,
                errors=errors,
            )

    def _collect_projects(self, recordings_dir: Path, *, role: str | None = None) -> list[Path]:
        projects = sorted(
            path
            for path in recordings_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".aup3"
        )
        if role is None:
            return projects
        return [path for path in projects if path.stem == role]

    def _log_summary(
        self,
        exported: list[Path],
        skipped: list[Path],
        errors: list[tuple[Path, Exception]],
    ) -> None:
        if not exported and not skipped and not errors:
            return
        self._logger.info(
            "Audacity export summary: %s exported, %s skipped, %s errors",
            len(exported),
            len(skipped),
            len(errors),
        )
