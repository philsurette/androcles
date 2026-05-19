from __future__ import annotations

from dataclasses import dataclass

from stager.production.cast_config import CastConfig
from stager.shared import paths


@dataclass(frozen=True)
class VoiceProfileCastResolver:
    paths_config: paths.PathConfig

    def actor_for_role(self, role: str, explicit_actor: str | None = None) -> str | None:
        if explicit_actor is not None:
            return explicit_actor
        assignment = CastConfig.load(self.paths_config).assignment_for_role(role)
        if assignment is None:
            return None
        return assignment.actor
