from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from stager.cli import build
from stager.production.production_status import ProductionStatusService
from stager.scriptwright import ProductionPlayLoader, ScriptWright
from stager.shared import paths


def test_production_status_reports_cast_and_segment_coverage(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  CAPTAIN:
    actor: phil
    recording: whole-role
    voice_profile: phil@CAPTAIN
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    segment_id = next(segment_id for ids in play.getRole("CAPTAIN").segments().values() for segment_id in ids)
    segment_path = cfg.segments_dir / "CAPTAIN" / f"{segment_id}.wav"
    segment_path.parent.mkdir(parents=True, exist_ok=True)
    segment_path.write_bytes(b"wav")

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.cast_configured is True
    assert status.roles[0].role == "CAPTAIN"
    assert status.roles[0].actor == "phil"
    assert status.roles[0].recording == "whole-role"
    assert status.roles[0].voice_profile == "phil@CAPTAIN"
    assert status.roles[0].recorded_segments == 1
    assert status.roles[0].missing_segments == ()


def test_production_status_cli_renders_basic_readiness(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["production-status", "--play", "test"])

    assert result.exit_code == 0
    assert "Production status for test: Untitled" in result.output
    assert "Cast config: missing" in result.output
    assert "CAPTAIN: unassigned, linerecorder, 0/1 segments, 1 missing" in result.output
    assert "Unassigned roles: CAPTAIN" in result.output
    assert "Missing segment recordings: 1" in result.output


def _config(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.
""",
        encoding="utf-8",
    )
    return cfg


def _patch_path_config(monkeypatch, cfg: paths.PathConfig) -> None:
    monkeypatch.setattr(build.paths, "PathConfig", lambda play_name: cfg)
