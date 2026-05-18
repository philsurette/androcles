from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from stager.audio.cleaned_audio_selector import CleanedAudioSelector
from stager.audio.voice_profile_config import VoiceProfileConfig
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.shared import paths


@dataclass
class VoiceProfileAudioSelector:
    paths_config: paths.PathConfig
    base_selector: CleanedAudioSelector
    config: VoiceProfileConfig
    actor: str | None = None
    output_format: str = "wav"
    _rendered_paths: dict[tuple[str, str], Path] | None = field(default=None, init=False, repr=False)

    def segment_path(self, role: str, segment_id: str) -> Path:
        rendered_path = self.rendered_path(role, segment_id)
        if rendered_path is None:
            return self.base_selector.segment_path(role, segment_id)
        if not rendered_path.exists():
            raise RuntimeError(
                f"Voice-profile audio missing: {paths.display_path(rendered_path)}. "
                "Run `./main voice-render` first."
            )
        return rendered_path

    def rendered_path(self, role: str, segment_id: str) -> Path | None:
        if self._rendered_paths is None:
            self._rendered_paths = self._build_index()
        return self._rendered_paths.get((role, segment_id))

    def _build_index(self) -> dict[tuple[str, str], Path]:
        resolver = VoiceProfileResolver(self.config)
        cache = VoiceRenderCache(self.paths_config)
        index = {}
        roles = sorted({profile.role for profile in self.config.cast_profiles.values()})
        for role in roles:
            resolved = resolver.resolve(role, actor=self.actor)
            if resolved is None:
                continue
            render_profile_id = cache.render_profile_id(resolved)
            role_dir = self.paths_config.segments_dir / role
            if not role_dir.exists():
                continue
            for source_path in sorted(role_dir.glob("*.wav")):
                index[(role, source_path.stem)] = cache.output_path(
                    render_profile_id=render_profile_id,
                    role=role,
                    segment_id=source_path.stem,
                    output_format=self.output_format,
                )
        return index
