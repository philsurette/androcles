from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stager.shared import paths


CLEANUP_APPROACH_PROFILE_BASED = "profile-based"
CLEANUP_APPROACH_ANALYSIS_BASED = "analysis-based"
DEFAULT_PROFILE_NAME = "gentle_voice_cleanup"
DEFAULT_BATCH_PADDING_SECONDS = 3.0
DEFAULT_BOUNDARY_WARNING_MS = 500
SUPPORTED_LOUDNORM_PROFILES = {"librivox", "podcast", "none"}


@dataclass(frozen=True)
class CleanupProfile:
    name: str
    declick: str = "none"
    deesser: str = "none"
    denoise: str = "none"
    gate: str = "none"
    loudnorm: str = "librivox"


@dataclass(frozen=True)
class RoleCleanupOverride:
    role: str
    profile: str | None = None
    analysis: bool | None = None


@dataclass(frozen=True)
class CleanupResolution:
    role: str
    kind: str
    profile: CleanupProfile | None = None

    @property
    def disabled(self) -> bool:
        return self.kind == "none"

    @property
    def uses_analysis(self) -> bool:
        return self.kind == "analysis"


@dataclass(frozen=True)
class AudioCleanupConfig:
    version: int = 1
    cleanup_approach: str = CLEANUP_APPROACH_PROFILE_BASED
    default_profile: str = DEFAULT_PROFILE_NAME
    batch_padding_seconds: float = DEFAULT_BATCH_PADDING_SECONDS
    boundary_warning_ms: int = DEFAULT_BOUNDARY_WARNING_MS
    profiles: dict[str, CleanupProfile] = field(default_factory=dict)
    roles: dict[str, RoleCleanupOverride] = field(default_factory=dict)

    @classmethod
    def load(cls, paths_config: paths.PathConfig) -> "AudioCleanupConfig":
        path = paths_config.play_dir / "audio_cleanup.yaml"
        if not path.exists():
            return cls.default()
        return AudioCleanupConfigParser().parse(path)

    @classmethod
    def default(cls) -> "AudioCleanupConfig":
        return cls(profiles=built_in_profiles())

    def resolve_role(self, role: str) -> CleanupResolution:
        override = self.roles.get(role)
        if override is not None:
            if override.profile == "none":
                return CleanupResolution(role=role, kind="none")
            if override.profile is not None:
                return CleanupResolution(role=role, kind="profile", profile=self._profile(override.profile))
            if override.analysis is True:
                return CleanupResolution(role=role, kind="analysis")
            if override.analysis is False:
                return CleanupResolution(role=role, kind="profile", profile=self._profile(self.default_profile))
        if self.cleanup_approach == CLEANUP_APPROACH_ANALYSIS_BASED:
            return CleanupResolution(role=role, kind="analysis")
        return CleanupResolution(role=role, kind="profile", profile=self._profile(self.default_profile))

    def _profile(self, name: str) -> CleanupProfile:
        try:
            return self.profiles[name]
        except KeyError as exc:
            raise RuntimeError(f"Unknown audio cleanup profile {name!r}") from exc


class AudioCleanupConfigParser:
    def parse(self, path: Path) -> AudioCleanupConfig:
        raw = self._load_yaml(path)
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid audio cleanup config: {paths.display_path(path)}")
        version = raw.get("version", 1)
        if version != 1:
            raise RuntimeError(f"Unsupported audio cleanup config version {version!r} in {paths.display_path(path)}")
        cleanup_approach = raw.get("cleanup_approach", CLEANUP_APPROACH_PROFILE_BASED)
        if cleanup_approach not in {CLEANUP_APPROACH_PROFILE_BASED, CLEANUP_APPROACH_ANALYSIS_BASED}:
            raise RuntimeError(
                f"Invalid cleanup_approach {cleanup_approach!r} in {paths.display_path(path)}"
            )
        profiles = built_in_profiles()
        profiles.update(self._parse_profiles(raw.get("profiles", {}), path))
        default_profile = raw.get("default_profile", DEFAULT_PROFILE_NAME)
        if default_profile not in profiles:
            raise RuntimeError(
                f"Unknown default_profile {default_profile!r} in {paths.display_path(path)}"
            )
        batch_padding_seconds = self._positive_float(
            raw.get("batch_padding_seconds", DEFAULT_BATCH_PADDING_SECONDS),
            "batch_padding_seconds",
            path,
        )
        boundary_warning_ms = self._positive_int(
            raw.get("boundary_warning_ms", DEFAULT_BOUNDARY_WARNING_MS),
            "boundary_warning_ms",
            path,
        )
        roles = self._parse_roles(raw.get("roles", {}), profiles, path)
        return AudioCleanupConfig(
            version=1,
            cleanup_approach=cleanup_approach,
            default_profile=default_profile,
            batch_padding_seconds=batch_padding_seconds,
            boundary_warning_ms=boundary_warning_ms,
            profiles=profiles,
            roles=roles,
        )

    def _load_yaml(self, path: Path) -> Any:
        yml = YAML(typ="safe", pure=True)
        return yml.load(path.read_text(encoding="utf-8"))

    def _parse_profiles(self, raw_profiles: Any, path: Path) -> dict[str, CleanupProfile]:
        if raw_profiles is None:
            return {}
        if not isinstance(raw_profiles, dict):
            raise RuntimeError(f"Invalid profiles in {paths.display_path(path)}")
        profiles = {}
        for name, raw_profile in raw_profiles.items():
            if not isinstance(name, str) or not name:
                raise RuntimeError(f"Invalid cleanup profile name in {paths.display_path(path)}")
            if not isinstance(raw_profile, dict):
                raise RuntimeError(f"Invalid cleanup profile {name!r} in {paths.display_path(path)}")
            profiles[name] = CleanupProfile(
                name=name,
                declick=str(raw_profile.get("declick", "none")),
                deesser=str(raw_profile.get("deesser", "none")),
                denoise=str(raw_profile.get("denoise", "none")),
                gate=str(raw_profile.get("gate", "none")),
                loudnorm=self._loudnorm(raw_profile.get("loudnorm", "librivox"), name, path),
            )
        return profiles

    def _parse_roles(
        self,
        raw_roles: Any,
        profiles: dict[str, CleanupProfile],
        path: Path,
    ) -> dict[str, RoleCleanupOverride]:
        if raw_roles is None:
            return {}
        if not isinstance(raw_roles, dict):
            raise RuntimeError(f"Invalid roles in {paths.display_path(path)}")
        roles = {}
        for role, raw_override in raw_roles.items():
            if not isinstance(role, str) or not role:
                raise RuntimeError(f"Invalid role override name in {paths.display_path(path)}")
            if not isinstance(raw_override, dict):
                raise RuntimeError(f"Invalid cleanup override for role {role!r} in {paths.display_path(path)}")
            profile = raw_override.get("profile")
            analysis = raw_override.get("analysis")
            if profile is not None and analysis is not None:
                raise RuntimeError(
                    f"Role {role!r} cannot specify both profile and analysis in {paths.display_path(path)}"
                )
            if profile is not None:
                if not isinstance(profile, str):
                    raise RuntimeError(f"Invalid profile override for role {role!r} in {paths.display_path(path)}")
                if profile != "none" and profile not in profiles:
                    raise RuntimeError(
                        f"Unknown cleanup profile {profile!r} for role {role!r} in {paths.display_path(path)}"
                    )
            if analysis is not None and not isinstance(analysis, bool):
                raise RuntimeError(f"Invalid analysis override for role {role!r} in {paths.display_path(path)}")
            roles[role] = RoleCleanupOverride(role=role, profile=profile, analysis=analysis)
        return roles

    def _loudnorm(self, value: Any, profile_name: str, path: Path) -> str:
        value = str(value)
        if value not in SUPPORTED_LOUDNORM_PROFILES:
            raise RuntimeError(
                f"Invalid loudnorm profile {value!r} in cleanup profile {profile_name!r} "
                f"from {paths.display_path(path)}"
            )
        return value

    def _positive_float(self, value: Any, field_name: str, path: Path) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}") from exc
        if parsed <= 0:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return parsed

    def _positive_int(self, value: Any, field_name: str, path: Path) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}") from exc
        if parsed <= 0:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return parsed


def built_in_profiles() -> dict[str, CleanupProfile]:
    return {
        "none": CleanupProfile(name="none", loudnorm="none"),
        "declick_gentle": CleanupProfile(name="declick_gentle", declick="gentle", loudnorm="none"),
        "declick_medium": CleanupProfile(name="declick_medium", declick="medium", loudnorm="none"),
        "deesser_gentle": CleanupProfile(name="deesser_gentle", deesser="gentle", loudnorm="none"),
        "denoise_light": CleanupProfile(name="denoise_light", denoise="light", loudnorm="none"),
        DEFAULT_PROFILE_NAME: CleanupProfile(
            name=DEFAULT_PROFILE_NAME,
            declick="gentle",
            deesser="gentle",
            denoise="light",
            loudnorm="librivox",
        ),
    }
