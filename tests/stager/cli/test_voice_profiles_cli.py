from __future__ import annotations

import math
from pathlib import Path
import shutil
import subprocess
import wave

from typer.testing import CliRunner

from stager.cli import build
from stager.domain.block import RoleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation, REQUIRED_VOICE_PROFILE_FILTERS


class FakeVoiceToolChecker:
    def __init__(self, filters: set[str] | None = None) -> None:
        self.filters = filters or set(REQUIRED_VOICE_PROFILE_FILTERS)
        self.calls = 0

    def require_audio_tools(self) -> FfmpegInstallation:
        self.calls += 1
        return FfmpegInstallation(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            ffprobe_path=Path("/usr/bin/ffprobe"),
            source="PATH",
            config_path=None,
            filters=frozenset(self.filters),
        )


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


def test_voice_profiles_doctor_reports_capabilities(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeVoiceToolChecker())

    result = CliRunner().invoke(build.app, ["voice-profiles", "doctor", "--play", "test"])

    assert result.exit_code == 0
    assert "required voice-profile filters: found" in result.output
    assert "optional voice-profile filters missing: concat, firequalizer, afir" in result.output


def test_voice_render_dry_run_reports_planned_segments(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_voice_profiles(cfg)
    _write_segment(cfg, "MEGAERA", "0_1_1")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeVoiceToolChecker())

    result = CliRunner().invoke(build.app, ["voice-render", "--play", "test", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run voice render: 1 segments, 0 cache hits." in result.output
    assert "phil@MEGAERA 0_1_1: render needed from canonical" in result.output
    assert "build/test/audio/rendered/phil@MEGAERA-" in result.output


def test_voice_render_dry_run_handles_missing_config(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_segment(cfg, "MEGAERA", "0_1_1")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeVoiceToolChecker())

    result = CliRunner().invoke(build.app, ["voice-render", "--play", "test", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run voice render: 0 segments, 0 cache hits." in result.output


def test_voice_render_dry_run_fails_for_ambiguous_actor(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_voice_profiles(cfg, include_alex=True)
    _write_segment(cfg, "MEGAERA", "0_1_1")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeVoiceToolChecker())

    result = CliRunner().invoke(build.app, ["voice-render", "--play", "test", "--dry-run"])

    assert result.exit_code != 0
    assert "Ambiguous actor for role 'MEGAERA'" in result.output


def test_run_voice_render_renders_and_then_skips_cache_hit(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_voice_profiles(cfg)
    _write_segment(cfg, "MEGAERA", "0_1_1")
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeVoiceToolChecker())
    runner = CopyingRunner()
    installation = FakeVoiceToolChecker().require_audio_tools()

    first = build.run_voice_render(
        paths_config=cfg,
        installation=installation,
        command_runner=runner,
    )
    second = build.run_voice_render(
        paths_config=cfg,
        installation=installation,
        command_runner=runner,
    )

    assert len(first) == 1
    assert first[0].rendered is True
    assert second[0].cache_hit is True
    assert len(runner.commands) == 1


def test_run_voice_render_probes_ffmpeg_once_when_installation_is_not_injected(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_voice_profiles(cfg)
    _write_segment(cfg, "MEGAERA", "0_1_1")
    checker = FakeVoiceToolChecker()
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", checker)

    results = build.run_voice_render(paths_config=cfg, command_runner=CopyingRunner())

    assert len(results) == 1
    assert checker.calls == 1


def test_voice_analyze_writes_report(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    _write_voice_analysis_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")
    monkeypatch.setattr(build, "load_production_play", lambda cfg: _play_for_voice_analysis())

    result = CliRunner().invoke(build.app, ["voice-analyze", "--play", "test", "--actor", "phil", "--role", "MEGAERA"])

    assert result.exit_code == 0
    assert "Analyzed 1 voice-profile role(s)." in result.output
    assert "build/test/audio/voice_analysis/report.json" in result.output
    assert "phil@MEGAERA" in result.output


def _write_voice_profiles(cfg: paths.PathConfig, *, include_alex: bool = False) -> None:
    alex = """
  alex:
    baseline:
      pitch_center_hz: 180
""" if include_alex else ""
    alex_profile = """
  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: computed
""" if include_alex else ""
    (cfg.play_dir / "voice_profiles.yaml").write_text(
        f"""
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
{alex}
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: explicit
    transforms:
      - type: pitch
        semitones: 1.5
        strategy: preserve_tempo
{alex_profile}
""",
        encoding="utf-8",
    )


def _write_segment(cfg: paths.PathConfig, role: str, segment_id: str) -> None:
    path = cfg.segments_dir / role / f"{segment_id}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"source")


def _write_voice_analysis_wav(path: Path, *, sample_rate: int = 8_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        for frame in range(sample_rate):
            value = int(12_000 * math.sin(2 * math.pi * 100 * frame / sample_rate))
            frames.append(value.to_bytes(2, "little", signed=True))
        wav.writeframes(b"".join(frames))


def _play_for_voice_analysis() -> Play:
    block_id = BlockId(0, 1)
    return Play(
        source_text_metadata=SourceTextMetadata(title="Test"),
        reading_metadata=ReadingMetadata(reading_type="solo"),
        blocks=[
            RoleBlock(
                block_id=block_id,
                role_names=["MEGAERA"],
                text="one two three four",
                segments=[
                    SpeechSegment(
                        segment_id=SegmentId(block_id, 1),
                        text="one two three four",
                        role="MEGAERA",
                    )
                ],
            )
        ],
    )


def _config(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def _patch_path_config(monkeypatch, cfg: paths.PathConfig) -> None:
    monkeypatch.setattr(build.paths, "PathConfig", lambda play_name: cfg)
