from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from stager.cli import build
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation


def test_audio_cleanup_doctor_reports_capabilities(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "doctor", "--play", "test"])

    assert result.exit_code == 0
    assert "required cleanup filters: found" in result.output
    assert "optional cleanup filters found: adeclick, deesser, afftdn" in result.output


def test_audio_cleanup_plan_resolves_default_profile(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.segments_dir / "MEGAERA").mkdir(parents=True)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code == 0
    assert "cleanup approach: profile-based" in result.output
    assert "MEGAERA: profile gentle_voice_cleanup" in result.output
    assert "adeclick" in result.output


def test_audio_cleanup_plan_reports_missing_optional_filters(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.segments_dir / "MEGAERA").mkdir(parents=True)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker(filters={"loudnorm", "atrim", "asetpts"}))

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code == 0
    assert "MEGAERA: missing optional filters adeclick, deesser, afftdn" in result.output


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


class FakeAudioToolChecker:
    def __init__(self, filters: set[str] | None = None) -> None:
        self.filters = filters or {
            "loudnorm",
            "atrim",
            "asetpts",
            "adeclick",
            "deesser",
            "afftdn",
        }

    def require_audio_tools(self) -> FfmpegInstallation:
        return FfmpegInstallation(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            ffprobe_path=Path("/usr/bin/ffprobe"),
            source="PATH",
            config_path=None,
            filters=frozenset(self.filters),
        )
