from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from stager.cli.quince import app
from stager.shared import paths


def test_quince_help_does_not_require_workspace() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Producer workflow CLI" in result.output


def test_quince_status_help_does_not_require_workspace() -> None:
    result = CliRunner().invoke(app, ["status", "--help"])

    assert result.exit_code == 0
    assert "Show production, cast, recording, and Playbook readiness" in result.output


def test_quince_list_shows_workspace_productions(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")

    result = CliRunner().invoke(app, ["list", "--workspace", tmp_path.as_posix()])

    assert result.exit_code == 0
    assert "androcles" in result.output
    assert "hamlet" in result.output


def test_quince_use_writes_active_play(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")

    result = CliRunner().invoke(app, ["use", "androcles", "--workspace", tmp_path.as_posix()])

    assert result.exit_code == 0
    assert "Active production: androcles" in result.output
    assert "active_play: androcles" in (tmp_path / "quince.yaml").read_text(encoding="utf-8")


def test_quince_status_infers_play_from_current_directory(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["status", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["context"]["play_id"] == "androcles"
    assert data["context"]["selection_source"] == "play-directory"
    assert data["status"]["play_id"] == "androcles"


def test_quince_status_rejects_ambiguous_workspace(tmp_path: Path, monkeypatch) -> None:
    _scriptwright_workspace(tmp_path, "androcles")
    _scriptwright_workspace(tmp_path, "hamlet")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code != 0
    assert "Multiple productions found" in result.output


def test_quince_next_recommends_publish_for_unpublished_changes(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["next"])

    assert result.exit_code == 0
    assert "Next: publish" in result.output
    assert "quince publish --play androcles" in result.output


def test_quince_changes_shows_current_diff(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["changes"])

    assert result.exit_code == 0
    assert "Current published production: none" in result.output
    assert "Working source has unpublished changes: yes" in result.output
    assert "No prior published production version." in result.output


def test_quince_publish_requires_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish"])

    assert result.exit_code != 0
    assert "Publishing requires --change-summary or --allow-empty-summary" in result.output


def test_quince_publish_writes_new_production_version(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish", "--change-summary", "Initial publish."])

    assert result.exit_code == 0
    assert "Published production" in result.output
    assert "// production_version:" in cfg.production_markdown.read_text(encoding="utf-8")


def _workspace(root: Path, *play_ids: str) -> None:
    (root / "plays").mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    for play_id in play_ids:
        (root / "plays" / play_id).mkdir(parents=True, exist_ok=True)


def _scriptwright_workspace(root: Path, play_id: str) -> paths.PathConfig:
    _workspace(root, play_id)
    cfg = paths.PathConfig(
        play_name=play_id,
        root=root / "src",
        build_root=root / "build",
        plays_dir=root / "plays",
        snippets_dir=root / "snippets",
    )
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.
""",
        encoding="utf-8",
    )
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    (cfg.play_dir / "source_text_metadata.yaml").write_text("title: Test Play\n", encoding="utf-8")
    (cfg.play_dir / "reading_metadata.yaml").write_text("reading_type: solo\n", encoding="utf-8")
    return cfg
