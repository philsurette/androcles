"""Convert source script formats into locked production markdown."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re

from stager.domain.block import Block, BlockingBlock, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.scriptwright.production_script import ProductionEntry, ProductionEntryKind, ProductionScript
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths
from stager.text.play_text_parser import PlayTextParser

logger = logging.getLogger(__name__)

ProductionMarkdownFormat = str
PRODUCTION_MARKDOWN_FORMATS = {"compact", "list", "doublespace"}


@dataclass
class ScriptWright:
    """Create locked `production.md` from supported source script formats."""

    paths_config: paths.PathConfig

    def reconcile(self) -> None:
        raise NotImplementedError(
            "ScriptWright reconcile is not implemented yet. Regenerate draft production.md freely before locking, "
            "or edit locked production.md directly while preserving existing ids."
        )

    def write_locked(self, force: bool = False, output_format: ProductionMarkdownFormat = "list") -> Path:
        self._validate_output_format(output_format)
        output_path = self.paths_config.production_markdown
        if output_path.exists():
            production = ProductionScriptParser(output_path).parse_path()
            if production.locked and not force:
                raise RuntimeError(
                    f"Refusing to overwrite locked production script: {paths.display_path(output_path)}"
                )
            text = self.render_from_play_text(output_format=output_format) if production.locked else self.render_locked_production(
                production,
                output_format=output_format,
            )
        else:
            text = self.render_from_play_text(output_format=output_format)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        logger.info("Wrote locked production script %s", paths.display_path(output_path))
        return output_path

    def render_from_play_text(self, output_format: ProductionMarkdownFormat = "list") -> str:
        self._validate_output_format(output_format)
        play = PlayTextParser(paths_config=self.paths_config).parse()
        return self.render_play(play, output_format=output_format)

    def write_from_play_text(self, force: bool = False, output_format: ProductionMarkdownFormat = "list") -> Path:
        self._validate_output_format(output_format)
        output_path = self.paths_config.production_markdown
        if output_path.exists() and self._is_locked_output(output_path.read_text(encoding="utf-8")) and not force:
            raise RuntimeError(
                f"Refusing to overwrite locked production script: {paths.display_path(output_path)}"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_from_play_text(output_format=output_format), encoding="utf-8")
        logger.info("Wrote locked production script %s", paths.display_path(output_path))
        return output_path

    def render_locked_production(
        self,
        production: ProductionScript,
        output_format: ProductionMarkdownFormat = "list",
    ) -> str:
        self._validate_output_format(output_format)
        lines = [
            "// script_format: quince-production-v1",
            "// source_kind: production",
            "// production_ids: locked",
            "",
        ]
        for production_id, entry in self._assign_ids(production.entries):
            lines.extend(entry.leading_comments)
            self._append_formatted_entry(
                lines,
                self._render_production_entry(production_id, entry),
                entry.kind,
                output_format,
            )
        return self._finish_lines(lines)

    def render_play(self, play: Play, output_format: ProductionMarkdownFormat = "list") -> str:
        self._validate_output_format(output_format)
        structure_ids = self._structure_ids(play)
        lines = [
            "// script_format: quince-production-v1",
            "// source_kind: production",
            "// production_ids: locked",
            "",
        ]
        for block in play.blocks:
            self._append_formatted_entry(
                lines,
                self._render_block(block, structure_ids),
                self._kind_for_block(block),
                output_format,
            )
        return self._finish_lines(lines)

    def _validate_output_format(self, output_format: ProductionMarkdownFormat) -> None:
        if output_format not in PRODUCTION_MARKDOWN_FORMATS:
            raise RuntimeError(f"Unknown production markdown format: {output_format}")

    def _append_formatted_entry(
        self,
        lines: list[str],
        line: str,
        kind: ProductionEntryKind,
        output_format: ProductionMarkdownFormat,
    ) -> None:
        lines.extend(self._formatted_entry_lines(line, kind, output_format, bool(lines and lines[-1] != "")))

    def _formatted_entry_lines(
        self,
        line: str,
        kind: ProductionEntryKind,
        output_format: ProductionMarkdownFormat,
        needs_heading_separator: bool = False,
    ) -> list[str]:
        if output_format == "compact":
            return [line]
        if output_format == "doublespace":
            return [line, ""]
        if kind == ProductionEntryKind.HEADING:
            return ["", line] if needs_heading_separator else [line]
        return [f"- {line}"]

    def _finish_lines(self, lines: list[str]) -> str:
        return "\n".join(lines).rstrip() + "\n"

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
        if isinstance(block, BlockingBlock):
            targets = ", ".join(block.targets)
            return f"/{targets}: {self._clean_text(block.text)}"
        if isinstance(block, RoleBlock):
            speakers = ", ".join(block.role_names)
            return f"{production_id} {speakers}: {self._clean_text(block.text)}"

        raise RuntimeError(f"Unsupported block type for production output: {type(block).__name__}")

    def _kind_for_block(self, block: Block) -> ProductionEntryKind:
        if isinstance(block, TitleBlock):
            return ProductionEntryKind.HEADING
        if isinstance(block, DescriptionBlock):
            return ProductionEntryKind.DESCRIPTION
        if isinstance(block, DirectionBlock):
            return ProductionEntryKind.DIRECTION
        if isinstance(block, BlockingBlock):
            return ProductionEntryKind.BLOCKING
        if isinstance(block, RoleBlock):
            return ProductionEntryKind.ROLE
        raise RuntimeError(f"Unsupported block type for production output: {type(block).__name__}")

    def _assign_ids(self, entries: tuple[ProductionEntry, ...]) -> list[tuple[str, ProductionEntry]]:
        current_structure: str | None = None
        line_counters: dict[str, int] = {}
        assigned: list[tuple[str, ProductionEntry]] = []
        assigned_ids: set[str] = set()
        for entry in entries:
            if entry.kind == ProductionEntryKind.BLOCKING:
                self._append_assigned_id(assigned, assigned_ids, f"__blocking_{len(assigned)}", entry)
                continue
            if entry.production_id is not None:
                production_id = entry.production_id
                explicit_structure = production_id.rsplit("-", 1)[0]
                current_structure = explicit_structure
                line_counters[explicit_structure] = max(
                    line_counters.get(explicit_structure, 0),
                    self._line_number_component(production_id),
                )
                self._append_assigned_id(assigned, assigned_ids, production_id, entry)
                continue
            if entry.kind == ProductionEntryKind.HEADING:
                current_structure = self._structure_id_for_heading(entry.text, current_structure)
                line_counters.setdefault(current_structure, 0)
                self._append_assigned_id(assigned, assigned_ids, f"{current_structure}-0", entry)
                continue
            if current_structure is None:
                current_structure = "0"
            line_counters[current_structure] = line_counters.get(current_structure, 0) + 1
            self._append_assigned_id(
                assigned,
                assigned_ids,
                f"{current_structure}-{line_counters[current_structure]}",
                entry,
            )
        return assigned

    def _append_assigned_id(
        self,
        assigned: list[tuple[str, ProductionEntry]],
        assigned_ids: set[str],
        production_id: str,
        entry: ProductionEntry,
    ) -> None:
        if production_id in assigned_ids:
            raise RuntimeError(f"Duplicate production id after assignment: {production_id}")
        assigned_ids.add(production_id)
        assigned.append((production_id, entry))

    def _structure_id_for_heading(self, heading: str, current_structure: str | None) -> str:
        normalized = heading.strip().upper()
        if "PROLOGUE" in normalized:
            return "P"
        if "EPILOGUE" in normalized:
            return "E"

        act_match = re.search(r"\bACT\s+([IVXLCDM]+|[0-9]+)\b", normalized)
        if act_match:
            return act_match.group(1)

        scene_match = re.search(r"\bSCENE\s+([IVXLCDM]+|[0-9]+)\b", normalized)
        if scene_match and current_structure is not None:
            return f"{current_structure}.{self._scene_component(scene_match.group(1))}"

        return current_structure or "1"

    def _scene_component(self, raw_component: str) -> str:
        if raw_component.isdigit():
            return raw_component
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        previous = 0
        for char in reversed(raw_component):
            value = roman_values[char]
            if value < previous:
                total -= value
            else:
                total += value
                previous = value
        return str(total)

    def _line_number_component(self, production_id: str) -> int:
        line_component = production_id.rsplit("-", 1)[1]
        match = re.match(r"(?P<line_no>[0-9]+)", line_component)
        if not match:
            raise RuntimeError(f"Production id is missing a line number: {production_id}")
        return int(match.group("line_no"))

    def _render_production_entry(self, production_id: str, entry: ProductionEntry) -> str:
        if entry.kind == ProductionEntryKind.HEADING:
            level = entry.heading_level or 1
            return f"{'#' * level} {production_id} {entry.text}"
        if entry.kind == ProductionEntryKind.DESCRIPTION:
            return f"{production_id} @description: {self._clean_text(entry.text)}"
        if entry.kind == ProductionEntryKind.DIRECTION:
            return f"{production_id} @direction: {self._clean_text(entry.text)}"
        if entry.kind == ProductionEntryKind.BLOCKING:
            return f"/{', '.join(entry.targets)}: {self._clean_text(entry.text)}"
        if entry.kind == ProductionEntryKind.ROLE:
            return f"{production_id} {', '.join(entry.roles)}: {self._clean_text(entry.text)}"
        raise RuntimeError(f"Unsupported production entry kind: {entry.kind}")

    def _production_id(self, block: Block, structure_ids: dict[int | None, str]) -> str:
        structure_id = structure_ids.get(block.block_id.part_id)
        if structure_id is None:
            raise RuntimeError(f"Missing structure id for part {block.block_id.part_id}")
        return f"{structure_id}-{block.block_id.block_no}"

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _is_locked_output(self, text: str) -> bool:
        return bool(re.search(r"(?m)^//\s*production_ids:\s*locked\s*$", text))
