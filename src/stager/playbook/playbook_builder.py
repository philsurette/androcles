from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import shutil
import zipfile

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.domain.segment import DirectionSegment, SimultaneousSegment, SpeechSegment
from stager.playbook.app_audio_asset import AppAudioAsset
from stager.playbook.app_context_block import AppContextBlock
from stager.playbook.app_cue import AppCue
from stager.playbook.app_cue_start_offset import AppCueStartOffset
from stager.playbook.app_direction import AppDirection
from stager.playbook.app_line import AppLine
from stager.playbook.app_manifest import AppManifest
from stager.playbook.app_play import AppPlay
from stager.playbook.app_reading import AppReading
from stager.playbook.app_response import AppResponse
from stager.playbook.app_response_segment import AppResponseSegment
from stager.playbook.app_role import AppRole
from stager.playbook.cue_start_offset_analyzer import CueStartOffsetAnalyzer
from stager.playbook.cue_selection import CueSelection
from stager.playbook.playbook_audio_packager import PlaybookAudioPackager
from stager.playbook.playbook_cue_selector import PlaybookCueSelector
from stager.shared import paths


@dataclass
class PlaybookBuilder:
    play: Play
    paths: paths.PathConfig
    play_id: str | None = None
    build_type: str = "custom"
    audio_format: str = "wav"
    selector: PlaybookCueSelector | None = None
    cue_start_offset_analyzer: CueStartOffsetAnalyzer | None = None
    audio_packager: PlaybookAudioPackager | None = None
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        if self.selector is None:
            self.selector = PlaybookCueSelector(play=self.play, paths=self.paths)
        if self.cue_start_offset_analyzer is None:
            self.cue_start_offset_analyzer = CueStartOffsetAnalyzer()
        if self.audio_packager is None:
            self.audio_packager = PlaybookAudioPackager(
                app_dir=self.app_dir,
                audio_format=self.audio_format,
            )

    @property
    def app_dir(self) -> Path:
        return self.paths.build_dir / "app"

    @property
    def zip_path(self) -> Path:
        return self.paths.build_dir / f"{self.paths.play_name}.playbook.zip"

    def build(self) -> Path:
        if self.app_dir.exists():
            shutil.rmtree(self.app_dir)
        self.app_dir.mkdir(parents=True, exist_ok=True)
        manifest = self.build_manifest()
        manifest_path = self.app_dir / "manifest.json"
        manifest_path.write_text(manifest.to_json(), encoding="utf-8")
        self._logger.info("Wrote Playbook manifest %s", paths.display_path(manifest_path))
        self._write_zip()
        self._logger.info("Wrote Playbook package %s", paths.display_path(self.zip_path))
        return self.zip_path

    def build_manifest(self) -> AppManifest:
        return AppManifest(
            play=AppPlay.from_play(self.play_id or self.paths.play_name, self.play),
            reading=AppReading.from_play(self.play, build_type=self.build_type),
            roles=[self._build_role(role) for role in self.play.roles if not role.meta and not role.name.startswith("_")],
            context=self._build_context_blocks(),
        )

    def _build_context_blocks(self) -> list[AppContextBlock]:
        context_blocks: list[AppContextBlock] = []
        for block in self.play.blocks:
            if not isinstance(block, (TitleBlock, DescriptionBlock, DirectionBlock)):
                continue
            if not block.segments:
                continue
            segment = block.segments[0]
            segment_id = str(segment.segment_id)
            context_blocks.append(
                AppContextBlock(
                    id=segment_id,
                    part_id=block.block_id.part_id,
                    block_id=self._block_id_for(block),
                    kind=self._context_kind_for(block),
                    speaker="_NARRATOR",
                    text=self._context_text_for(block),
                    audio=self._copy_required_audio(
                        source_path=self.paths.segments_dir / "_NARRATOR" / f"{segment_id}.wav",
                        role="_NARRATOR",
                        segment_id=segment_id,
                        category="context",
                    ),
                )
            )
        return context_blocks

    def _build_role(self, role) -> AppRole:
        app_role = AppRole.from_domain(self.play, role)
        lines: list[AppLine] = []
        for block in role.blocks:
            response_segments = self._response_segments_for_role(block, role.name)
            if not response_segments:
                continue
            cue_selection = self.selector.select_for_block(block)
            lines.append(
                AppLine(
                    id=AppLine.line_id_for(block, role.name),
                    part_id=block.block_id.part_id,
                    block_id=AppLine.block_id_for(block),
                    role=role.name,
                    speaker=block.callout or role.name,
                    cue=self._build_cue(cue_selection),
                    response=AppResponse(
                        text=" ".join(segment.text for segment in response_segments),
                        segments=[self._build_response_segment(role.name, segment) for segment in response_segments],
                    ),
                    directions=[
                        AppDirection.from_segment(segment, placement="inline")
                        for segment in block.segments
                        if isinstance(segment, DirectionSegment)
                    ],
                    previous_roles=self.play.getPrecedingRoles(block.block_id, include_meta_roles=True),
                    simultaneous=any(isinstance(segment, SimultaneousSegment) for segment in response_segments),
                )
            )
        app_role.lines = lines
        return app_role

    def _response_segments_for_role(self, block: RoleBlock, role: str) -> list[SpeechSegment | SimultaneousSegment]:
        segments: list[SpeechSegment | SimultaneousSegment] = []
        for segment in block.segments:
            if isinstance(segment, SpeechSegment) and segment.role == role:
                segments.append(segment)
            elif isinstance(segment, SimultaneousSegment) and role in segment.roles:
                segments.append(segment)
        return segments

    def _block_id_for(self, block) -> str:
        part = block.block_id.part_id if block.block_id.part_id is not None else ""
        return f"{part}.{block.block_id.block_no}"

    def _context_kind_for(self, block: TitleBlock | DescriptionBlock | DirectionBlock) -> str:
        if isinstance(block, TitleBlock):
            return "heading"
        if isinstance(block, DescriptionBlock):
            return "description"
        return "direction"

    def _context_text_for(self, block: TitleBlock | DescriptionBlock | DirectionBlock) -> str:
        if isinstance(block, TitleBlock):
            return block.heading
        return block.text

    def _build_cue(self, selection: CueSelection) -> AppCue:
        asset = self._copy_required_audio(
            source_path=selection.audio_path,
            role=selection.source_role,
            segment_id=selection.audio_path.stem,
            category="cue",
        )
        return AppCue(
            speaker=selection.speaker,
            text=selection.text,
            audio=asset,
        )

    def _build_response_segment(
        self,
        role: str,
        segment: SpeechSegment | SimultaneousSegment,
    ) -> AppResponseSegment:
        asset = self._copy_required_audio(
            source_path=self.paths.segments_dir / role / f"{segment.segment_id}.wav",
            role=role,
            segment_id=str(segment.segment_id),
            category="response",
        )
        owners = [segment.role] if isinstance(segment, SpeechSegment) else list(segment.roles)
        return AppResponseSegment(
            id=str(segment.segment_id),
            owners=owners,
            text=segment.text,
            audio=asset,
            simultaneous=isinstance(segment, SimultaneousSegment),
        )

    def _copy_required_audio(self, source_path: Path, role: str, segment_id: str, category: str) -> AppAudioAsset:
        if not source_path.exists():
            raise RuntimeError(
                f"Missing required {category} audio for role {role} segment {segment_id} "
                f"while building Playbook: {paths.display_path(source_path)}"
            )
        duration_ms = self.paths.get_audio_length_ms(source_path)
        cue_start_offsets: list[AppCueStartOffset] = []
        if category == "cue":
            assert self.cue_start_offset_analyzer is not None
            cue_start_offsets = self.cue_start_offset_analyzer.analyze(source_path, duration_ms)
        assert self.audio_packager is not None
        packaged_audio = self.audio_packager.package(
            source_path,
            self.app_dir / "audio" / "segments" / role,
        )
        return AppAudioAsset(
            path=packaged_audio.manifest_path,
            duration_ms=duration_ms,
            required=True,
            cue_start_offsets=cue_start_offsets,
        )

    def _write_zip(self) -> None:
        self.zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.app_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(self.app_dir).as_posix())
