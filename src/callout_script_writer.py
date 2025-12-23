#!/usr/bin/env python3
"""Emit the _CALLER.md callout script."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import paths
from play import Play
from block import RoleBlock


@dataclass
class CalloutScriptWriter:
    play: Play

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """
        Write _CALLER.md listing each callout to record in a single _CALLOUT.wav.
        Callouts are sorted alphabetically and use the callout name as the id.
        """
        target = out_path or (paths.MARKDOWN_ROLES_DIR / "_CALLER.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        callouts: list[str] = []
        seen: set[str] = set()
        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            if blk.callout is None:
                continue
            if blk.callout in seen:
                continue
            seen.add(blk.callout)
            callouts.append(blk.callout)

        lines: list[str] = []
        for name in sorted(callouts):
            lines.append(f"- {name}")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
