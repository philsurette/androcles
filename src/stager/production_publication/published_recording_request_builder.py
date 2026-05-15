from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.domain.block import RoleBlock
from stager.domain.play import Play
from stager.domain.segment import SimultaneousSegment, SpeechSegment
from stager.linerecorder.recording_request_builder import RecordingRequestBuilder
from stager.shared import paths


@dataclass
class PublishedRecordingRequestBuilder:
    play: Play
    paths_config: paths.PathConfig
    line_reasons: dict[str, str]
    version_label: str
    build_id: str | None = None
    build_timestamp: str | None = None

    def build(self) -> list[Path]:
        selected_by_role: dict[str, set[str]] = {}
        reasons_by_item: dict[str, str] = {}
        for block in self.play.blocks:
            if not isinstance(block, RoleBlock):
                continue
            if block.production_id not in self.line_reasons:
                continue
            reason = self.line_reasons[block.production_id]
            for segment in block.segments:
                if isinstance(segment, SpeechSegment) and not segment.role.startswith("_"):
                    segment_id = self._segment_id(segment.production_id)
                    selected_by_role.setdefault(segment.role, set()).add(segment_id)
                    reasons_by_item[segment_id] = reason
                elif isinstance(segment, SimultaneousSegment):
                    segment_id = self._segment_id(segment.production_id)
                    reasons_by_item[segment_id] = reason
                    for role in segment.roles:
                        if not role.startswith("_"):
                            selected_by_role.setdefault(role, set()).add(segment_id)
        zip_paths: list[Path] = []
        for role, item_ids in sorted(selected_by_role.items()):
            zip_paths.append(
                RecordingRequestBuilder(
                    play=self.play,
                    paths=self.paths_config,
                    role=role,
                    build_id=self.build_id,
                    build_timestamp=self.build_timestamp,
                    request_kind=f"production_update_{self.version_label}",
                    selected_segment_ids=item_ids,
                    selected_item_reasons=reasons_by_item,
                    notes=f"Production update {self.version_label}.",
                ).build()
            )
        return zip_paths

    def _segment_id(self, production_id: str | None) -> str:
        if production_id is None:
            raise RuntimeError("Recordable segment is missing production id")
        return production_id
