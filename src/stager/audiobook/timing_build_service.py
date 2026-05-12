"""Service for generating timing workbooks."""
from __future__ import annotations

from dataclasses import dataclass

from stager.audiobook.timings_xlsx import generate_xlsx
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.paths import PathConfig


@dataclass
class TimingBuildService:
    """Build timing spreadsheets for the current play."""

    paths: PathConfig

    def build(
        self,
        *,
        librivox: bool | None,
        segment_spacing_ms: int,
        callouts: bool,
        callout_spacing_ms: int,
        minimal_callouts: bool,
        include_decorations: bool,
    ) -> None:
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            librivox_override=librivox,
        ).resolve()
        effective_librivox = effective_build_type == "librivox"
        play = ProductionPlayLoader(paths_config=self.paths).load()
        part_ids = [p.part_no for p in play.parts if p.part_no is not None]
        if effective_librivox and len(part_ids) > 1:
            for part_no in part_ids:
                generate_xlsx(
                    librivox=effective_librivox,
                    part_no=part_no,
                    include_callouts=callouts,
                    callout_spacing_ms=callout_spacing_ms,
                    minimal_callouts=minimal_callouts,
                    segment_spacing_ms=segment_spacing_ms,
                    include_decorations=include_decorations,
                    paths_config=self.paths,
                )
            return
        generate_xlsx(
            librivox=effective_librivox,
            include_callouts=callouts,
            callout_spacing_ms=callout_spacing_ms,
            minimal_callouts=minimal_callouts,
            segment_spacing_ms=segment_spacing_ms,
            include_decorations=include_decorations,
            paths_config=self.paths,
        )
