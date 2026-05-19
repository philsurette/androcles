from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
import zipfile

from stager.domain.block import BlockingBlock, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.domain.segment import BlockingSegment, DescriptionSegment, DirectionSegment, Segment, SimultaneousSegment, SpeechSegment
from stager.linerecorder.recording_context import RecordingContext
from stager.linerecorder.recording_request_manifest import (
    RecordingPreferences,
    RecordingRequestItem,
    RecordingRequestManifest,
    RecordingRequestMetadata,
    RecordingRequestBlocking,
    RecordingRequestPlay,
    RecordingRequestProduction,
    RecordingRequestRole,
)
from stager.playbook.app_line import AppLine
from stager.playbook.playbook_cue_selector import PlaybookCueSelector
from stager.production.cast_config import CastConfig
from stager.production_publication.production_version import ProductionVersion
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths


@dataclass
class RecordingRequestBuilder:
    play: Play
    paths: paths.PathConfig
    role: str
    play_id: str | None = None
    request_kind: str = "full_role"
    request_id: str | None = None
    created_at: str | None = None
    notes: str | None = None
    build_id: str | None = None
    build_timestamp: str | None = None
    item_reason: str | None = None
    selected_segment_ids: set[str] | None = None
    selected_item_reasons: dict[str, str] | None = None
    cue_selector: PlaybookCueSelector | None = None
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        if self.cue_selector is None:
            self.cue_selector = PlaybookCueSelector(play=self.play, paths=self.paths)

    @property
    def request_dir(self) -> Path:
        return self.paths.build_dir / "linerecorder" / self.role

    @property
    def zip_path(self) -> Path:
        return self.paths.build_dir / "linerecorder" / f"{self.role}.recording-request.zip"

    def build(self) -> Path:
        if self.request_dir.exists():
            shutil.rmtree(self.request_dir)
        self.request_dir.mkdir(parents=True, exist_ok=True)
        manifest = self.build_manifest()
        manifest_path = self.request_dir / "manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self._logger.info("Wrote Recording Request manifest %s", paths.display_path(manifest_path))
        self._write_zip()
        self._logger.info("Wrote Recording Request package %s", paths.display_path(self.zip_path))
        return self.zip_path

    def build_manifest(self) -> RecordingRequestManifest:
        role = self.play.getRole(self.role)
        if role is None or role.meta or role.name.startswith("_"):
            raise ValueError(f"Unknown rehearsable role: {self.role}")

        created_at = self.created_at or self._now()
        production = self._production_metadata()
        cast_config = CastConfig.load(self.paths)
        assignment = cast_config.assignment_for_role(role.name)
        actor = cast_config.actors.get(assignment.actor) if assignment is not None and assignment.actor is not None else None
        return RecordingRequestManifest(
            request=RecordingRequestMetadata(
                id=self.request_id or self._default_request_id(created_at),
                kind=self.request_kind,
                created_at=created_at,
                notes=self.notes,
                production_version=production.version,
            ),
            play=RecordingRequestPlay(
                id=self.play_id or self.paths.play_name,
                title=self.play.title,
                version=production.version,
                buildId=self.build_id,
                buildTimestamp=self.build_timestamp,
            ),
            production=production,
            role=RecordingRequestRole(
                id=role.name,
                display_name=role.name,
                actor_id=assignment.actor if assignment is not None else None,
                actor_display_name=actor.display_name if actor is not None else None,
                actor_email=actor.email if actor is not None else None,
            ),
            recording=RecordingPreferences(),
            items=self._build_items(),
        )

    def _production_metadata(self) -> RecordingRequestProduction:
        source_path = self.paths.production_markdown
        source = self._production_source(source_path)
        if not source_path.exists():
            return RecordingRequestProduction(source=source)
        metadata = ProductionScriptParser(source_path).parse_path().metadata
        production_version = self._parse_production_version(metadata.get("production_version"))
        parent_version = metadata.get("parent_production_version")
        normalized_parent = None if parent_version in (None, "none") else parent_version
        published_at = self._published_at(production_version, source)
        return RecordingRequestProduction(
            source=source,
            version=str(production_version) if production_version is not None else None,
            sequence=production_version.sequence if production_version is not None else None,
            publication_id=production_version.publication_id if production_version is not None else None,
            parent_version=normalized_parent,
            published_at=published_at,
        )

    def _production_source(self, source_path: Path) -> str:
        try:
            current_path = ProductionVersionStore(self.paths).current_production_path()
        except RuntimeError:
            return "working"
        if current_path is not None and source_path.resolve() == current_path.resolve():
            return "published"
        return "working"

    def _parse_production_version(self, value: str | None) -> ProductionVersion | None:
        if value is None:
            return None
        return ProductionVersion.parse(value)

    def _published_at(self, production_version: ProductionVersion | None, source: str) -> str | None:
        if production_version is None or source != "published":
            return None
        return ProductionVersionStore(self.paths).load_version(str(production_version)).published_at

    def _build_items(self) -> list[RecordingRequestItem]:
        items: list[RecordingRequestItem] = []
        matched_segment_ids: set[str] = set()
        sequence = 1
        for block in self.play.blocks:
            if not isinstance(block, RoleBlock):
                continue
            response_segments = self._response_segments_for_role(block)
            for segment in response_segments:
                segment_id = self._segment_request_id(segment)
                if self.selected_segment_ids is not None and segment_id not in self.selected_segment_ids:
                    continue
                matched_segment_ids.add(segment_id)
                items.append(self._build_item(block, segment, sequence))
                sequence += 1
        if self.selected_segment_ids is not None:
            missing = self.selected_segment_ids - matched_segment_ids
            if missing:
                raise ValueError(
                    f"Selected segment ids do not belong to role {self.role}: {', '.join(sorted(missing))}"
                )
        return items

    def _build_item(
        self,
        block: RoleBlock,
        segment: SpeechSegment | SimultaneousSegment,
        sequence: int,
    ) -> RecordingRequestItem:
        assert self.cue_selector is not None
        cue = self.cue_selector.select_for_block(block)
        previous = self._previous_context(block)
        if previous is not None and previous.speaker == cue.speaker and previous.text == cue.text:
            previous = None
        next_context = self._next_context(block)
        section = self._section_for_block(block)
        segment_id = str(segment.segment_id)
        return RecordingRequestItem(
            id=self._segment_request_id(segment),
            line_id=AppLine.line_id_for(block, self.role),
            block_id=AppLine.block_id_for(block),
            segment_id=segment_id,
            line_content_hash=block.content_hash,
            segment_content_hash=segment.content_hash,
            sequence=sequence,
            display_text=block.text,
            segment_text=segment.text,
            output_path=f"audio/segments/{self.role}/{segment_id}.wav",
            cue_text=cue.text,
            cue_speaker=cue.speaker,
            previous_text=previous.text if previous else None,
            previous_speaker=previous.speaker if previous else None,
            next_text=next_context.text if next_context else None,
            next_speaker=next_context.speaker if next_context else None,
            section_id=section[0],
            section_title=section[1],
            scene_heading=section[1],
            stage_directions=[
                direction.text
                for direction in block.segments
                if isinstance(direction, DirectionSegment)
            ],
            blocking=self._blocking_context(block),
            reason=self._item_reason(self._segment_request_id(segment)),
            simultaneous=isinstance(segment, SimultaneousSegment),
        )

    def _item_reason(self, item_id: str) -> str:
        if self.selected_item_reasons is not None and item_id in self.selected_item_reasons:
            return self.selected_item_reasons[item_id]
        if self.item_reason is not None:
            return self.item_reason
        if self.request_kind == "full_role":
            return "initial_recording"
        return self.request_kind

    def _segment_request_id(self, segment: SpeechSegment | SimultaneousSegment) -> str:
        if segment.production_id is None:
            raise RuntimeError(f"Missing production id for recording request segment {segment.segment_id}")
        return segment.production_id

    def _response_segments_for_role(self, block: RoleBlock) -> list[SpeechSegment | SimultaneousSegment]:
        segments: list[SpeechSegment | SimultaneousSegment] = []
        for segment in block.segments:
            if isinstance(segment, SpeechSegment) and segment.role == self.role:
                segments.append(segment)
            elif isinstance(segment, SimultaneousSegment) and self.role in segment.roles:
                segments.append(segment)
        return segments

    def _previous_context(self, block: RoleBlock) -> RecordingContext | None:
        previous_blocks: list = []
        for candidate in self.play.blocks:
            if candidate is block:
                break
            previous_blocks.append(candidate)
        for candidate in reversed(previous_blocks):
            context = self._last_context_for_block(candidate)
            if context is not None:
                return context
        return None

    def _next_context(self, block: RoleBlock) -> RecordingContext | None:
        seen_block = False
        for candidate in self.play.blocks:
            if candidate is block:
                seen_block = True
                continue
            if not seen_block:
                continue
            context = self._first_context_for_block(candidate)
            if context is not None:
                return context
        return None

    def _last_context_for_block(self, block) -> RecordingContext | None:
        if isinstance(block, RoleBlock):
            for segment in reversed(block.segments):
                context = self._context_for_segment(segment, block)
                if context is not None:
                    return context
            return None
        return self._context_for_narrator_block(block)

    def _blocking_context(self, block: RoleBlock) -> list[RecordingRequestBlocking]:
        blocking: list[RecordingRequestBlocking] = []
        seen_ids: set[str] = set()
        for segment in block.segments:
            if isinstance(segment, BlockingSegment):
                self._append_blocking(blocking, seen_ids, segment, "inline")
        block_index = self.play.blocks.index(block)
        previous_index = self._adjacent_role_block_index(block_index, -1)
        next_index = self._adjacent_role_block_index(block_index, 1)
        start = 0 if previous_index is None else previous_index + 1
        stop = len(self.play.blocks) if next_index is None else next_index
        for candidate in self.play.blocks[start:stop]:
            if isinstance(candidate, BlockingBlock) and self._blocking_targets_role(candidate.targets):
                for segment in candidate.segments:
                    if isinstance(segment, BlockingSegment):
                        self._append_blocking(blocking, seen_ids, segment, candidate.placement)
        return blocking

    def _adjacent_role_block_index(self, start_index: int, step: int) -> int | None:
        index = start_index + step
        while 0 <= index < len(self.play.blocks):
            candidate = self.play.blocks[index]
            if isinstance(candidate, RoleBlock) and self._response_segments_for_role(candidate):
                return index
            index += step
        return None

    def _blocking_targets_role(self, targets: list[str]) -> bool:
        return "*" in targets or self.role in targets

    def _append_blocking(
        self,
        blocking: list[RecordingRequestBlocking],
        seen_ids: set[str],
        segment: BlockingSegment,
        placement: str,
    ) -> None:
        if segment.production_id is None:
            raise RuntimeError(f"Missing production id for blocking segment {segment.segment_id}")
        if segment.production_id in seen_ids:
            return
        seen_ids.add(segment.production_id)
        blocking.append(
            RecordingRequestBlocking(
                id=segment.production_id,
                targets=list(segment.targets),
                text=segment.text,
                placement=placement,
            )
        )

    def _first_context_for_block(self, block) -> RecordingContext | None:
        if isinstance(block, RoleBlock):
            for segment in block.segments:
                context = self._context_for_segment(segment, block)
                if context is not None:
                    return context
            return None
        return self._context_for_narrator_block(block)

    def _context_for_segment(self, segment: Segment, block: RoleBlock) -> RecordingContext | None:
        if isinstance(segment, SpeechSegment) and not segment.role.startswith("_"):
            return RecordingContext(speaker=segment.role, text=segment.text)
        if isinstance(segment, SimultaneousSegment):
            return RecordingContext(
                speaker=block.callout or ", ".join(segment.roles),
                text=segment.text,
            )
        if isinstance(segment, DirectionSegment):
            return RecordingContext(speaker="_NARRATOR", text=segment.text)
        return None

    def _context_for_narrator_block(self, block) -> RecordingContext | None:
        if isinstance(block, TitleBlock):
            return RecordingContext(speaker="_NARRATOR", text=block.heading)
        if isinstance(block, (DescriptionBlock, DirectionBlock)):
            return RecordingContext(speaker="_NARRATOR", text=block.text)
        return None

    def _section_for_block(self, block: RoleBlock) -> tuple[str, str]:
        part = self.play.getPart(block.block_id.part_id)
        section_id = "play" if block.block_id.part_id is None else f"part-{block.block_id.part_id}"
        title = None
        if part is not None:
            title = part.title
            if title is None:
                title_block = next((candidate for candidate in part.blocks if isinstance(candidate, TitleBlock)), None)
                title = title_block.heading if title_block else None
        if title is None:
            title = self.play.title if block.block_id.part_id is None else f"Part {block.block_id.part_id + 1}"
        return section_id, title

    def _default_request_id(self, created_at: str) -> str:
        return f"{self.play_id or self.paths.play_name}-{self.role}-{self.request_kind}-{created_at.split('T', maxsplit=1)[0]}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _write_zip(self) -> None:
        self.zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.request_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(self.request_dir).as_posix())
