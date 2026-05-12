"""Load locked production markdown into existing Stager play models."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from ruamel import yaml

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, Reader, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DescriptionSegment, DirectionSegment, MetaSegment, SimultaneousSegment
from stager.domain.segment_id import SegmentId
from stager.scriptwright.production_script import ProductionEntry, ProductionEntryKind
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths

logger = logging.getLogger(__name__)


@dataclass
class ProductionPlayLoader:
    """Adapt locked `production.md` into the existing `Play` domain model."""

    paths_config: paths.PathConfig

    def load(self) -> Play:
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
                current_part = next_part_no
                next_part_no += 1
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

    def _title_block(self, entry: ProductionEntry, part_no: int) -> TitleBlock:
        block_id = BlockId(part_no, 0)
        source_text = f"## {part_no}: {entry.text} ##"
        return TitleBlock(
            block_id=block_id,
            text=source_text,
            segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=source_text)],
            part_id=part_no,
            heading=entry.text,
        )

    def _script_block(self, entry: ProductionEntry, block_id: BlockId):
        if entry.kind == ProductionEntryKind.DESCRIPTION:
            return DescriptionBlock(
                block_id=block_id,
                text=entry.text,
                segments=[DescriptionSegment(segment_id=SegmentId(block_id, 1), text=entry.text)],
            )
        if entry.kind == ProductionEntryKind.DIRECTION:
            return DirectionBlock(
                block_id=block_id,
                text=entry.text,
                segments=[DirectionSegment(segment_id=SegmentId(block_id, 1), text=entry.text)],
            )
        if entry.kind == ProductionEntryKind.ROLE:
            roles = list(entry.roles)
            if len(roles) > 1:
                return RoleBlock(
                    block_id=block_id,
                    role_names=roles,
                    callout=roles[0],
                    text=entry.text,
                    segments=[
                        SimultaneousSegment(
                            segment_id=SegmentId(block_id, 1),
                            text=entry.text,
                            roles=roles,
                        )
                    ],
                )
            return RoleBlock(
                block_id=block_id,
                role_names=roles,
                callout=roles[0],
                text=entry.text,
                segments=RoleBlock.split_block_segments(entry.text, block_id, roles[0]),
            )
        raise RuntimeError(f"Unsupported production entry kind: {entry.kind}")

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
