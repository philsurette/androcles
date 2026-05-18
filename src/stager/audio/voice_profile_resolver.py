from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import asdict, dataclass

from stager.audio.voice_profile_config import (
    PITCH_STRATEGY_AUTO,
    PITCH_STRATEGY_LINKED_SPEED,
    PITCH_STRATEGY_PRESERVE_TEMPO,
    CastVoiceProfile,
    ObservedVoiceMetrics,
    RoleVoiceTarget,
    VoiceProfileConfig,
    VoiceTransform,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedVoiceProfile:
    profile_id: str
    stable_id: str
    actor: str
    role: str
    mode: str
    transforms: tuple[VoiceTransform, ...]
    selected_pitch_strategy: str | None = None
    observed_metrics: ObservedVoiceMetrics | None = None
    warnings: tuple[str, ...] = ()


class VoiceProfileResolver:
    def __init__(self, config: VoiceProfileConfig) -> None:
        self.config = config

    def resolve(self, role: str, actor: str | None = None) -> ResolvedVoiceProfile | None:
        active_actor = self._resolve_actor(role=role, explicit_actor=actor)
        if active_actor is None:
            return None
        profile = self._profile_for(role=role, actor=active_actor)
        if profile.mode == "none":
            return self._resolved(profile=profile, transforms=(), selected_pitch_strategy=None, warnings=())
        if profile.mode == "explicit":
            transforms, selected_pitch_strategy, warnings = self._resolve_explicit(profile)
            return self._resolved(
                profile=profile,
                transforms=transforms,
                selected_pitch_strategy=selected_pitch_strategy,
                warnings=warnings,
            )
        transforms, selected_pitch_strategy, warnings = self._resolve_computed(profile)
        return self._resolved(
            profile=profile,
            transforms=transforms,
            selected_pitch_strategy=selected_pitch_strategy,
            warnings=warnings,
        )

    def _resolve_actor(self, role: str, explicit_actor: str | None) -> str | None:
        if explicit_actor is not None:
            if explicit_actor not in self.config.actors:
                raise RuntimeError(f"Unknown actor {explicit_actor!r}")
            if self._profile_for(role=role, actor=explicit_actor, required=False) is None:
                raise RuntimeError(f"No cast profile for actor {explicit_actor!r} and role {role!r}")
            return explicit_actor

        mapped_actor = self.config.role_actors.get(role)
        if mapped_actor is not None:
            return mapped_actor

        profiles = self.config.cast_profiles_for_role(role)
        if not profiles:
            return None
        if len(profiles) > 1:
            profile_ids = ", ".join(sorted(profile.profile_id for profile in profiles))
            raise RuntimeError(f"Ambiguous actor for role {role!r}; matching cast profiles: {profile_ids}")
        return profiles[0].actor

    def _profile_for(self, role: str, actor: str, required: bool = True) -> CastVoiceProfile | None:
        for profile in self.config.cast_profiles.values():
            if profile.role == role and profile.actor == actor:
                return profile
        if required:
            raise RuntimeError(f"No cast profile for actor {actor!r} and role {role!r}")
        return None

    def _resolve_explicit(self, profile: CastVoiceProfile) -> tuple[tuple[VoiceTransform, ...], str | None, tuple[str, ...]]:
        transforms = self._expand_presets(profile.transforms)
        selected_pitch_strategy = None
        warnings: list[str] = []
        resolved = []
        for transform in transforms:
            if transform.type != "pitch":
                resolved.append(transform)
                continue
            strategy = str(transform.params.get("strategy", PITCH_STRATEGY_AUTO))
            if strategy == PITCH_STRATEGY_AUTO:
                strategy = PITCH_STRATEGY_PRESERVE_TEMPO
            selected_pitch_strategy = strategy
            if strategy == PITCH_STRATEGY_PRESERVE_TEMPO:
                warnings.append(
                    f"Independent pitch selected for {profile.actor}@{profile.role}; listen for artifacts."
                )
            resolved.append(self._with_param(transform, "strategy", strategy))
        return tuple(resolved), selected_pitch_strategy, tuple(warnings)

    def _resolve_computed(self, profile: CastVoiceProfile) -> tuple[tuple[VoiceTransform, ...], str, tuple[str, ...]]:
        actor = self.config.actors[profile.actor]
        target = self.config.role_targets[profile.role]
        if actor.pitch_center_hz is None or target.pitch_center_hz is None:
            raise RuntimeError(f"Computed cast profile {profile.profile_id!r} requires actor and role pitch_center_hz")

        semitones = 12 * math.log2(target.pitch_center_hz / actor.pitch_center_hz)
        semitones = self._clamp_pitch(semitones, target)
        semitones = float(profile.overrides.get("pitch_shift_semitones", semitones))
        selected_pitch_strategy, warnings = self._select_pitch_strategy(profile, target, semitones)

        transforms: list[VoiceTransform] = []
        if target.preset is not None:
            transforms.append(VoiceTransform(type="preset", params={"name": target.preset}))
        transforms.append(
            VoiceTransform(
                type="pitch",
                params={
                    "semitones": semitones,
                    "strategy": selected_pitch_strategy,
                },
            )
        )
        transforms.extend(profile.transforms)
        expanded = self._expand_presets(tuple(transforms))
        return expanded, selected_pitch_strategy, tuple(warnings)

    def _select_pitch_strategy(
        self,
        profile: CastVoiceProfile,
        target: RoleVoiceTarget,
        semitones: float,
    ) -> tuple[str, list[str]]:
        policy = target.tempo_policy
        pitch_policy = target.pitch_strategy
        if not pitch_policy.prefer_linked_speed_pitch_when_safe:
            return pitch_policy.fallback, self._preserve_tempo_warnings(profile, pitch_policy.fallback)

        metrics = self.config.observed_metrics_for(profile.actor, profile.role)
        if metrics is None or metrics.speaking_rate_wpm is None:
            return PITCH_STRATEGY_PRESERVE_TEMPO, [
                f"Preserving tempo for {profile.actor}@{profile.role}; no observed tempo is available."
            ]
        if metrics.confidence < policy.min_confidence:
            return PITCH_STRATEGY_PRESERVE_TEMPO, [
                f"Preserving tempo for {profile.actor}@{profile.role}; observed tempo confidence is too low."
            ]

        speed_factor = 2 ** (semitones / 12)
        if policy.max_linked_speed_change is not None:
            speed_delta = abs(speed_factor - 1.0)
            if speed_delta > policy.max_linked_speed_change:
                return PITCH_STRATEGY_PRESERVE_TEMPO, [
                    f"Preserving tempo for {profile.actor}@{profile.role}; linked speed change is outside policy."
                ]

        predicted_wpm = metrics.speaking_rate_wpm * speed_factor
        if policy.acceptable_range_wpm is not None:
            low, high = policy.acceptable_range_wpm
            if predicted_wpm < low or predicted_wpm > high:
                return PITCH_STRATEGY_PRESERVE_TEMPO, [
                    f"Preserving tempo for {profile.actor}@{profile.role}; linked pitch would move tempo outside policy."
                ]

        return PITCH_STRATEGY_LINKED_SPEED, []

    def _preserve_tempo_warnings(self, profile: CastVoiceProfile, strategy: str) -> list[str]:
        if strategy == PITCH_STRATEGY_PRESERVE_TEMPO:
            return [f"Independent pitch selected for {profile.actor}@{profile.role}; listen for artifacts."]
        return []

    def _clamp_pitch(self, semitones: float, target: RoleVoiceTarget) -> float:
        if target.max_pitch_shift_semitones is None:
            return semitones
        limit = target.max_pitch_shift_semitones
        return max(-limit, min(limit, semitones))

    def _expand_presets(self, transforms: tuple[VoiceTransform, ...]) -> tuple[VoiceTransform, ...]:
        expanded = []
        for transform in transforms:
            if transform.type != "preset":
                expanded.append(transform)
                continue
            name = str(transform.params["name"])
            preset = self.config.presets.get(name)
            if preset is None:
                raise RuntimeError(f"Unknown voice preset {name!r}")
            expanded.extend(self._expand_presets(preset.transforms))
        return tuple(expanded)

    def _resolved(
        self,
        profile: CastVoiceProfile,
        transforms: tuple[VoiceTransform, ...],
        selected_pitch_strategy: str | None,
        warnings: tuple[str, ...],
    ) -> ResolvedVoiceProfile:
        for warning in warnings:
            logger.warning(warning)
        observed_metrics = self.config.observed_metrics_for(profile.actor, profile.role)
        stable_id = self._stable_id(profile, transforms, selected_pitch_strategy, observed_metrics)
        return ResolvedVoiceProfile(
            profile_id=profile.profile_id,
            stable_id=stable_id,
            actor=profile.actor,
            role=profile.role,
            mode=profile.mode,
            transforms=transforms,
            selected_pitch_strategy=selected_pitch_strategy,
            observed_metrics=observed_metrics,
            warnings=warnings,
        )

    def _stable_id(
        self,
        profile: CastVoiceProfile,
        transforms: tuple[VoiceTransform, ...],
        selected_pitch_strategy: str | None,
        observed_metrics: ObservedVoiceMetrics | None,
    ) -> str:
        payload = {
            "profile_id": profile.profile_id,
            "actor": profile.actor,
            "role": profile.role,
            "mode": profile.mode,
            "transforms": [asdict(transform) for transform in transforms],
            "selected_pitch_strategy": selected_pitch_strategy,
            "observed_metrics": asdict(observed_metrics) if observed_metrics is not None else None,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return digest[:16]

    def _with_param(self, transform: VoiceTransform, key: str, value: object) -> VoiceTransform:
        params = dict(transform.params)
        params[key] = value
        return VoiceTransform(type=transform.type, params=params)
