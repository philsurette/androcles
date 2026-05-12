"""Convert source script formats into locked production markdown."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re

from stager.domain.block import Block, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.shared import paths
from stager.text.play_text_parser import PlayTextParser

logger = logging.getLogger(__name__)


@dataclass
class ScriptWright:
    """Create locked `production.md` from supported source script formats."""

    paths_config: paths.PathConfig

    def render_from_play_text(self) -> str:
        play = PlayTextParser(paths_config=self.paths_config).parse()
        return self.render_play(play)

    def write_from_play_text(self, force: bool = False) -> Path:
        output_path = self.paths_config.production_markdown
        if output_path.exists() and self._is_locked_output(output_path.read_text(encoding="utf-8")) and not force:
            raise RuntimeError(
                f"Refusing to overwrite locked production script: {paths.display_path(output_path)}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_from_play_text(), encoding="utf-8")
        logger.info("Wrote locked production script %s", paths.display_path(output_path))
        return output_path

    def render_play(self, play: Play) -> str:
        structure_ids = self._structure_ids(play)
        lines = [
            "// script_format: quince-production-v1",
            "// source_kind: production",
            "// production_ids: locked",
            "",
        ]
        for block in play.blocks:
            lines.append(self._render_block(block, structure_ids))
        return "\n".join(lines) + "\n"

    def _structure_ids(self, play: Play) -> dict[int | None, str]:
        return {
            part.part_no: self._structure_id(part.part_no, part.title)
            for part in play.parts
        }

    def _structure_id(self, part_no: int | None, title: str | None) -> str:
        if part_no is None:
            return "0"

        normalized = (title or "").strip().upper()
        if "PROLOGUE" in normalized:
            return "P"
        if "EPILOGUE" in normalized:
            return "E"

        roman_match = re.search(r"\bACT\s+([IVXLCDM]+)\b", normalized)
        if roman_match:
            return roman_match.group(1)

        return str(part_no)

    def _render_block(self, block: Block, structure_ids: dict[int | None, str]) -> str:
        production_id = self._production_id(block, structure_ids)
        if isinstance(block, TitleBlock):
            return f"# {production_id} {block.heading}"
        if isinstance(block, DescriptionBlock):
            return f"{production_id} @description: {self._clean_text(block.text)}"
        if isinstance(block, DirectionBlock):
            return f"{production_id} @direction: {self._clean_text(block.text)}"
        if isinstance(block, RoleBlock):
            speakers = ", ".join(block.role_names)
            return f"{production_id} {speakers}: {self._clean_text(block.text)}"

        raise RuntimeError(f"Unsupported block type for production output: {type(block).__name__}")

    def _production_id(self, block: Block, structure_ids: dict[int | None, str]) -> str:
        structure_id = structure_ids.get(block.block_id.part_id)
        if structure_id is None:
            raise RuntimeError(f"Missing structure id for part {block.block_id.part_id}")
        return f"{structure_id}-{block.block_id.block_no}"

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _is_locked_output(self, text: str) -> bool:
        return bool(re.search(r"(?m)^//\s*production_ids:\s*locked\s*$", text))
