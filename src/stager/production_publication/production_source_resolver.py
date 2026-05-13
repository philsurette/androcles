from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from stager.production_publication.production_version_store import ProductionVersionStore
from stager.shared import paths

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedProductionSource:
    kind: str
    path: Path


@dataclass
class ProductionSourceResolver:
    paths_config: paths.PathConfig

    VALID_SOURCES = {"auto", "published", "working"}

    def resolve(self, source: str = "auto") -> ResolvedProductionSource:
        source_key = source.strip().lower()
        if source_key not in self.VALID_SOURCES:
            raise ValueError(
                f"Unknown production source: {source}. Choose from auto, published, working."
            )
        if source_key == "working":
            resolved = ResolvedProductionSource(kind="working", path=self.paths_config.production_markdown)
            self._log_selected(resolved)
            return resolved

        published_path = ProductionVersionStore(self.paths_config).current_production_path()
        if published_path is not None:
            resolved = ResolvedProductionSource(kind="published", path=published_path)
            self._log_selected(resolved)
            return resolved

        if source_key == "published":
            raise RuntimeError("No published production version exists.")

        resolved = ResolvedProductionSource(kind="working", path=self.paths_config.production_markdown)
        logger.warning(
            "No published production version exists; using working production source %s",
            paths.display_path(resolved.path),
        )
        return resolved

    def apply_to(self, source: str = "auto") -> paths.PathConfig:
        resolved = self.resolve(source)
        self.paths_config.production_markdown = resolved.path
        return self.paths_config

    def _log_selected(self, resolved: ResolvedProductionSource) -> None:
        logger.info(
            "Using %s production source %s",
            resolved.kind,
            paths.display_path(resolved.path),
        )
