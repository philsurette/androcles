from __future__ import annotations

from dataclasses import dataclass

from ruamel.yaml import YAML

from stager.domain.play import Play
from stager.production.cast_config import CastActor, CastConfig, CastRoleAssignment
from stager.shared import paths


@dataclass(frozen=True)
class CastValidationResult:
    unknown_roles: tuple[str, ...]
    unassigned_roles: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.unknown_roles


class CastConfigService:
    def __init__(self, *, paths_config: paths.PathConfig, play: Play) -> None:
        self.paths_config = paths_config
        self.play = play

    def load(self) -> CastConfig:
        return CastConfig.load(self.paths_config)

    def validate(self, config: CastConfig | None = None) -> CastValidationResult:
        config = config or self.load()
        valid_roles = self._valid_role_ids()
        unknown_roles = tuple(sorted(set(config.roles) - valid_roles))
        unassigned_roles = tuple(
            role
            for role in self._ordered_role_ids()
            if role not in config.roles or config.roles[role].actor is None
        )
        return CastValidationResult(unknown_roles=unknown_roles, unassigned_roles=unassigned_roles)

    def assign(self, *, role: str, actor: str, recording: str | None = None) -> CastConfig:
        valid_roles = self._valid_role_ids()
        if role not in valid_roles:
            raise RuntimeError(f"Unknown rehearsable role: {role}")
        config = self.load()
        actors = dict(config.actors)
        if actor not in actors:
            actors[actor] = CastActor(actor_id=actor, display_name=actor)
        roles = dict(config.roles)
        existing = roles.get(role)
        roles[role] = CastRoleAssignment(
            role=role,
            actor=actor,
            recording=recording or (existing.recording if existing is not None else "linerecorder"),
            voice_profile=existing.voice_profile if existing is not None else None,
            notes=existing.notes if existing is not None else None,
        )
        updated = CastConfig(actors=actors, roles=roles)
        self.save(updated)
        return updated

    def save(self, config: CastConfig) -> None:
        self.paths_config.play_dir.mkdir(parents=True, exist_ok=True)
        yaml = YAML()
        yaml.default_flow_style = False
        with (self.paths_config.play_dir / "cast.yaml").open("w", encoding="utf-8") as output:
            yaml.dump(config.to_dict(), output)

    def _ordered_role_ids(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.play.roles if not role.meta and not role.name.startswith("_"))

    def _valid_role_ids(self) -> set[str]:
        return set(self._ordered_role_ids())
