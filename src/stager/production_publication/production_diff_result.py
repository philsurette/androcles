from __future__ import annotations

from dataclasses import dataclass

from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change_report import ProductionChangeReport
from stager.production_publication.production_version import ProductionVersion


@dataclass(frozen=True)
class ProductionDiffResult:
    change_report: ProductionChangeReport
    current_version: PublishedVersion | None
    working_production_version: ProductionVersion | None

