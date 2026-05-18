from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from stager.audio.voice_profile_config import VoiceProfileConfigParser
from stager.audio.voice_profile_renderer import VoiceProfileRenderer
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation, REQUIRED_VOICE_PROFILE_FILTERS


class CopyingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        input_path = Path(command[command.index("-i") + 1])
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_path, output_path)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")


class FailingRunner:
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="bad filter")


def test_voice_profile_renderer_renders_segment_and_writes_manifest(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)
    source = cache.source_identity(layer="canonical", path=source_path)
    runner = CopyingRunner()

    result = VoiceProfileRenderer(
        paths_config=cfg,
        installation=_installation(tmp_path),
        command_runner=runner,
    ).render_segment(
        resolved_profile=resolved,
        source=source,
        segment_id="0_1_1",
    )

    assert result.rendered is True
    assert result.cache_hit is False
    assert result.segment.output_path.exists()
    assert result.manifest_path.exists()
    assert runner.commands[0][0] == str(tmp_path / "ffmpeg")
    assert "-af" in runner.commands[0]
    assert "asetrate=48000*" in runner.commands[0][runner.commands[0].index("-af") + 1]


def test_voice_profile_renderer_skips_cache_hit(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)
    source = cache.source_identity(layer="canonical", path=source_path)
    runner = CopyingRunner()
    renderer = VoiceProfileRenderer(
        paths_config=cfg,
        installation=_installation(tmp_path),
        command_runner=runner,
    )

    first = renderer.render_segment(resolved_profile=resolved, source=source, segment_id="0_1_1")
    second = renderer.render_segment(resolved_profile=resolved, source=source, segment_id="0_1_1")

    assert first.rendered is True
    assert second.rendered is False
    assert second.cache_hit is True
    assert len(runner.commands) == 1


def test_voice_profile_renderer_force_ignores_cache_hit(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    source = VoiceRenderCache(cfg).source_identity(layer="canonical", path=source_path)
    runner = CopyingRunner()
    renderer = VoiceProfileRenderer(
        paths_config=cfg,
        installation=_installation(tmp_path),
        command_runner=runner,
    )

    renderer.render_segment(resolved_profile=resolved, source=source, segment_id="0_1_1")
    renderer.render_segment(resolved_profile=resolved, source=source, segment_id="0_1_1", force=True)

    assert len(runner.commands) == 2


def test_voice_profile_renderer_pads_effect_tails(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "GOD" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path, role="GOD", transform="""
      - type: reverb
        delay_ms: 80
        decay: 0.4
""")
    source = VoiceRenderCache(cfg).source_identity(layer="canonical", path=source_path)
    runner = CopyingRunner()

    VoiceProfileRenderer(
        paths_config=cfg,
        installation=_installation(tmp_path),
        command_runner=runner,
    ).render_segment(
        resolved_profile=resolved,
        source=source,
        segment_id="0_1_1",
    )

    filter_spec = runner.commands[0][runner.commands[0].index("-af") + 1]
    assert "aecho=0.8:0.9:80.0:0.4" in filter_spec
    assert "apad=pad_dur=2.0" in filter_spec


def test_voice_profile_renderer_fails_for_missing_required_filters(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    source = VoiceRenderCache(cfg).source_identity(layer="canonical", path=source_path)
    installation = _installation(tmp_path, filters=set(REQUIRED_VOICE_PROFILE_FILTERS) - {"loudnorm"})

    with pytest.raises(RuntimeError, match="Missing required FFmpeg voice-profile filter"):
        VoiceProfileRenderer(
            paths_config=cfg,
            installation=installation,
            command_runner=CopyingRunner(),
        ).render_segment(
            resolved_profile=resolved,
            source=source,
            segment_id="0_1_1",
        )


def test_voice_profile_renderer_reports_ffmpeg_failure(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    source = VoiceRenderCache(cfg).source_identity(layer="canonical", path=source_path)

    with pytest.raises(RuntimeError, match="bad filter"):
        VoiceProfileRenderer(
            paths_config=cfg,
            installation=_installation(tmp_path),
            command_runner=FailingRunner(),
        ).render_segment(
            resolved_profile=resolved,
            source=source,
            segment_id="0_1_1",
        )


def _installation(tmp_path: Path, *, filters: set[str] | None = None) -> FfmpegInstallation:
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    return FfmpegInstallation(
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        source="test",
        config_path=None,
        filters=frozenset(filters or set(REQUIRED_VOICE_PROFILE_FILTERS)),
    )


def _resolved(tmp_path: Path, *, role: str = "MEGAERA", transform: str | None = None):
    transform = transform or """
      - type: pitch
        semitones: 1.5
        strategy: preserve_tempo
"""
    path = tmp_path / f"voice_profiles_{role}.yaml"
    path.write_text(
        f"""
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  {role}:
    target:
      pitch_center_hz: 205
cast_profiles:
  phil@{role}:
    actor: phil
    role: {role}
    mode: explicit
    transforms:
{transform}
""",
        encoding="utf-8",
    )
    config = VoiceProfileConfigParser().parse(path)
    resolved = VoiceProfileResolver(config).resolve(role)
    assert resolved is not None
    return resolved


def _cfg(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    return cfg
