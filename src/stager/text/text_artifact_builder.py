"""Build markdown text artifacts for a play."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from stager.shared import paths
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.text.announcer import select_announcer
from stager.text.announcer_script_writer import AnnouncerScriptWriter
from stager.text.callout_script_writer import CalloutScriptWriter
from stager.text.narrator_markdown_writer import NarratorMarkdownWriter
from stager.text.play_markdown_writer import PlayMarkdownWriter
from stager.text.role_markdown_writer import RoleMarkdownWriter


logger = logging.getLogger(__name__)


@dataclass
class TextArtifactBuilder:
    """Build the markdown artifacts emitted by the Stager text workflow."""

    paths: paths.PathConfig

    def _load_play(self):
        return ProductionPlayLoader(paths_config=self.paths).load()

    def build_all(self, *, line_no_prefix: bool = True, build_type: str | None = None) -> None:
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            explicit_build_type=build_type,
        ).resolve()
        self.write_play(line_no_prefix=line_no_prefix)
        self.write_roles(line_no_prefix=line_no_prefix)
        self.write_callout_script()
        self.write_announcer(build_type=effective_build_type)

    def write_play(self, *, line_no_prefix: bool = True) -> Path:
        play = self._load_play()
        writer = PlayMarkdownWriter(play, paths=self.paths, prefix_line_nos=line_no_prefix)
        path = writer.to_markdown()
        logger.info("wrote %s", paths.display_path(path))
        return path

    def write_roles(self, *, line_no_prefix: bool = True) -> list[Path]:
        play = self._load_play()
        written_paths: list[Path] = []
        for role in play.roles:
            writer = RoleMarkdownWriter(
                role,
                reading_metadata=getattr(play, "reading_metadata", None),
                paths=self.paths,
                prefix_line_nos=line_no_prefix,
            )
            path = writer.to_markdown()
            written_paths.append(path)
            logger.debug("wrote %s", paths.display_path(path))
        narrator_path = NarratorMarkdownWriter(
            play,
            reading_metadata=getattr(play, "reading_metadata", None),
            paths=self.paths,
            prefix_line_nos=line_no_prefix,
        ).to_markdown()
        written_paths.append(narrator_path)
        if written_paths:
            role_names = [r.name for r in play.roles] + ["_NARRATOR"]
            logger.info(
                "created .md files in %s for %s",
                paths.display_path(written_paths[0].parent),
                ",".join(role_names),
            )
        return written_paths

    def write_callout_script(self) -> Path:
        play = self._load_play()
        writer = CalloutScriptWriter(play, paths=self.paths)
        path = writer.to_markdown()
        logger.info("wrote %s", paths.display_path(path))
        return path

    def write_announcer(self, *, build_type: str | None = None) -> Path:
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            explicit_build_type=build_type,
        ).resolve()
        play = self._load_play()
        announcer = select_announcer(play, build_type=effective_build_type)
        writer = AnnouncerScriptWriter(announcer=announcer, paths=self.paths)
        path = writer.to_markdown()
        logger.info("wrote %s", paths.display_path(path))
        return path
