from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stager.shared import paths


SUPPORTED_RECORDING_METHODS = {"linerecorder", "whole-role"}


@dataclass(frozen=True)
class CastActor:
    actor_id: str
    display_name: str
    email: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CastRoleAssignment:
    role: str
    actor: str | None = None
    recording: str = "linerecorder"
    voice_profile: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CastConfig:
    actors: dict[str, CastActor] = field(default_factory=dict)
    roles: dict[str, CastRoleAssignment] = field(default_factory=dict)

    @classmethod
    def load(cls, paths_config: paths.PathConfig) -> "CastConfig":
        return CastConfigParser().parse(paths_config.play_dir / "cast.yaml")

    def assignment_for_role(self, role: str) -> CastRoleAssignment | None:
        return self.roles.get(role)


class CastConfigParser:
    def parse(self, path: Path) -> CastConfig:
        if not path.exists():
            return CastConfig()
        raw = self._load_yaml(path)
        if raw is None:
            return CastConfig()
        raw = self._mapping(raw, "cast config", path)
        version = raw.get("version", 1)
        if version != 1:
            raise RuntimeError(f"Unsupported cast config version {version!r} in {paths.display_path(path)}")
        actors = self._parse_actors(raw.get("actors", {}), path)
        roles = self._parse_roles(raw.get("roles", {}), path)
        for role_assignment in roles.values():
            if role_assignment.actor is not None and role_assignment.actor not in actors:
                raise RuntimeError(
                    f"Cast role {role_assignment.role!r} references unknown actor "
                    f"{role_assignment.actor!r} in {paths.display_path(path)}"
                )
        return CastConfig(actors=actors, roles=roles)

    def _load_yaml(self, path: Path) -> Any:
        yaml = YAML(typ="safe", pure=True)
        try:
            return yaml.load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Invalid YAML in {paths.display_path(path)}: {exc}") from exc

    def _parse_actors(self, raw_actors: Any, path: Path) -> dict[str, CastActor]:
        raw_actors = self._mapping(raw_actors, "actors", path)
        actors: dict[str, CastActor] = {}
        for actor_id, raw_actor in raw_actors.items():
            actor_id = self._id(actor_id, "actor id", path)
            raw_actor = self._mapping(raw_actor, f"actor {actor_id!r}", path)
            display_name = raw_actor.get("display_name", actor_id)
            actors[actor_id] = CastActor(
                actor_id=actor_id,
                display_name=self._text(display_name, f"display_name for actor {actor_id!r}", path),
                email=self._optional_text(raw_actor.get("email"), f"email for actor {actor_id!r}", path),
                notes=self._optional_text(raw_actor.get("notes"), f"notes for actor {actor_id!r}", path),
            )
        return actors

    def _parse_roles(self, raw_roles: Any, path: Path) -> dict[str, CastRoleAssignment]:
        raw_roles = self._mapping(raw_roles, "roles", path)
        roles: dict[str, CastRoleAssignment] = {}
        for role, raw_role in raw_roles.items():
            role = self._id(role, "role id", path)
            raw_role = self._mapping(raw_role, f"role {role!r}", path)
            recording = self._text(raw_role.get("recording", "linerecorder"), f"recording method for role {role!r}", path)
            if recording not in SUPPORTED_RECORDING_METHODS:
                raise RuntimeError(
                    f"Invalid recording method {recording!r} for role {role!r} in {paths.display_path(path)}"
                )
            roles[role] = CastRoleAssignment(
                role=role,
                actor=self._optional_id(raw_role.get("actor"), f"actor for role {role!r}", path),
                recording=recording,
                voice_profile=self._optional_id(raw_role.get("voice_profile"), f"voice_profile for role {role!r}", path),
                notes=self._optional_text(raw_role.get("notes"), f"notes for role {role!r}", path),
            )
        return roles

    def _mapping(self, value: Any, label: str, path: Path) -> dict:
        if not isinstance(value, dict):
            raise RuntimeError(f"Invalid {label} in {paths.display_path(path)}")
        return value

    def _id(self, value: Any, label: str, path: Path) -> str:
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Invalid {label} in {paths.display_path(path)}")
        return value.strip()

    def _optional_id(self, value: Any, label: str, path: Path) -> str | None:
        if value is None:
            return None
        return self._id(value, label, path)

    def _text(self, value: Any, label: str, path: Path) -> str:
        if not isinstance(value, str):
            raise RuntimeError(f"Invalid {label} in {paths.display_path(path)}")
        return value.strip()

    def _optional_text(self, value: Any, label: str, path: Path) -> str | None:
        if value is None:
            return None
        return self._text(value, label, path)
