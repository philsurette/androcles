#!/usr/bin/env python3
"""Emit callouts and associated roles to markdown."""
from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict
from pathlib import Path

import paths
from play import Play
from block import RoleBlock


@dataclass
class CalloutsMarkdownWriter:
    play: Play

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write callouts.md listing callouts and their associated roles."""
        target = out_path or (paths.MARKDOWN_DIR / "_CALLOUTS.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        callouts: OrderedDict[str, list[str]] = OrderedDict()

        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            callout = blk.callout
            if callout is None:
                continue
            roles = blk.role_names if getattr(blk, "role_names", None) else [blk.primary_role]
            if callout not in callouts:
                callouts[callout] = []
            for role in roles:
                if role not in callouts[callout]:
                    callouts[callout].append(role)

        lines: list[str] = []
        for callout in sorted(callouts.keys()):
            roles = callouts[callout]
            lines.append(f"# {callout}")
            for role in roles:
                lines.append(f"* {role}")
            lines.append("")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
