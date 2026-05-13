from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from stager.cli import build
from stager.shared import paths


def test_audio_command_checks_required_audio_tools(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    audio_path = tmp_path / "input.wav"
    audio_path.write_bytes(b"")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", MissingAudioToolChecker())

    result = CliRunner().invoke(build.app, ["normalize", str(audio_path), "--play", "test"])

    assert result.exit_code != 0
    assert "Missing required audio tool" in result.output


def test_text_command_does_not_check_required_audio_tools(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", MissingAudioToolChecker())
    monkeypatch.setattr(build, "run_text", lambda **kwargs: None)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code == 0


def test_wav_playbook_does_not_check_required_audio_tools(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", MissingAudioToolChecker())
    monkeypatch.setattr(build, "run_playbook", lambda **kwargs: cfg.build_dir / "test.playbook.zip")

    result = CliRunner().invoke(build.app, ["playbook", "--play", "test"])

    assert result.exit_code == 0


def test_playbook_reports_missing_required_audio_without_traceback(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)

    def fail_playbook(**kwargs) -> Path:
        raise RuntimeError(
            "Missing required cue audio for role ALICE segment 1_0_1 "
            "while building Playbook: build/test/audio/segments/ALICE/1_0_1.wav"
        )

    monkeypatch.setattr(build, "run_playbook", fail_playbook)

    result = CliRunner().invoke(build.app, ["playbook", "--play", "test"])

    assert result.exit_code != 0
    assert "Missing required cue audio for role ALICE segment 1_0_1" in result.output
    assert "Traceback" not in result.output


def test_mp3_playbook_checks_required_audio_tools(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", MissingAudioToolChecker())

    result = CliRunner().invoke(build.app, ["playbook", "--play", "test", "--audio-format", "mp3"])

    assert result.exit_code != 0
    assert "Missing required audio tool" in result.output


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


class MissingAudioToolChecker:
    def require_audio_tools(self) -> None:
        raise RuntimeError("Missing required audio tool")
