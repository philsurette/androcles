"""Service for generating legacy cue audio files."""
from __future__ import annotations

from dataclasses import dataclass

from stager.cues.cue_builder import CueBuilder
from stager.shared.paths import PathConfig
from stager.text.play_text_parser import PlayTextParser


@dataclass
class CueBuildService:
    """Build cue files for one role or all rehearsal roles."""

    paths: PathConfig

    def build(
        self,
        *,
        role: str | None = None,
        response_delay_ms: int = 2000,
        max_cue_size_ms: int = 5000,
        include_prompts: bool = True,
        callout_spacing_ms: int = 300,
    ) -> None:
        play = PlayTextParser(paths_config=self.paths).parse()
        builder = CueBuilder(
            play,
            paths=self.paths,
            response_delay_ms=response_delay_ms,
            max_cue_size_ms=max_cue_size_ms,
            include_prompts=include_prompts,
            callout_spacing_ms=callout_spacing_ms,
        )
        roles = [role] if role else [r.name for r in play.roles] + ["_NARRATOR"]
        for role_name in roles:
            builder.build_cues(role_name)
