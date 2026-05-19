from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths
from stager.staging.production_exporter import ProductionStagingExporter


@dataclass(frozen=True)
class StagingExportResult:
    output_path: Path
    written: bool
    removed_stale: bool


class StagingExportService:
    def __init__(self, *, paths_config: paths.PathConfig) -> None:
        self.paths_config = paths_config

    def export(self) -> StagingExportResult:
        output_path = self.output_path()
        if not self.paths_config.production_markdown.exists():
            raise RuntimeError(
                "Missing locked production script "
                f"{paths.display_path(self.paths_config.production_markdown)}; "
                "run './main scriptwright lock' first."
            )
        production = ProductionScriptParser(source_path=self.paths_config.production_markdown).parse_path()
        text = ProductionStagingExporter().export(production)
        if not text.strip():
            removed_stale = False
            if output_path.exists():
                output_path.unlink()
                removed_stale = True
            return StagingExportResult(output_path=output_path, written=False, removed_stale=removed_stale)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        return StagingExportResult(output_path=output_path, written=True, removed_stale=False)

    def output_path(self) -> Path:
        return self.paths_config.build_dir / "staging" / "staging.txt"
