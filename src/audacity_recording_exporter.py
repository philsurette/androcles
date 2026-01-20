from __future__ import annotations

import logging
from dataclasses import dataclass, field

from audacityctl.exporter import Exporter, ExportContext
from audacityctl.project import AudacityProject

import paths


@dataclass
class AudacityRecordingExporter:
    """Export Audacity projects in a play's recordings folder to WAV files."""

    paths: paths.PathConfig = field(default_factory=paths.current)
    export_extension: str = ".wav"
    exporter: Exporter | None = None
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        if self.exporter is None:
            self.exporter = Exporter(export_extension=self.export_extension)

    def export_recordings(self) -> None:
        recordings_dir = self.paths.recordings_dir
        self._logger.info(
            "Checking Audacity exports in %s",
            recordings_dir,
        )
        context = ExportContext(
            root_folder=str(recordings_dir),
            export_extension=self.export_extension,
            export_folder_name="",
        )
        self.exporter.identify_needed_exports(context)
        try:
            self._export_context(context)
        finally:
            context.log_summary()

    def _export_context(self, context: ExportContext) -> None:
        if context.dry_run:
            for aup3_path in context.get_exportable_paths():
                context.add_exported(aup3_path)
            return
        exportables = context.get_exportable_paths()
        if not exportables:
            self._logger.info("All exports are up to date")
            return
        with self.exporter.manager.open_client() as client:
            for aup3_path in exportables:
                try:
                    with client.open_project(
                        AudacityProject(
                            path=aup3_path,
                            export_folder_name=context.export_folder_name,
                            export_extension=context.export_extension,
                        )
                    ):
                        client.export_open_project()
                    context.add_exported(aup3_path)
                except RuntimeError as exc:
                    context.add_error(aup3_path, exc)
                    self._logger.error("Unable to export %s", aup3_path)
                    raise
