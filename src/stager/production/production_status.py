from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from stager.audio.voice_profile_config import VoiceProfileConfig
from stager.domain.play import Play, Role
from stager.domain.segment import SimultaneousSegment, SpeechSegment
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
    stale_segments: tuple[str, ...] = ()
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
            "stale_segments": list(self.stale_segments),
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
class AudioplayProductionStatus:
    exists: bool
    build_timestamp: str | None = None
    production_version: str | None = None
    production_source: str | None = None
    audio_format: str | None = None
    audio_source: str | None = None
    matches_current_published_version: bool | None = None

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "build_timestamp": self.build_timestamp,
            "production_version": self.production_version,
            "production_source": self.production_source,
            "audio_format": self.audio_format,
            "audio_source": self.audio_source,
            "matches_current_published_version": self.matches_current_published_version,
        }


@dataclass(frozen=True)
class CleanupReviewProductionStatus:
    exists: bool
    reviewed_segments: int = 0
    expected_segments: int = 0
    missing_segments: tuple[str, ...] = ()
    missing_output_segments: tuple[str, ...] = ()
    warning_count: int = 0
    fallback_count: int = 0

    @property
    def complete(self) -> bool:
        return self.exists and not self.missing_segments and not self.missing_output_segments

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "reviewed_segments": self.reviewed_segments,
            "expected_segments": self.expected_segments,
            "missing_segments": list(self.missing_segments),
            "missing_output_segments": list(self.missing_output_segments),
            "warning_count": self.warning_count,
            "fallback_count": self.fallback_count,
            "complete": self.complete,
        }


@dataclass(frozen=True)
class VoiceProfileProductionStatus:
    configured_profiles: int
    expected_segments: int
    rendered_segments: int
    missing_segments: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.expected_segments == self.rendered_segments and not self.missing_segments

    def to_dict(self) -> dict:
        return {
            "configured_profiles": self.configured_profiles,
            "expected_segments": self.expected_segments,
            "rendered_segments": self.rendered_segments,
            "missing_segments": list(self.missing_segments),
            "complete": self.complete,
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
    audioplay: AudioplayProductionStatus
    cleanup_review: CleanupReviewProductionStatus
    voice_profiles: VoiceProfileProductionStatus
    blocking_changes: tuple[str, ...] = ()

    @property
    def missing_recording_count(self) -> int:
        return sum(len(role.missing_segments) for role in self.roles)

    @property
    def stale_recording_count(self) -> int:
        return sum(len(role.stale_segments) for role in self.roles)

    @property
    def unassigned_roles(self) -> tuple[str, ...]:
        return tuple(role.role for role in self.roles if not role.assigned)

    @property
    def missing_source_recording_roles(self) -> tuple[str, ...]:
        return tuple(
            role.role
            for role in self.roles
            if role.recording == "whole-role" and role.source_recording_exists is False
        )

    def to_dict(self) -> dict:
        return {
            "play_id": self.play_id,
            "play_title": self.play_title,
            "current_published_version": self.current_published_version,
            "working_production_version": self.working_production_version,
            "has_unpublished_changes": self.has_unpublished_changes,
            "cast_configured": self.cast_configured,
            "missing_recording_count": self.missing_recording_count,
            "stale_recording_count": self.stale_recording_count,
            "unassigned_roles": list(self.unassigned_roles),
            "missing_source_recording_roles": list(self.missing_source_recording_roles),
            "blocking_changes": list(self.blocking_changes),
            "roles": [role.to_dict() for role in self.roles],
            "playbook": self.playbook.to_dict(),
            "audioplay": self.audioplay.to_dict(),
            "cleanup_review": self.cleanup_review.to_dict(),
            "voice_profiles": self.voice_profiles.to_dict(),
        }


class ProductionStatusService:
    def __init__(self, *, paths_config: paths.PathConfig, play: Play) -> None:
        self.paths_config = paths_config
        self.play = play

    def build(self) -> ProductionStatus:
        cast_config = CastConfig.load(self.paths_config)
        self._validate_cast_roles(cast_config)
        self._validate_cast_voice_profiles(cast_config)
        diff = ProductionPublisher(paths_config=self.paths_config).diff_with_versions()
        current_version = diff.current_version.production_version if diff.current_version is not None else None
        current_version_text = str(current_version) if current_version is not None else None
        blocking_changes = tuple(change.line_id for change in diff.change_report.blocking_changed)
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
            audioplay=self._audioplay_status(current_version_text),
            cleanup_review=self._cleanup_review_status(),
            voice_profiles=self._voice_profile_status(),
            blocking_changes=blocking_changes,
        )

    def _role_status(self, role: Role, assignment: CastRoleAssignment | None) -> RoleProductionStatus:
        expected_hashes = self._role_segment_hashes(role)
        expected = tuple(expected_hashes)
        missing = tuple(
            segment_id
            for segment_id in expected
            if not (self.paths_config.segments_dir / role.name / f"{segment_id}.wav").exists()
        )
        stale = self._stale_imported_segments(role.name, expected_hashes)
        return RoleProductionStatus(
            role=role.name,
            actor=assignment.actor if assignment is not None else None,
            recording=assignment.recording if assignment is not None else "linerecorder",
            expected_segments=len(expected),
            recorded_segments=len(expected) - len(missing),
            missing_segments=missing,
            stale_segments=stale,
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

    def _validate_cast_voice_profiles(self, cast_config: CastConfig) -> None:
        requested_profile_ids = {
            assignment.voice_profile
            for assignment in cast_config.roles.values()
            if assignment.voice_profile is not None
        }
        if not requested_profile_ids:
            return
        if not (self.paths_config.play_dir / "voice_profiles.yaml").exists():
            return
        voice_config = VoiceProfileConfig.load(self.paths_config)
        unknown_profiles = sorted(requested_profile_ids - set(voice_config.cast_profiles))
        if unknown_profiles:
            raise RuntimeError(f"cast.yaml references unknown voice profile(s): {', '.join(unknown_profiles)}")
        unknown_actors = sorted(
            {
                assignment.actor
                for assignment in cast_config.roles.values()
                if assignment.actor is not None and assignment.voice_profile is not None
            }
            - set(voice_config.actors)
        )
        if unknown_actors:
            raise RuntimeError(f"cast.yaml voice-profile roles reference unknown voice actor(s): {', '.join(unknown_actors)}")
        mismatched_profiles = sorted(
            profile_id
            for role_id, assignment in cast_config.roles.items()
            for profile_id in [assignment.voice_profile]
            if profile_id is not None
            and profile_id in voice_config.cast_profiles
            and (
                voice_config.cast_profiles[profile_id].role != role_id
                or (
                    assignment.actor is not None
                    and voice_config.cast_profiles[profile_id].actor != assignment.actor
                )
            )
        )
        if mismatched_profiles:
            raise RuntimeError(
                "cast.yaml voice_profile assignment does not match role/actor: "
                + ", ".join(mismatched_profiles)
            )

    def _source_recording_exists(self, role: str, assignment: CastRoleAssignment | None) -> bool | None:
        if assignment is None or assignment.recording != "whole-role":
            return None
        return any(self.paths_config.recordings_dir.glob(f"{role}*.wav"))

    def _role_segment_hashes(self, role: Role) -> dict[str, str | None]:
        hashes: dict[str, str | None] = {}
        for block in role.blocks:
            key = (block.block_id.part_id, block.block_id.block_no)
            for segment in block.segments:
                if isinstance(segment, SpeechSegment) and segment.role == role.name:
                    segment_id = f"{'' if key[0] is None else key[0]}_{key[1]}_{segment.segment_id.segment_no}"
                    hashes[segment_id] = segment.content_hash
                elif isinstance(segment, SimultaneousSegment) and role.name in segment.roles:
                    segment_id = f"{'' if key[0] is None else key[0]}_{key[1]}_{segment.segment_id.segment_no}"
                    hashes[segment_id] = segment.content_hash
        return hashes

    def _all_expected_segment_keys(self) -> dict[tuple[str, str], str | None]:
        expected = {}
        for role in self.play.roles:
            if role.meta or role.name.startswith("_"):
                continue
            for segment_id, content_hash in self._role_segment_hashes(role).items():
                expected[(role.name, segment_id)] = content_hash
        return expected

    def _stale_imported_segments(self, role: str, expected_hashes: dict[str, str | None]) -> tuple[str, ...]:
        imported = self._latest_imported_segment_hashes()
        stale = []
        for segment_id, current_hash in expected_hashes.items():
            if current_hash is None:
                continue
            target = f"{role}/{segment_id}.wav"
            imported_hash = imported.get(target)
            if imported_hash is not None and imported_hash != current_hash:
                stale.append(segment_id)
        return tuple(stale)

    def _latest_imported_segment_hashes(self) -> dict[str, str]:
        imports_dir = self.paths_config.build_dir / "linerecorder" / "imports"
        if not imports_dir.exists():
            return {}
        latest: dict[str, str] = {}
        for manifest_path in sorted(imports_dir.glob("*/import.json")):
            try:
                transaction = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for item in transaction.get("imported", []):
                if not isinstance(item, dict):
                    continue
                target_path = item.get("target_path")
                segment_hash = item.get("segment_content_hash")
                if isinstance(target_path, str) and isinstance(segment_hash, str):
                    target_file = self.paths_config.segments_dir / target_path
                    if target_file.exists() and target_file.stat().st_mtime > manifest_path.stat().st_mtime:
                        continue
                    latest[target_path] = segment_hash
        return latest

    def _cleanup_review_status(self) -> CleanupReviewProductionStatus:
        expected = self._all_expected_segment_keys()
        review_path = self.paths_config.audio_out_dir / "cleaned" / "cleanup_review.json"
        if not review_path.exists():
            return CleanupReviewProductionStatus(exists=False, expected_segments=len(expected))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        reviewed: set[tuple[str, str]] = set()
        missing_output = []
        warning_count = 0
        fallback_count = 0
        for entry in review.get("entries", []):
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            segment_id = entry.get("segment_id")
            if not isinstance(role, str) or not isinstance(segment_id, str):
                continue
            key = (role, segment_id)
            if key not in expected:
                continue
            reviewed.add(key)
            warnings = entry.get("warnings")
            if isinstance(warnings, list):
                warning_count += len(warnings)
            if entry.get("fallback") is True:
                fallback_count += 1
            output_path = entry.get("output_path")
            if not isinstance(output_path, str) or not self._path_from_record(output_path).exists():
                missing_output.append(f"{role}/{segment_id}")
        missing = tuple(f"{role}/{segment_id}" for role, segment_id in sorted(set(expected) - reviewed))
        return CleanupReviewProductionStatus(
            exists=True,
            reviewed_segments=len(reviewed),
            expected_segments=len(expected),
            missing_segments=missing,
            missing_output_segments=tuple(sorted(missing_output)),
            warning_count=warning_count,
            fallback_count=fallback_count,
        )

    def _voice_profile_status(self) -> VoiceProfileProductionStatus:
        config = VoiceProfileConfig.load(self.paths_config)
        active_profiles = tuple(profile for profile in config.cast_profiles.values() if profile.mode != "none")
        if not active_profiles:
            return VoiceProfileProductionStatus(configured_profiles=0, expected_segments=0, rendered_segments=0)
        expected = set()
        role_segments = {
            role.name: tuple(self._role_segment_hashes(role))
            for role in self.play.roles
            if not role.meta and not role.name.startswith("_")
        }
        for profile in active_profiles:
            for segment_id in role_segments.get(profile.role, ()):
                expected.add((profile.actor, profile.role, segment_id))
        rendered = self._rendered_voice_segments()
        present = expected & rendered
        missing = tuple(f"{actor}@{role}/{segment_id}" for actor, role, segment_id in sorted(expected - present))
        return VoiceProfileProductionStatus(
            configured_profiles=len(active_profiles),
            expected_segments=len(expected),
            rendered_segments=len(present),
            missing_segments=missing,
        )

    def _rendered_voice_segments(self) -> set[tuple[str, str, str]]:
        rendered = set()
        rendered_dir = self.paths_config.audio_out_dir / "rendered"
        if not rendered_dir.exists():
            return rendered
        for manifest_path in rendered_dir.glob("*/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            actor = manifest.get("actor")
            role = manifest.get("role")
            if not isinstance(actor, str) or not isinstance(role, str):
                continue
            for segment in manifest.get("segments", []):
                if not isinstance(segment, dict):
                    continue
                segment_id = segment.get("segment_id")
                output_path = segment.get("output_path")
                if isinstance(segment_id, str) and isinstance(output_path, str) and self._path_from_record(output_path).exists():
                    rendered.add((actor, role, segment_id))
        return rendered

    def _path_from_record(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return paths.project_root() / path

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

    def _audioplay_status(self, current_published_version: str | None) -> AudioplayProductionStatus:
        manifest_path = self.paths_config.audio_play_dir / "audioplay_manifest.json"
        if not manifest_path.exists():
            return AudioplayProductionStatus(exists=False)
        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return AudioplayProductionStatus(exists=True)
        build = raw_manifest.get("build") if isinstance(raw_manifest, dict) else None
        production = raw_manifest.get("production") if isinstance(raw_manifest, dict) else None
        options = raw_manifest.get("options") if isinstance(raw_manifest, dict) else None
        build = build if isinstance(build, dict) else {}
        production = production if isinstance(production, dict) else {}
        options = options if isinstance(options, dict) else {}
        production_version = production.get("version") if isinstance(production.get("version"), str) else None
        matches_current = None
        if current_published_version is not None:
            matches_current = production_version == current_published_version
        return AudioplayProductionStatus(
            exists=True,
            build_timestamp=build.get("buildTimestamp") if isinstance(build.get("buildTimestamp"), str) else None,
            production_version=production_version,
            production_source=production.get("source") if isinstance(production.get("source"), str) else None,
            audio_format=options.get("audioFormat") if isinstance(options.get("audioFormat"), str) else None,
            audio_source=options.get("audioSource") if isinstance(options.get("audioSource"), str) else None,
            matches_current_published_version=matches_current,
        )
