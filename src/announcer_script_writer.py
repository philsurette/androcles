#!/usr/bin/env python3
"""Generate announcer script markdown from an Announcer."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from announcer import Announcer, LibrivoxAnnouncer


@dataclass
class AnnouncerScriptWriter:
    announcer: Announcer
    paths: paths.PathConfig = field(default_factory=paths.current)

    def __post_init__(self) -> None:
        if self.announcer is None:
            raise RuntimeError("announcer is required for AnnouncerScriptWriter")

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write announcer script to build/<play>/markdown/roles/_ANNOUNCER.md."""
        target = out_path or (self.paths.markdown_roles_dir / "_ANNOUNCER.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        reader = self.announcer.play.reading_metadata.reader_for_id(self.announcer.announcer_role)
        read_by = [f"announcements read by {reader.reader or '<name>'}\n"]
        paragraphs = [a.text for a in self.announcer.announcements()]
        content = "\n\n".join(read_by + paragraphs).rstrip() + "\n"
        target.write_text(content, encoding="utf-8")
        return target
