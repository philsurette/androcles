"""Load locked production markdown into existing Stager play models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging

from ruamel import yaml

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, Reader, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DescriptionSegment, DirectionSegment, MetaSegment, SimultaneousSegment
from stager.domain.segment_id import SegmentId
from stager.scriptwright.content_hasher import ContentHasher
from stager.scriptwright.production_script import ProductionEntry, ProductionEntryKind
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths

logger = logging.getLogger(__name__)


@dataclass
class ProductionPlayLoader:
    """Adapt locked `production.md` into the existing `Play` domain model."""

    paths_config: paths.PathConfig
    content_hasher: ContentHasher = field(default_factory=ContentHasher)

    def load(self) -> Play:
        if not self.paths_config.production_markdown.exists():
            raise RuntimeError(
                "Missing locked production script "
                f"{paths.display_path(self.paths_config.production_markdown)}; "
                "run './main scriptwright lock' first."
            )
        production = ProductionScriptParser(self.paths_config.production_markdown).parse_path()
        if not production.locked:
            raise RuntimeError(
                f"Stager requires locked production script: {paths.display_path(self.paths_config.production_markdown)}"
            )

        play = Play(
            source_text_metadata=self._load_source_text_metadata(),
            reading_metadata=self._load_reading_metadata(),
        )
        current_part: int | None = None
        next_part_no = 0
        block_counters: dict[int | None, int] = {}

        for entry in production.entries:
            if entry.kind == ProductionEntryKind.HEADING:
                current_part = self._part_no_for_heading(entry, next_part_no)
                next_part_no = max(next_part_no, current_part + 1)
                block = self._title_block(entry, current_part)
                block_counters[current_part] = 0
            else:
                block_counters[current_part] = block_counters.get(current_part, 0) + 1
                block_id = BlockId(current_part, block_counters[current_part])
                block = self._script_block(entry, block_id)
            play.blocks.append(block)
            play._by_id[block.block_id] = block

        play.rebuild_parts_index()
        return play

    def _part_no_for_heading(self, entry: ProductionEntry, fallback: int) -> int:
        if entry.production_id is None:
            return fallback
        structural_id = entry.production_id.split("-", 1)[0]
        top_level = structural_id.split(".", 1)[0]
        if top_level == "P":
            return 0
        if top_level.isdigit():
            return int(top_level)
        roman_value = self._roman_to_int(top_level)
        return roman_value if roman_value is not None else fallback

    def _roman_to_int(self, raw_value: str) -> int | None:
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        if any(char not in roman_values for char in raw_value):
            return None
        total = 0
        previous = 0
        for char in reversed(raw_value):
            value = roman_values[char]
            if value < previous:
                total -= value
            else:
                total += value
                previous = value
        return total

    def _title_block(self, entry: ProductionEntry, part_no: int) -> TitleBlock:
        block_id = BlockId(part_no, 0)
        source_text = f"## {part_no}: {entry.text} ##"
        content_hash = self.content_hasher.hash_line(entry.kind.value, entry.text)
        return TitleBlock(
            block_id=block_id,
            text=source_text,
            segments=[
                MetaSegment(
                    segment_id=SegmentId(block_id, 1),
                    text=source_text,
                    production_id=self._segment_production_id(entry, 1, "m"),
                    content_hash=self.content_hasher.hash_segment("meta", entry.text),
                )
            ],
            part_id=part_no,
            heading=entry.text,
            production_id=entry.production_id,
            content_hash=content_hash,
        )

    def _script_block(self, entry: ProductionEntry, block_id: BlockId):
        content_hash = self.content_hasher.hash_line(
            entry.kind.value,
            entry.text,
            entry.roles,
        )
        if entry.kind == ProductionEntryKind.DESCRIPTION:
            return DescriptionBlock(
                block_id=block_id,
                text=entry.text,
                production_id=entry.production_id,
                content_hash=content_hash,
                segments=[
                    DescriptionSegment(
                        segment_id=SegmentId(block_id, 1),
                        text=entry.text,
                        production_id=self._segment_production_id(entry, 1, "d"),
                        content_hash=self.content_hasher.hash_segment("description", entry.text),
                    )
                ],
            )
        if entry.kind == ProductionEntryKind.DIRECTION:
            return DirectionBlock(
                block_id=block_id,
                text=entry.text,
                production_id=entry.production_id,
                content_hash=content_hash,
                segments=[
                    DirectionSegment(
                        segment_id=SegmentId(block_id, 1),
                        text=entry.text,
                        production_id=self._segment_production_id(entry, 1, "d"),
                        content_hash=self.content_hasher.hash_segment("direction", entry.text),
                    )
                ],
            )
        if entry.kind == ProductionEntryKind.ROLE:
            roles = list(entry.roles)
            if len(roles) > 1:
                return RoleBlock(
                    block_id=block_id,
                    role_names=roles,
                    callout=roles[0],
                    text=entry.text,
                    production_id=entry.production_id,
                    content_hash=content_hash,
                    segments=[
                        SimultaneousSegment(
                            segment_id=SegmentId(block_id, 1),
                            text=entry.text,
                            roles=roles,
                            production_id=self._segment_production_id(entry, 1, "s"),
                            content_hash=self.content_hasher.hash_segment("simultaneous", entry.text, ",".join(roles)),
                        )
                    ],
                )
            segments = RoleBlock.split_block_segments(entry.text, block_id, roles[0])
            speech_count = 0
            direction_count = 0
            for segment in segments:
                if isinstance(segment, DirectionSegment):
                    direction_count += 1
                    segment.production_id = self._segment_production_id(entry, direction_count, "d")
                    segment.content_hash = self.content_hasher.hash_segment("direction", segment.text)
                else:
                    speech_count += 1
                    segment.production_id = self._segment_production_id(entry, speech_count, "s")
                    segment.content_hash = self.content_hasher.hash_segment("speech", segment.text, roles[0])
            return RoleBlock(
                block_id=block_id,
                role_names=roles,
                callout=roles[0],
                text=entry.text,
                production_id=entry.production_id,
                content_hash=content_hash,
                segments=segments,
            )
        raise RuntimeError(f"Unsupported production entry kind: {entry.kind}")

    def _segment_production_id(self, entry: ProductionEntry, index: int, prefix: str) -> str | None:
        if entry.production_id is None:
            return None
        return f"{entry.production_id}:{prefix}{index}"

    def _load_source_text_metadata(self) -> SourceTextMetadata:
        meta_path = self.paths_config.play_dir / "source_text_metadata.yaml"
        if not meta_path.exists():
            logger.warning("could not find source text metadata at %s", paths.display_path(meta_path))
            return SourceTextMetadata()
        yml = yaml.YAML(typ="safe", pure=True)
        raw = yml.load(meta_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid metadata format in {paths.display_path(meta_path)}")
        return SourceTextMetadata(**raw)

    def _load_reading_metadata(self) -> ReadingMetadata:
        meta_path = self.paths_config.play_dir / "reading_metadata.yaml"
        if not meta_path.exists():
            logger.warning("could not find reading metadata at %s", paths.display_path(meta_path))
            return ReadingMetadata()
        yml = yaml.YAML(typ="safe", pure=True)
        raw = yml.load(meta_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid metadata format in {paths.display_path(meta_path)}")
        readers = [Reader(**entry) for entry in raw.get("readers", []) or []]
        meta_kwargs = dict(raw)
        meta_kwargs["readers"] = readers
        return ReadingMetadata(**meta_kwargs)
