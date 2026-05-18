from __future__ import annotations

from dataclasses import dataclass

from stager.domain.play import Play, Role
from stager.production.cast_config import CastConfig, CastRoleAssignment
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

    @property
    def assigned(self) -> bool:
        return self.actor is not None

    @property
    def complete(self) -> bool:
        return self.expected_segments == self.recorded_segments


@dataclass(frozen=True)
class ProductionStatus:
    play_id: str
    play_title: str
    current_published_version: str | None
    working_production_version: str | None
    has_unpublished_changes: bool
    roles: tuple[RoleProductionStatus, ...]
    cast_configured: bool

    @property
    def missing_recording_count(self) -> int:
        return sum(len(role.missing_segments) for role in self.roles)

    @property
    def unassigned_roles(self) -> tuple[str, ...]:
        return tuple(role.role for role in self.roles if not role.assigned)


class ProductionStatusService:
    def __init__(self, *, paths_config: paths.PathConfig, play: Play) -> None:
        self.paths_config = paths_config
        self.play = play

    def build(self) -> ProductionStatus:
        cast_config = CastConfig.load(self.paths_config)
        diff = ProductionPublisher(paths_config=self.paths_config).diff_with_versions()
        current_version = diff.current_version.production_version if diff.current_version is not None else None
        role_statuses = tuple(
            self._role_status(role, cast_config.assignment_for_role(role.name))
            for role in self.play.roles
            if not role.meta and not role.name.startswith("_")
        )
        return ProductionStatus(
            play_id=self.paths_config.play_name,
            play_title=self.play.title,
            current_published_version=str(current_version) if current_version is not None else None,
            working_production_version=str(diff.working_production_version)
            if diff.working_production_version is not None
            else None,
            has_unpublished_changes=bool(diff.change_report.changes),
            roles=role_statuses,
            cast_configured=bool(cast_config.actors or cast_config.roles),
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
        )
