#!/usr/bin/env python3
"""Generate announcer YAML for Librivox-style recordings."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruamel import yaml
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString

import paths
from play import Play


@dataclass
class AnnouncerScriptWriter:
    play: Play

    def __post_init__(self) -> None:
        if self.play is None:
            raise RuntimeError("play cannot be None for AnnouncerScriptWriter")

    def _sections_block(self) -> CommentedMap:
        """
        Build nested section entries keyed by number with start/end keys.
        Sections are derived from numbered parts in the play.
        """
        sections: CommentedMap = CommentedMap()
        numbered_parts = [p for p in self.play.parts if p.part_no is not None]
        for part in numbered_parts:
            sec_no = part.part_no
            entry = CommentedMap()
            entry["start"] = LiteralScalarString(f"section {sec_no}")
            entry["end"] = LiteralScalarString(f"end of section {sec_no}")
            sections[sec_no] = entry
        return sections

    def to_yaml(self, out_path: Path | None = None) -> Path:
        """Write announcer YAML into build/<play>/markdown/roles/_ANNOUNCER.yaml."""
        target = out_path or (paths.MARKDOWN_ROLES_DIR / "_ANNOUNCER.yaml")
        target.parent.mkdir(parents=True, exist_ok=True)

        title = self.play.title
        author = self.play.author

        content = CommentedMap()
        content["title"] = LiteralScalarString(title)
        content["author"] = LiteralScalarString(author)
        content["end_of_recording"] = LiteralScalarString(f"End of \"{title}\" by {author}.")

        librivox = CommentedMap()
        librivox["this_is_a_librivox_recording"] = LiteralScalarString("This is a Librivox Recording.")
        librivox["all_librivox_recordings"] = LiteralScalarString("All Librivox Recordings are in the public domain.")
        librivox["for_more_information"] = LiteralScalarString("For more information or to volunteer, please visit librivox.org.")
        librivox["section_pd_declaration"] = LiteralScalarString("This librivox recording is in the public domain.")
        librivox["section_end_suffix"] = LiteralScalarString(f"of \"{title}\" by {author}")
        librivox["sections"] = self._sections_block()
        content["librivox"] = librivox

        yml = yaml.YAML()  # round-trip to preserve ordering and literal scalars
        yml.default_flow_style = False
        yml.width = 4096
        with target.open("w", encoding="utf-8") as fh:
            yml.dump(content, fh)
        return target
