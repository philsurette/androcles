from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from stager.shared import paths


VOICE_PROFILE_VERSION = 1
PITCH_STRATEGY_AUTO = "auto"
PITCH_STRATEGY_LINKED_SPEED = "linked_speed"
PITCH_STRATEGY_PRESERVE_TEMPO = "preserve_tempo"
SUPPORTED_PITCH_STRATEGIES = {
    PITCH_STRATEGY_AUTO,
    PITCH_STRATEGY_LINKED_SPEED,
    PITCH_STRATEGY_PRESERVE_TEMPO,
}
SUPPORTED_PITCH_FALLBACKS = {
    PITCH_STRATEGY_LINKED_SPEED,
    PITCH_STRATEGY_PRESERVE_TEMPO,
}
SUPPORTED_CAST_MODES = {"none", "explicit", "computed"}
SUPPORTED_TRANSFORM_TYPES = {
    "pitch",
    "speed",
    "highpass",
    "lowpass",
    "eq",
    "filter_curve",
    "compressor",
    "reverb",
    "delay",
    "gain",
    "loudnorm",
    "preset",
}


@dataclass(frozen=True)
class ActorVoiceBaseline:
    actor_id: str
    display_name: str | None = None
    pitch_center_hz: float | None = None
    speaking_rate_wpm: float | None = None
    brightness: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RoleTempoPolicy:
    mode: str = "preserve_performance"
    acceptable_range_wpm: tuple[float, float] | None = None
    max_linked_speed_change: float | None = None
    min_confidence: float = 0.0


@dataclass(frozen=True)
class PitchStrategyPolicy:
    prefer_linked_speed_pitch_when_safe: bool = False
    fallback: str = PITCH_STRATEGY_PRESERVE_TEMPO


@dataclass(frozen=True)
class RoleVoiceTarget:
    role: str
    description: str | None = None
    pitch_center_hz: float | None = None
    speaking_rate_wpm: float | None = None
    tone: str | None = None
    preset: str | None = None
    max_pitch_shift_semitones: float | None = None
    tempo_policy: RoleTempoPolicy = field(default_factory=RoleTempoPolicy)
    pitch_strategy: PitchStrategyPolicy = field(default_factory=PitchStrategyPolicy)
    notes: str | None = None


@dataclass(frozen=True)
class ObservedVoiceMetrics:
    actor: str
    role: str
    speaking_rate_wpm: float | None = None
    confidence: float = 0.0
    source: str | None = None
    speech_active_seconds: float | None = None
    word_count: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class VoiceTransform:
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoicePreset:
    name: str
    transforms: tuple[VoiceTransform, ...] = ()


@dataclass(frozen=True)
class CastVoiceProfile:
    profile_id: str
    actor: str
    role: str
    mode: str
    transforms: tuple[VoiceTransform, ...] = ()
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoiceProfileConfig:
    version: int = VOICE_PROFILE_VERSION
    actors: dict[str, ActorVoiceBaseline] = field(default_factory=dict)
    role_targets: dict[str, RoleVoiceTarget] = field(default_factory=dict)
    observed_metrics: dict[str, ObservedVoiceMetrics] = field(default_factory=dict)
    cast_profiles: dict[str, CastVoiceProfile] = field(default_factory=dict)
    presets: dict[str, VoicePreset] = field(default_factory=dict)
    role_actors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, paths_config: paths.PathConfig) -> "VoiceProfileConfig":
        path = paths_config.play_dir / "voice_profiles.yaml"
        if not path.exists():
            return cls()
        return VoiceProfileConfigParser().parse(path)

    def cast_profiles_for_role(self, role: str) -> list[CastVoiceProfile]:
        return [profile for profile in self.cast_profiles.values() if profile.role == role]

    def observed_metrics_for(self, actor: str, role: str) -> ObservedVoiceMetrics | None:
        return self.observed_metrics.get(actor_role_key(actor, role))


class VoiceProfileConfigParser:
    def parse(self, path: Path) -> VoiceProfileConfig:
        raw = self._load_yaml(path)
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid voice profile config: {paths.display_path(path)}")
        version = raw.get("version", VOICE_PROFILE_VERSION)
        if version != VOICE_PROFILE_VERSION:
            raise RuntimeError(f"Unsupported voice profile config version {version!r} in {paths.display_path(path)}")

        actors = self._parse_actors(raw.get("actors", {}), path)
        role_targets = self._parse_role_targets(raw.get("role_targets", {}), path)
        presets = self._parse_presets(raw.get("presets", {}), path)
        observed_metrics = self._parse_observed_metrics(raw.get("observed_metrics", {}), actors, role_targets, path)
        cast_profiles = self._parse_cast_profiles(raw.get("cast_profiles", {}), actors, role_targets, path)
        role_actors = self._parse_role_actors(raw.get("role_actors", {}), actors, role_targets, path)
        return VoiceProfileConfig(
            version=VOICE_PROFILE_VERSION,
            actors=actors,
            role_targets=role_targets,
            observed_metrics=observed_metrics,
            cast_profiles=cast_profiles,
            presets=presets,
            role_actors=role_actors,
        )

    def _load_yaml(self, path: Path) -> Any:
        yml = YAML(typ="safe", pure=True)
        return yml.load(path.read_text(encoding="utf-8"))

    def _parse_actors(self, raw_actors: Any, path: Path) -> dict[str, ActorVoiceBaseline]:
        if raw_actors is None:
            return {}
        if not isinstance(raw_actors, dict):
            raise RuntimeError(f"Invalid actors in {paths.display_path(path)}")
        actors = {}
        for actor_id, raw_actor in raw_actors.items():
            actor_id = self._id(actor_id, "actor id", path)
            raw_actor = self._mapping(raw_actor, f"actor {actor_id!r}", path)
            baseline = self._mapping(raw_actor.get("baseline", {}), f"baseline for actor {actor_id!r}", path)
            actors[actor_id] = ActorVoiceBaseline(
                actor_id=actor_id,
                display_name=self._optional_str(raw_actor.get("display_name"), "display_name", path),
                pitch_center_hz=self._optional_positive_float(baseline.get("pitch_center_hz"), "pitch_center_hz", path),
                speaking_rate_wpm=self._optional_positive_float(
                    baseline.get("speaking_rate_wpm"),
                    "speaking_rate_wpm",
                    path,
                ),
                brightness=self._optional_str(baseline.get("brightness"), "brightness", path),
                notes=self._optional_str(baseline.get("notes"), "notes", path),
            )
        return actors

    def _parse_role_targets(self, raw_targets: Any, path: Path) -> dict[str, RoleVoiceTarget]:
        if raw_targets is None:
            return {}
        if not isinstance(raw_targets, dict):
            raise RuntimeError(f"Invalid role_targets in {paths.display_path(path)}")
        targets = {}
        for role, raw_role_target in raw_targets.items():
            role = self._id(role, "role id", path)
            raw_role_target = self._mapping(raw_role_target, f"role target {role!r}", path)
            raw_target = self._mapping(raw_role_target.get("target", raw_role_target), f"target for role {role!r}", path)
            targets[role] = RoleVoiceTarget(
                role=role,
                description=self._optional_str(raw_role_target.get("description"), "description", path),
                pitch_center_hz=self._optional_positive_float(raw_target.get("pitch_center_hz"), "pitch_center_hz", path),
                speaking_rate_wpm=self._optional_positive_float(
                    raw_target.get("speaking_rate_wpm"),
                    "speaking_rate_wpm",
                    path,
                ),
                tone=self._optional_str(raw_target.get("tone"), "tone", path),
                preset=self._optional_str(raw_target.get("preset"), "preset", path),
                max_pitch_shift_semitones=self._optional_positive_float(
                    raw_target.get("max_pitch_shift_semitones"),
                    "max_pitch_shift_semitones",
                    path,
                ),
                tempo_policy=self._parse_tempo_policy(raw_target.get("tempo_policy", {}), role, path),
                pitch_strategy=self._parse_pitch_strategy(raw_target.get("pitch_strategy", {}), role, path),
                notes=self._optional_str(raw_target.get("notes"), "notes", path),
            )
        return targets

    def _parse_tempo_policy(self, raw_policy: Any, role: str, path: Path) -> RoleTempoPolicy:
        raw_policy = self._mapping(raw_policy, f"tempo_policy for role {role!r}", path)
        mode = str(raw_policy.get("mode", "preserve_performance"))
        if mode != "preserve_performance":
            raise RuntimeError(f"Invalid tempo_policy mode {mode!r} for role {role!r} in {paths.display_path(path)}")
        acceptable_range_wpm = self._optional_range(raw_policy.get("acceptable_range_wpm"), "acceptable_range_wpm", path)
        max_linked_speed_change = self._optional_positive_float(
            raw_policy.get("max_linked_speed_change"),
            "max_linked_speed_change",
            path,
        )
        min_confidence = self._confidence(raw_policy.get("min_confidence", 0.0), "min_confidence", path)
        return RoleTempoPolicy(
            mode=mode,
            acceptable_range_wpm=acceptable_range_wpm,
            max_linked_speed_change=max_linked_speed_change,
            min_confidence=min_confidence,
        )

    def _parse_pitch_strategy(self, raw_policy: Any, role: str, path: Path) -> PitchStrategyPolicy:
        raw_policy = self._mapping(raw_policy, f"pitch_strategy for role {role!r}", path)
        prefer_linked = raw_policy.get("prefer_linked_speed_pitch_when_safe", False)
        if not isinstance(prefer_linked, bool):
            raise RuntimeError(
                f"Invalid prefer_linked_speed_pitch_when_safe for role {role!r} in {paths.display_path(path)}"
            )
        fallback = str(raw_policy.get("fallback", PITCH_STRATEGY_PRESERVE_TEMPO))
        if fallback not in SUPPORTED_PITCH_FALLBACKS:
            raise RuntimeError(f"Invalid pitch_strategy fallback {fallback!r} for role {role!r} in {paths.display_path(path)}")
        return PitchStrategyPolicy(
            prefer_linked_speed_pitch_when_safe=prefer_linked,
            fallback=fallback,
        )

    def _parse_observed_metrics(
        self,
        raw_metrics: Any,
        actors: dict[str, ActorVoiceBaseline],
        role_targets: dict[str, RoleVoiceTarget],
        path: Path,
    ) -> dict[str, ObservedVoiceMetrics]:
        if raw_metrics is None:
            return {}
        if not isinstance(raw_metrics, dict):
            raise RuntimeError(f"Invalid observed_metrics in {paths.display_path(path)}")
        metrics = {}
        for raw_key, raw_metric in raw_metrics.items():
            actor, role = self._actor_role_key(raw_key, path)
            self._require_known_actor(actor, actors, path)
            self._require_known_role(role, role_targets, path)
            raw_metric = self._mapping(raw_metric, f"observed metrics {raw_key!r}", path)
            metrics[actor_role_key(actor, role)] = ObservedVoiceMetrics(
                actor=actor,
                role=role,
                speaking_rate_wpm=self._optional_positive_float(
                    raw_metric.get("speaking_rate_wpm"),
                    "speaking_rate_wpm",
                    path,
                ),
                confidence=self._confidence(raw_metric.get("confidence", 0.0), "confidence", path),
                source=self._optional_str(raw_metric.get("source"), "source", path),
                speech_active_seconds=self._optional_positive_float(
                    raw_metric.get("speech_active_seconds"),
                    "speech_active_seconds",
                    path,
                ),
                word_count=self._optional_positive_int(raw_metric.get("word_count"), "word_count", path),
                notes=self._optional_str(raw_metric.get("notes"), "notes", path),
            )
        return metrics

    def _parse_cast_profiles(
        self,
        raw_profiles: Any,
        actors: dict[str, ActorVoiceBaseline],
        role_targets: dict[str, RoleVoiceTarget],
        path: Path,
    ) -> dict[str, CastVoiceProfile]:
        if raw_profiles is None:
            return {}
        if not isinstance(raw_profiles, dict):
            raise RuntimeError(f"Invalid cast_profiles in {paths.display_path(path)}")
        profiles = {}
        seen_bindings = set()
        for profile_id, raw_profile in raw_profiles.items():
            profile_id = self._id(profile_id, "cast profile id", path)
            raw_profile = self._mapping(raw_profile, f"cast profile {profile_id!r}", path)
            actor = self._id(raw_profile.get("actor"), f"actor for cast profile {profile_id!r}", path)
            role = self._id(raw_profile.get("role"), f"role for cast profile {profile_id!r}", path)
            self._require_known_actor(actor, actors, path)
            self._require_known_role(role, role_targets, path)
            binding = actor_role_key(actor, role)
            if binding in seen_bindings:
                raise RuntimeError(f"Duplicate cast profile binding {binding!r} in {paths.display_path(path)}")
            seen_bindings.add(binding)
            mode = str(raw_profile.get("mode", "computed"))
            if mode not in SUPPORTED_CAST_MODES:
                raise RuntimeError(f"Invalid cast profile mode {mode!r} in {paths.display_path(path)}")
            transforms = self._parse_transforms(raw_profile.get("transforms", []), path)
            overrides = self._mapping(raw_profile.get("overrides", {}), f"overrides for cast profile {profile_id!r}", path)
            if mode == "computed":
                actor_baseline = actors[actor]
                role_target = role_targets[role]
                if actor_baseline.pitch_center_hz is None or role_target.pitch_center_hz is None:
                    raise RuntimeError(
                        f"Computed cast profile {profile_id!r} requires actor and role pitch_center_hz "
                        f"in {paths.display_path(path)}"
                    )
            profiles[profile_id] = CastVoiceProfile(
                profile_id=profile_id,
                actor=actor,
                role=role,
                mode=mode,
                transforms=transforms,
                overrides=dict(overrides),
            )
        return profiles

    def _parse_presets(self, raw_presets: Any, path: Path) -> dict[str, VoicePreset]:
        if raw_presets is None:
            return {}
        if not isinstance(raw_presets, dict):
            raise RuntimeError(f"Invalid presets in {paths.display_path(path)}")
        presets = {}
        for name, raw_preset in raw_presets.items():
            name = self._id(name, "preset name", path)
            raw_preset = self._mapping(raw_preset, f"preset {name!r}", path)
            presets[name] = VoicePreset(
                name=name,
                transforms=self._parse_transforms(raw_preset.get("transforms", []), path),
            )
        return presets

    def _parse_role_actors(
        self,
        raw_role_actors: Any,
        actors: dict[str, ActorVoiceBaseline],
        role_targets: dict[str, RoleVoiceTarget],
        path: Path,
    ) -> dict[str, str]:
        if raw_role_actors is None:
            return {}
        if not isinstance(raw_role_actors, dict):
            raise RuntimeError(f"Invalid role_actors in {paths.display_path(path)}")
        role_actors = {}
        for role, actor in raw_role_actors.items():
            role = self._id(role, "role_actors role", path)
            actor = self._id(actor, f"actor for role {role!r}", path)
            self._require_known_actor(actor, actors, path)
            self._require_known_role(role, role_targets, path)
            role_actors[role] = actor
        return role_actors

    def _parse_transforms(self, raw_transforms: Any, path: Path) -> tuple[VoiceTransform, ...]:
        if raw_transforms is None:
            return ()
        if not isinstance(raw_transforms, list):
            raise RuntimeError(f"Invalid transforms in {paths.display_path(path)}")
        transforms = []
        for raw_transform in raw_transforms:
            raw_transform = self._mapping(raw_transform, "transform", path)
            transform_type = str(raw_transform.get("type", ""))
            if transform_type not in SUPPORTED_TRANSFORM_TYPES:
                raise RuntimeError(f"Unsupported voice transform type {transform_type!r} in {paths.display_path(path)}")
            if "preserve_tempo" in raw_transform:
                raise RuntimeError(
                    f"Pitch transforms must use strategy, not preserve_tempo, in {paths.display_path(path)}"
                )
            params = {key: value for key, value in raw_transform.items() if key != "type"}
            self._validate_transform(transform_type, params, path)
            transforms.append(VoiceTransform(type=transform_type, params=params))
        return tuple(transforms)

    def _validate_transform(self, transform_type: str, params: dict[str, Any], path: Path) -> None:
        if transform_type == "pitch":
            if "semitones" not in params:
                raise RuntimeError(f"Pitch transform missing semitones in {paths.display_path(path)}")
            self._float(params["semitones"], "semitones", path)
            strategy = str(params.get("strategy", PITCH_STRATEGY_AUTO))
            if strategy not in SUPPORTED_PITCH_STRATEGIES:
                raise RuntimeError(f"Invalid pitch strategy {strategy!r} in {paths.display_path(path)}")
        if transform_type == "speed":
            self._positive_float(params.get("speed_factor"), "speed_factor", path)
        if transform_type in {"highpass", "lowpass"}:
            self._positive_float(params.get("frequency_hz"), "frequency_hz", path)
        if transform_type == "preset":
            self._id(params.get("name"), "preset transform name", path)

    def _actor_role_key(self, value: Any, path: Path) -> tuple[str, str]:
        value = self._id(value, "actor-role key", path)
        parts = value.split("@", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise RuntimeError(f"Invalid actor-role key {value!r} in {paths.display_path(path)}")
        return parts[0], parts[1]

    def _require_known_actor(self, actor: str, actors: dict[str, ActorVoiceBaseline], path: Path) -> None:
        if actor not in actors:
            raise RuntimeError(f"Unknown actor {actor!r} in {paths.display_path(path)}")

    def _require_known_role(self, role: str, role_targets: dict[str, RoleVoiceTarget], path: Path) -> None:
        if role not in role_targets:
            raise RuntimeError(f"Unknown role {role!r} in {paths.display_path(path)}")

    def _mapping(self, value: Any, name: str, path: Path) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise RuntimeError(f"Invalid {name} in {paths.display_path(path)}")
        return value

    def _id(self, value: Any, name: str, path: Path) -> str:
        if not isinstance(value, str) or not value:
            raise RuntimeError(f"Invalid {name} in {paths.display_path(path)}")
        return value

    def _optional_str(self, value: Any, field_name: str, path: Path) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return value

    def _optional_positive_float(self, value: Any, field_name: str, path: Path) -> float | None:
        if value is None:
            return None
        return self._positive_float(value, field_name, path)

    def _optional_positive_int(self, value: Any, field_name: str, path: Path) -> int | None:
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}") from exc
        if parsed <= 0:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return parsed

    def _optional_range(self, value: Any, field_name: str, path: Path) -> tuple[float, float] | None:
        if value is None:
            return None
        if not isinstance(value, list) or len(value) != 2:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        low = self._positive_float(value[0], field_name, path)
        high = self._positive_float(value[1], field_name, path)
        if low >= high:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return low, high

    def _confidence(self, value: Any, field_name: str, path: Path) -> float:
        parsed = self._float(value, field_name, path)
        if parsed < 0.0 or parsed > 1.0:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return parsed

    def _positive_float(self, value: Any, field_name: str, path: Path) -> float:
        parsed = self._float(value, field_name, path)
        if parsed <= 0:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}")
        return parsed

    def _float(self, value: Any, field_name: str, path: Path) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(path)}") from exc


def actor_role_key(actor: str, role: str) -> str:
    return f"{actor}@{role}"
