from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from stager.cli import build
from stager.production_publication.production_publisher import ProductionPublisher
from stager.scriptwright import ScriptWright
from stager.shared import paths


def _config(tmp_path: Path) -> paths.PathConfig:
    (tmp_path / "play-config.yaml").write_text("play_id: test\nbuild_type: custom\n", encoding="utf-8")
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
    def fake_path_config(play_name: str) -> paths.PathConfig:
        return cfg

    monkeypatch.setattr(build.paths, "PathConfig", fake_path_config)


def test_text_cli_rejects_missing_production_markdown(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "run './main scriptwright lock' first" in str(result.exception)


def test_text_cli_rejects_draft_production_markdown(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "Stager requires locked production script" in str(result.exception)


def test_text_cli_uses_locked_production_markdown(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code == 0
    assert (cfg.markdown_dir / "Untitled.md").exists()


def test_text_cli_auto_uses_published_production_when_available(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(cfg).publish()
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Working text.
""",
        encoding="utf-8",
    )
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code == 0
    assert "Stand fast." in (cfg.markdown_dir / "Untitled.md").read_text(encoding="utf-8")
    assert "Working text." not in (cfg.markdown_dir / "Untitled.md").read_text(encoding="utf-8")


def test_text_cli_short_production_source_option_can_use_working_source(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(cfg).publish()
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Working text.
""",
        encoding="utf-8",
    )
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "-ps", "working", "--play", "test"])

    assert result.exit_code == 0
    assert "Working text." in (cfg.markdown_dir / "Untitled.md").read_text(encoding="utf-8")


def test_publish_production_cli_requires_change_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["publish-production", "--play", "test"])

    assert result.exit_code != 0
    assert "Publishing requires --change-summary or --allow-empty-summary." in result.output


def test_publish_production_cli_accepts_change_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(
        build.app,
        ["publish-production", "--change-summary", "Initial table read.", "--play", "test"],
    )

    assert result.exit_code == 0
    production_text = cfg.production_markdown.read_text(encoding="utf-8")
    assert "// production_version: " in production_text
    assert "// parent_production_version: none" in production_text
    assert "// production_note: Initial table read." in production_text


def test_publish_production_cli_can_allow_empty_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["publish-production", "--allow-empty-summary", "--play", "test"])

    assert result.exit_code == 0
    production_text = cfg.production_markdown.read_text(encoding="utf-8")
    assert "// production_version: " in production_text
    assert "// production_note: Published production." in production_text


def test_scriptwright_reconcile_reports_not_implemented(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["scriptwright", "reconcile", "--play", "test"])

    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
    assert "ScriptWright reconcile is not implemented yet" in str(result.exception)
