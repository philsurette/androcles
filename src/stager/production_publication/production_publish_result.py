from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change_report import ProductionChangeReport


@dataclass(frozen=True)
class ProductionPublishResult:
    version: PublishedVersion
    change_report: ProductionChangeReport
    id_updates: dict[str, str]
    recording_request_paths: tuple[Path, ...] = ()
