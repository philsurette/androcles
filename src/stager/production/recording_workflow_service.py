from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from stager.audio.segment_build_service import SegmentBuildService
from stager.domain.block import RoleBlock
from stager.domain.play import Play
from stager.domain.segment import SimultaneousSegment, SpeechSegment
from stager.linerecorder.recording_request_builder import RecordingRequestBuilder
from stager.linerecorder.role_recordings_importer import (
    RecordingImportProcessingOptions,
    RoleRecordingsImporter,
    RoleRecordingsImportResult,
)
from stager.production.cast_config import CastConfig
from stager.production.production_status import ProductionStatusService
from stager.production_publication.production_publisher import ProductionPublisher
from stager.shared import paths


@dataclass(frozen=True)
class RecordingRequestBuildResult:
    role: str
    actor: str | None
    path: Path
    item_count: int
    request_kind: str


@dataclass(frozen=True)
class RecordingRequestSelectionResult:
    requests: tuple[RecordingRequestBuildResult, ...]
    skipped_whole_role_roles: tuple[str, ...]


@dataclass(frozen=True)
class SplitRecordingsResult:
    roles: tuple[str, ...]
    skipped_linerecorder_roles: tuple[str, ...]


class RecordingWorkflowService:
    def __init__(self, *, paths_config: paths.PathConfig, play: Play) -> None:
        self.paths_config = paths_config
        self.play = play

    def send_requests(
        self,
        *,
        role: str | None = None,
        actor: str | None = None,
        changed_only: bool = False,
        missing_only: bool = False,
        notes: str | None = None,
    ) -> RecordingRequestSelectionResult:
        if changed_only and missing_only:
            raise RuntimeError("Use either --changed-only or --missing-only, not both.")
        cast_config = CastConfig.load(self.paths_config)
        roles = self._selected_roles(role=role, actor=actor, cast_config=cast_config)
        skipped_whole_role_roles = tuple(
            selected_role
            for selected_role in roles
            if self._recording_method(selected_role, cast_config) == "whole-role"
        )
        request_roles = tuple(
            selected_role
            for selected_role in roles
            if self._recording_method(selected_role, cast_config) != "whole-role"
        )
        build_id, build_timestamp = self._read_playbook_build_metadata()
        requests = []
        for selected_role in request_roles:
            selected_item_ids, item_reasons, request_kind = self._request_selection(
                role=selected_role,
                changed_only=changed_only,
                missing_only=missing_only,
            )
            if selected_item_ids is not None and not selected_item_ids:
                continue
            actor_id = self._actor_for_role(selected_role, cast_config)
            request_notes = self._request_notes(actor_id=actor_id, notes=notes)
            builder = RecordingRequestBuilder(
                play=self.play,
                paths=self.paths_config,
                role=selected_role,
                build_id=build_id,
                build_timestamp=build_timestamp,
                request_kind=request_kind,
                selected_segment_ids=selected_item_ids,
                selected_item_reasons=item_reasons,
                notes=request_notes,
            )
            path = builder.build()
            manifest = json.loads((builder.request_dir / "manifest.json").read_text(encoding="utf-8"))
            requests.append(
                RecordingRequestBuildResult(
                    role=selected_role,
                    actor=actor_id,
                    path=path,
                    item_count=len(manifest["items"]),
                    request_kind=request_kind,
                )
            )
        return RecordingRequestSelectionResult(
            requests=tuple(requests),
            skipped_whole_role_roles=skipped_whole_role_roles,
        )

    def receive_recordings(
        self,
        *,
        package_path: Path,
        denoise: bool = False,
        trim_silence: bool = False,
    ) -> RoleRecordingsImportResult:
        return RoleRecordingsImporter(paths=self.paths_config, play=self.play).import_package(
            package_path,
            processing_options=RecordingImportProcessingOptions(denoise=denoise, trim_silence=trim_silence),
        )

    def split_recordings(
        self,
        *,
        role: str | None = None,
        include_linerecorder: bool = False,
        silence_thresh: int = -60,
        separator_len_ms: int = 1700,
        chunk_size: int = 50,
        force: bool = False,
    ) -> SplitRecordingsResult:
        cast_config = CastConfig.load(self.paths_config)
        roles = self._selected_roles(role=role, actor=None, cast_config=cast_config)
        linerecorder_roles = tuple(
            selected_role
            for selected_role in roles
            if self._recording_method(selected_role, cast_config) != "whole-role"
        )
        split_roles = roles if include_linerecorder else tuple(
            selected_role
            for selected_role in roles
            if self._recording_method(selected_role, cast_config) == "whole-role"
        )
        for selected_role in split_roles:
            SegmentBuildService(paths=self.paths_config).build(
                role=selected_role,
                silence_thresh=silence_thresh,
                separator_len_ms=separator_len_ms,
                chunk_size=chunk_size,
                force=force,
            )
        return SplitRecordingsResult(
            roles=tuple(split_roles),
            skipped_linerecorder_roles=() if include_linerecorder else linerecorder_roles,
        )

    def _selected_roles(self, *, role: str | None, actor: str | None, cast_config: CastConfig) -> tuple[str, ...]:
        valid_roles = self._ordered_role_ids()
        if role is not None and role not in valid_roles:
            raise RuntimeError(f"Unknown rehearsable role: {role}")
        roles = (role,) if role is not None else valid_roles
        if actor is None:
            return roles
        return tuple(
            selected_role
            for selected_role in roles
            if self._actor_for_role(selected_role, cast_config) == actor
        )

    def _ordered_role_ids(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.play.roles if not role.meta and not role.name.startswith("_"))

    def _recording_method(self, role: str, cast_config: CastConfig) -> str:
        assignment = cast_config.assignment_for_role(role)
        return assignment.recording if assignment is not None else "linerecorder"

    def _actor_for_role(self, role: str, cast_config: CastConfig) -> str | None:
        assignment = cast_config.assignment_for_role(role)
        return assignment.actor if assignment is not None else None

    def _request_notes(self, *, actor_id: str | None, notes: str | None) -> str | None:
        parts = []
        if actor_id is not None:
            parts.append(f"Actor: {actor_id}")
        if notes is not None and notes.strip():
            parts.append(notes.strip())
        return "\n".join(parts) if parts else None

    def _request_selection(
        self,
        *,
        role: str,
        changed_only: bool,
        missing_only: bool,
    ) -> tuple[set[str] | None, dict[str, str] | None, str]:
        if changed_only:
            return self._changed_item_ids(role), self._changed_item_reasons(role), "changed_segments"
        if missing_only:
            return self._missing_item_ids(role), None, "missing_segments"
        return None, None, "full_role"

    def _changed_item_ids(self, role: str) -> set[str]:
        diff = ProductionPublisher(paths_config=self.paths_config).diff()
        changed_line_ids = {
            change.current.id
            for change in (*diff.added, *diff.changed_id_reuse)
            if change.current is not None and change.current.roles
        }
        return {
            production_id
            for block in self._role_blocks(role)
            if block.production_id in changed_line_ids
            for production_id in self._recordable_production_ids(block, role)
        }

    def _changed_item_reasons(self, role: str) -> dict[str, str]:
        diff = ProductionPublisher(paths_config=self.paths_config).diff()
        added = {
            change.current.id
            for change in diff.added
            if change.current is not None and change.current.roles
        }
        changed = {
            change.current.id
            for change in diff.changed_id_reuse
            if change.current is not None and change.current.roles
        }
        reasons = {}
        for block in self._role_blocks(role):
            if block.production_id in added:
                reason = "script_added"
            elif block.production_id in changed:
                reason = "script_changed"
            else:
                continue
            for production_id in self._recordable_production_ids(block, role):
                reasons[production_id] = reason
        return reasons

    def _missing_item_ids(self, role: str) -> set[str]:
        status = ProductionStatusService(paths_config=self.paths_config, play=self.play).build()
        missing_segment_ids = {
            segment_id
            for role_status in status.roles
            if role_status.role == role
            for segment_id in role_status.missing_segments
        }
        return {
            production_id
            for block in self._role_blocks(role)
            for segment_id, production_id in self._recordable_segments(block, role).items()
            if segment_id in missing_segment_ids
        }

    def _role_blocks(self, role: str) -> tuple[RoleBlock, ...]:
        return tuple(block for block in self.play.blocks if isinstance(block, RoleBlock) and role in block.role_names)

    def _recordable_production_ids(self, block: RoleBlock, role: str) -> set[str]:
        return set(self._recordable_segments(block, role).values())

    def _recordable_segments(self, block: RoleBlock, role: str) -> dict[str, str]:
        result = {}
        for segment in block.segments:
            if isinstance(segment, SpeechSegment) and segment.role == role:
                result[str(segment.segment_id)] = self._required_production_id(segment.production_id)
            elif isinstance(segment, SimultaneousSegment) and role in segment.roles:
                result[str(segment.segment_id)] = self._required_production_id(segment.production_id)
        return result

    def _required_production_id(self, production_id: str | None) -> str:
        if production_id is None:
            raise RuntimeError("Recordable segment is missing production id")
        return production_id

    def _read_playbook_build_metadata(self) -> tuple[str | None, str | None]:
        manifest_path = self.paths_config.build_dir / "app" / "manifest.json"
        if not manifest_path.exists():
            return None, None
        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None, None
        build = raw_manifest.get("build") if isinstance(raw_manifest, dict) else None
        if not isinstance(build, dict):
            return None, None
        build_id = build.get("buildId")
        build_timestamp = build.get("buildTimestamp")
        return (
            build_id if isinstance(build_id, str) and build_id else None,
            build_timestamp if isinstance(build_timestamp, str) and build_timestamp else None,
        )
