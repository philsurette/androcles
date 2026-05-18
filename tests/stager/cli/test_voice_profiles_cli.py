from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from typer.testing import CliRunner

from stager.cli import build
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation, REQUIRED_VOICE_PROFILE_FILTERS


class FakeVoiceToolChecker:
    def __init__(self, filters: set[str] | None = None) -> None:
        self.filters = filters or set(REQUIRED_VOICE_PROFILE_FILTERS)

    def require_audio_tools(self) -> FfmpegInstallation:
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
