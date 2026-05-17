from __future__ import annotations

from datetime import datetime
from datetime import timezone
from dataclasses import dataclass, field
import itertools
import logging
from pathlib import Path
from uuid import uuid4
import shutil
import zipfile

from stager.domain.block import BlockingBlock, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.domain.segment import BlockingSegment, DirectionSegment, SimultaneousSegment, SpeechSegment
from stager.playbook.app_audio_asset import AppAudioAsset
from stager.playbook.app_blocking import AppBlocking
from stager.playbook.app_context_block import AppContextBlock
from stager.playbook.app_cue import AppCue
from stager.playbook.app_cue_start_offset import AppCueStartOffset
from stager.playbook.app_direction import AppDirection
from stager.playbook.app_line import AppLine
from stager.playbook.app_manifest import AppManifest, AppManifestBuild
from stager.playbook.app_play import AppPlay
from stager.playbook.app_production import AppProduction
from stager.playbook.app_reading import AppReading
from stager.playbook.app_response import AppResponse
from stager.playbook.app_response_segment import AppResponseSegment
from stager.playbook.app_role import AppRole
from stager.playbook.app_section import AppSection
from stager.playbook.cue_start_offset_analyzer import CueStartOffsetAnalyzer
from stager.playbook.cue_selection import CueSelection
from stager.playbook.playbook_audio_work_item import PlaybookAudioWorkItem
from stager.playbook.playbook_audio_packager import PlaybookAudioPackager
from stager.playbook.playbook_cue_selector import PlaybookCueSelector
from stager.playbook.playbook_progress_reporter import PlaybookProgressReporter
from stager.production_publication.production_version import ProductionVersion
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright.production_script_parser import ProductionScriptParser
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
    progress_reporter: PlaybookProgressReporter | None = None
    build_id: str | None = None
    build_timestamp: str | None = None
    _manifest_assets: list[AppAudioAsset] = field(default_factory=list, init=False, repr=False)
    _audio_asset_cache: dict[tuple[Path, str, str], AppAudioAsset] = field(default_factory=dict, init=False, repr=False)
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
        self._manifest_assets.clear()
        if self.app_dir.exists():
            shutil.rmtree(self.app_dir)
        self.app_dir.mkdir(parents=True, exist_ok=True)
        audio_work_items = self.plan_audio_work()
        if self.progress_reporter is not None:
            self.progress_reporter.start_audio_packaging(len(audio_work_items))
        manifest = self.build_manifest()
        if self.progress_reporter is not None:
            self.progress_reporter.finish_audio_packaging()
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
            build=self._build_metadata(),
            production=self._production_metadata(),
            sections=self._build_sections(),
            roles=[self._build_role(role) for role in self.play.roles if not role.meta and not role.name.startswith("_")],
            context=self._build_context_blocks(),
            assets=self._manifest_assets,
        )

    def _build_metadata(self) -> AppManifestBuild:
        return AppManifestBuild(buildId=self._manifest_build_id(), buildTimestamp=self._manifest_build_timestamp())

    def _production_metadata(self) -> AppProduction:
        source_path = self.paths.production_markdown
        source = self._production_source(source_path)
        if not source_path.exists():
            return AppProduction(source=source)

        metadata = ProductionScriptParser(source_path).parse_path().metadata
        production_version = self._parse_production_version(metadata.get("production_version"))
        parent_version = metadata.get("parent_production_version")
        normalized_parent = None if parent_version in (None, "none") else parent_version
        published_at = self._published_at(production_version, source)
        return AppProduction(
            source=source,
            version=str(production_version) if production_version is not None else None,
            sequence=production_version.sequence if production_version is not None else None,
            publication_id=production_version.publication_id if production_version is not None else None,
            parent_version=normalized_parent,
            published_at=published_at,
        )

    def _production_source(self, source_path: Path) -> str:
        current_path = ProductionVersionStore(self.paths).current_production_path()
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

    def _manifest_build_id(self) -> str:
        return self.build_id or uuid4().hex

    def _manifest_build_timestamp(self) -> str:
        return self.build_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def plan_audio_work(self) -> list[PlaybookAudioWorkItem]:
        work_items: list[PlaybookAudioWorkItem] = []
        work_items.extend(self._role_audio_work_items())
        work_items.extend(self._context_audio_work_items())
        return work_items

    def _build_sections(self) -> list[AppSection]:
        sections: list[AppSection] = []
        for ordinal, part in enumerate(self.play.parts):
            title_block = next((block for block in part.blocks if isinstance(block, TitleBlock)), None)
            title = part.title or (title_block.heading if title_block else None)
            if title is None:
                title = self.play.title if part.part_no is None else f"Part {part.part_no + 1}"
            sections.append(
                AppSection(
                    id="play" if part.part_no is None else f"part-{part.part_no}",
                    part_id=part.part_no,
                    block_id=self._block_id_for(title_block) if title_block else None,
                    title=title,
                    ordinal=ordinal,
                )
            )
        return sections

    def _context_blocks(self) -> list[TitleBlock | DescriptionBlock | DirectionBlock | BlockingBlock]:
        return [
            block
            for block in self.play.blocks
            if isinstance(block, (TitleBlock, DescriptionBlock, DirectionBlock, BlockingBlock)) and block.segments
        ]

    def _context_audio_work_items(self) -> list[PlaybookAudioWorkItem]:
        work_items: list[PlaybookAudioWorkItem] = []
        for block in self._context_blocks():
            if isinstance(block, BlockingBlock):
                continue
            segment_id = str(block.segments[0].segment_id)
            work_items.append(
                PlaybookAudioWorkItem(
                    source_path=self.paths.segments_dir / "_NARRATOR" / f"{segment_id}.wav",
                    role="_NARRATOR",
                    segment_id=segment_id,
                    category="context",
                )
            )
        return work_items

    def _role_audio_work_items(self) -> list[PlaybookAudioWorkItem]:
        work_items: list[PlaybookAudioWorkItem] = []
        for role in self.play.roles:
            if role.meta or role.name.startswith("_"):
                continue
            for block in role.blocks:
                response_segments = self._response_segments_for_role(block, role.name)
                if not response_segments:
                    continue
                cue_selection = self.selector.select_for_block(block)
                work_items.append(
                    PlaybookAudioWorkItem(
                        source_path=cue_selection.audio_path,
                        role=cue_selection.source_role,
                        segment_id=cue_selection.audio_path.stem,
                        category="cue",
                    )
                )
                callout_source = self._callout_source_for(block)
                if callout_source is not None:
                    work_items.append(
                        PlaybookAudioWorkItem(
                            source_path=callout_source,
                            role=block.callout or "_CALLER",
                            segment_id=callout_source.stem,
                            category="callout",
                        )
                    )
                for segment in response_segments:
                    segment_id = str(segment.segment_id)
                    work_items.append(
                        PlaybookAudioWorkItem(
                            source_path=self.paths.segments_dir / role.name / f"{segment_id}.wav",
                            role=role.name,
                            segment_id=segment_id,
                            category="response",
                        )
                    )
                for segment in self._inline_direction_segments_for(block):
                    segment_id = str(segment.segment_id)
                    work_items.append(
                        PlaybookAudioWorkItem(
                            source_path=self.paths.segments_dir / "_NARRATOR" / f"{segment_id}.wav",
                            role="_NARRATOR",
                            segment_id=segment_id,
                            category="direction",
                        )
                    )
        return work_items

    def _build_context_blocks(self) -> list[AppContextBlock]:
        context_blocks: list[AppContextBlock] = []
        for block in self._context_blocks():
            segment = block.segments[0]
            segment_id = str(segment.segment_id)
            audio = None
            if not isinstance(block, BlockingBlock):
                audio = self._copy_required_audio(
                    source_path=self.paths.segments_dir / "_NARRATOR" / f"{segment_id}.wav",
                    role="_NARRATOR",
                    segment_id=segment_id,
                    category="context",
                )
            context_blocks.append(
                AppContextBlock(
                    id=self._required_production_id(block.production_id, f"context block {block.block_id}"),
                    part_id=block.block_id.part_id,
                    block_id=self._block_id_for(block),
                    kind=self._context_kind_for(block),
                    speaker="_NARRATOR",
                    text=self._context_text_for(block),
                    content_hash=block.content_hash,
                    audio=audio,
                    targets=list(block.targets) if isinstance(block, BlockingBlock) else None,
                    placement=block.placement if isinstance(block, BlockingBlock) else None,
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
            self._build_callout(block)
            for segment in self._inline_direction_segments_for(block):
                self._copy_required_audio(
                    source_path=self.paths.segments_dir / "_NARRATOR" / f"{segment.segment_id}.wav",
                    role="_NARRATOR",
                    segment_id=str(segment.segment_id),
                    category="direction",
                )

            lines.append(
                AppLine(
                    id=AppLine.line_id_for(block, role.name),
                    part_id=block.block_id.part_id,
                    block_id=AppLine.block_id_for(block),
                    role=role.name,
                    speaker=block.callout or role.name,
                    content_hash=block.content_hash,
                    cue=self._build_cue(cue_selection),
                    response=AppResponse(
                        text=" ".join(segment.text for segment in response_segments),
                        segments=[self._build_response_segment(role.name, segment) for segment in response_segments],
                    ),
                    directions=[
                        AppDirection.from_segment(segment, placement="inline")
                        for segment in self._inline_direction_segments_for(block)
                    ],
                    blocking=[
                        AppBlocking.from_segment(segment, placement="inline")
                        for segment in block.segments
                        if isinstance(segment, BlockingSegment)
                    ],
                    previous_roles=self.play.getPrecedingRoles(block.block_id, include_meta_roles=True),
                    simultaneous=any(isinstance(segment, SimultaneousSegment) for segment in response_segments),
                )
            )
        app_role.lines = lines
        return app_role

    def _inline_direction_segments_for(self, block: RoleBlock) -> list[DirectionSegment]:
        return [segment for segment in block.segments if isinstance(segment, DirectionSegment)]

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

    def _context_kind_for(self, block: TitleBlock | DescriptionBlock | DirectionBlock | BlockingBlock) -> str:
        if isinstance(block, TitleBlock):
            return "heading"
        if isinstance(block, DescriptionBlock):
            return "description"
        if isinstance(block, BlockingBlock):
            return "blocking"
        return "direction"

    def _context_text_for(self, block: TitleBlock | DescriptionBlock | DirectionBlock | BlockingBlock) -> str:
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
            id=self._required_production_id(segment.production_id, f"response segment {segment.segment_id}"),
            segment_id=str(segment.segment_id),
            content_hash=segment.content_hash,
            owners=owners,
            text=segment.text,
            audio=asset,
            simultaneous=isinstance(segment, SimultaneousSegment),
        )

    def _build_callout(self, block: RoleBlock) -> None:
        source_path = self._callout_source_for(block)
        if source_path is None:
            return
        self._copy_required_audio(
            source_path=source_path,
            role=block.callout or "_CALLER",
            segment_id=source_path.stem,
            category="callout",
            destination_dir="callouts",
        )


    def _callout_source_for(self, block: RoleBlock) -> Path | None:
        if block.callout is None:
            return None
        return self._resolve_callout_source(block.callout)

    def _resolve_callout_source(self, callout: str) -> Path | None:
        base_dir = self.paths.build_dir / "audio" / "callouts"
        if not base_dir.exists():
            return None

        candidate_names = self._callout_candidate_names(callout)
        for candidate_name, ext in itertools.product(candidate_names, (".wav", ".mp3")):
            direct = base_dir / f"{candidate_name}{ext}"
            if direct.exists():
                return direct
            nested = base_dir / candidate_name / f"{candidate_name}{ext}"
            if nested.exists():
                return nested

        target_keys = {self._normalize_callout_name(name) for name in candidate_names}
        for candidate_file in sorted(base_dir.rglob("*")):
            if not candidate_file.is_file() or candidate_file.suffix.lower() not in {".wav", ".mp3"}:
                continue
            if self._normalize_callout_name(candidate_file.stem) in target_keys:
                self._logger.warning(
                    "Resolved callout '%s' using fallback source %s",
                    callout,
                    paths.display_path(candidate_file),
                )
                return candidate_file
        return None

    def _callout_candidate_names(self, callout: str) -> list[str]:
        candidates: list[str] = []

        def append(name: str) -> None:
            if name and name not in candidates:
                candidates.append(name)

        append(callout)
        append(callout.replace("-", " "))
        append(callout.replace(" ", "-"))

        if "-" in callout:
            base = callout.split("-", 1)[0]
            append(base)
            append(base.replace(" ", "-"))
            append(base.replace("-", " "))

        return candidates

    def _normalize_callout_name(self, value: str) -> str:
        return value.replace("-", " ").strip().lower()

    def _required_production_id(self, production_id: str | None, description: str) -> str:
        if production_id is None:
            raise RuntimeError(f"Missing production id for {description}")
        return production_id

    def _copy_required_audio(
        self,
        source_path: Path,
        role: str,
        segment_id: str,
        category: str,
        destination_dir: str = "segments",
    ) -> AppAudioAsset:
        if not source_path.exists():
            raise RuntimeError(
                f"Missing required {category} audio for role {role} segment {segment_id} "
                f"while building Playbook: {paths.display_path(source_path)}"
            )
        cache_key = (source_path, category, destination_dir)
        cached = self._audio_asset_cache.get(cache_key)
        if cached is not None:
            return cached
        duration_ms = self.paths.get_audio_length_ms(source_path)
        cue_start_offsets: list[AppCueStartOffset] = []
        if category == "cue":
            assert self.cue_start_offset_analyzer is not None
            cue_start_offsets = self.cue_start_offset_analyzer.analyze(source_path, duration_ms)
        assert self.audio_packager is not None
        packaged_audio = self.audio_packager.package(
            source_path,
            self.app_dir / "audio" / destination_dir / role,
        )
        asset = AppAudioAsset(
            path=packaged_audio.manifest_path,
            duration_ms=duration_ms,
            required=True,
            cue_start_offsets=cue_start_offsets,
        )
        self._manifest_assets.append(asset)
        self._audio_asset_cache[cache_key] = asset
        if self.progress_reporter is not None:
            self.progress_reporter.audio_packaged(role, segment_id, category)
        return asset

    def _write_zip(self) -> None:
        self.zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.app_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(self.app_dir).as_posix())
