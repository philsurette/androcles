from __future__ import annotations

from dataclasses import dataclass
import json

from stager.domain.play import Play, Role
from stager.production.cast_config import CastConfig, CastRoleAssignment, SUPPORTED_RECORDING_METHODS
from stager.production_publication.production_publisher import ProductionPublisher
from stager.shared import paths


@dataclass(frozen=True)
class RoleProductionStatus:
    role: str
    actor: str | None
    recording: str
    expected_segments: int
    recorded_segments: int
    missing_segments: tuple[str, ...]
    voice_profile: str | None = None
    source_recording_exists: bool | None = None

    @property
    def assigned(self) -> bool:
        return self.actor is not None

    @property
    def complete(self) -> bool:
        return self.expected_segments == self.recorded_segments

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "actor": self.actor,
            "recording": self.recording,
            "expected_segments": self.expected_segments,
            "recorded_segments": self.recorded_segments,
            "missing_segments": list(self.missing_segments),
            "complete": self.complete,
            "voice_profile": self.voice_profile,
            "source_recording_exists": self.source_recording_exists,
        }


@dataclass(frozen=True)
class PlaybookProductionStatus:
    exists: bool
    build_id: str | None = None
    build_timestamp: str | None = None
    production_version: str | None = None
    production_source: str | None = None
    matches_current_published_version: bool | None = None

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "build_id": self.build_id,
            "build_timestamp": self.build_timestamp,
            "production_version": self.production_version,
            "production_source": self.production_source,
            "matches_current_published_version": self.matches_current_published_version,
        }


@dataclass(frozen=True)
class ProductionStatus:
    play_id: str
    play_title: str
    current_published_version: str | None
    working_production_version: str | None
    has_unpublished_changes: bool
    roles: tuple[RoleProductionStatus, ...]
    cast_configured: bool
    playbook: PlaybookProductionStatus

    @property
    def missing_recording_count(self) -> int:
        return sum(len(role.missing_segments) for role in self.roles)

    @property
    def unassigned_roles(self) -> tuple[str, ...]:
        return tuple(role.role for role in self.roles if not role.assigned)

    def to_dict(self) -> dict:
        return {
            "play_id": self.play_id,
            "play_title": self.play_title,
            "current_published_version": self.current_published_version,
            "working_production_version": self.working_production_version,
            "has_unpublished_changes": self.has_unpublished_changes,
            "cast_configured": self.cast_configured,
            "missing_recording_count": self.missing_recording_count,
            "unassigned_roles": list(self.unassigned_roles),
            "roles": [role.to_dict() for role in self.roles],
            "playbook": self.playbook.to_dict(),
        }


class ProductionStatusService:
    def __init__(self, *, paths_config: paths.PathConfig, play: Play) -> None:
        self.paths_config = paths_config
        self.play = play

    def build(self) -> ProductionStatus:
        cast_config = CastConfig.load(self.paths_config)
        self._validate_cast_roles(cast_config)
        diff = ProductionPublisher(paths_config=self.paths_config).diff_with_versions()
        current_version = diff.current_version.production_version if diff.current_version is not None else None
        current_version_text = str(current_version) if current_version is not None else None
        role_statuses = tuple(
            self._role_status(role, cast_config.assignment_for_role(role.name))
            for role in self.play.roles
            if not role.meta and not role.name.startswith("_")
        )
        return ProductionStatus(
            play_id=self.paths_config.play_name,
            play_title=self.play.title,
            current_published_version=current_version_text,
            working_production_version=str(diff.working_production_version)
            if diff.working_production_version is not None
            else None,
            has_unpublished_changes=bool(diff.change_report.changes),
            roles=role_statuses,
            cast_configured=bool(cast_config.actors or cast_config.roles),
            playbook=self._playbook_status(current_version_text),
        )

    def _role_status(self, role: Role, assignment: CastRoleAssignment | None) -> RoleProductionStatus:
        expected = tuple(segment_id for segment_ids in role.segments().values() for segment_id in segment_ids)
        missing = tuple(
            segment_id
            for segment_id in expected
            if not (self.paths_config.segments_dir / role.name / f"{segment_id}.wav").exists()
        )
        return RoleProductionStatus(
            role=role.name,
            actor=assignment.actor if assignment is not None else None,
            recording=assignment.recording if assignment is not None else "linerecorder",
            expected_segments=len(expected),
            recorded_segments=len(expected) - len(missing),
            missing_segments=missing,
            voice_profile=assignment.voice_profile if assignment is not None else None,
            source_recording_exists=self._source_recording_exists(role.name, assignment)
        )

    def _validate_cast_roles(self, cast_config: CastConfig) -> None:
        valid_roles = {role.name for role in self.play.roles if not role.meta and not role.name.startswith("_")}
        unknown_roles = sorted(set(cast_config.roles) - valid_roles)
        if unknown_roles:
            raise RuntimeError(f"cast.yaml references unknown rehearsable role(s): {', '.join(unknown_roles)}")
        invalid_recording_methods = sorted(
            {
                assignment.recording
                for assignment in cast_config.roles.values()
                if assignment.recording not in SUPPORTED_RECORDING_METHODS
            }
        )
        if invalid_recording_methods:
            raise RuntimeError(f"cast.yaml uses invalid recording method(s): {', '.join(invalid_recording_methods)}")

    def _source_recording_exists(self, role: str, assignment: CastRoleAssignment | None) -> bool | None:
        if assignment is None or assignment.recording != "whole-role":
            return None
        return any(self.paths_config.recordings_dir.glob(f"{role}*.wav"))

    def _playbook_status(self, current_published_version: str | None) -> PlaybookProductionStatus:
        manifest_path = self.paths_config.build_dir / "app" / "manifest.json"
        if not manifest_path.exists():
            return PlaybookProductionStatus(exists=False)
        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return PlaybookProductionStatus(exists=True)
        build = raw_manifest.get("build") if isinstance(raw_manifest, dict) else None
        production = raw_manifest.get("production") if isinstance(raw_manifest, dict) else None
        build = build if isinstance(build, dict) else {}
        production = production if isinstance(production, dict) else {}
        production_version = production.get("version") if isinstance(production.get("version"), str) else None
        matches_current = None
        if current_published_version is not None:
            matches_current = production_version == current_published_version
        return PlaybookProductionStatus(
            exists=True,
            build_id=build.get("buildId") if isinstance(build.get("buildId"), str) else None,
            build_timestamp=build.get("buildTimestamp") if isinstance(build.get("buildTimestamp"), str) else None,
            production_version=production_version,
            production_source=production.get("source") if isinstance(production.get("source"), str) else None,
            matches_current_published_version=matches_current,
        )
