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


def _replace_production_body(cfg: paths.PathConfig, body: str) -> None:
    lines = cfg.production_markdown.read_text(encoding="utf-8").splitlines()
    header_lines: list[str] = []
    for line in lines:
        if not line.startswith("//"):
            break
        header_lines.append(line)
    cfg.production_markdown.write_text("\n".join(header_lines) + f"\n\n{body}\n", encoding="utf-8")


def _production_version(cfg: paths.PathConfig) -> str:
    for line in cfg.production_markdown.read_text(encoding="utf-8").splitlines():
        if line.startswith("// production_version: "):
            return line.removeprefix("// production_version: ")
    raise AssertionError("Missing production_version metadata")


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


def test_text_cli_does_not_write_production_version_metadata(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    before = cfg.production_markdown.read_text(encoding="utf-8")
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["text", "--play", "test"])

    assert result.exit_code == 0
    assert cfg.production_markdown.read_text(encoding="utf-8") == before
    assert "// production_version:" not in cfg.production_markdown.read_text(encoding="utf-8")


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


def test_playbook_cli_does_not_create_or_back_write_production_version_metadata(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    before = cfg.production_markdown.read_text(encoding="utf-8")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "run_playbook", lambda **kwargs: cfg.build_dir / "test.playbook.zip")

    result = CliRunner().invoke(build.app, ["playbook", "--play", "test"])

    assert result.exit_code == 0
    assert cfg.production_markdown.read_text(encoding="utf-8") == before
    assert "// production_version:" not in cfg.production_markdown.read_text(encoding="utf-8")


def test_recording_request_cli_does_not_create_or_back_write_production_version_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    before = cfg.production_markdown.read_text(encoding="utf-8")
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "run_recording_request", lambda **kwargs: cfg.build_dir / "CAPTAIN.recording-request.zip")

    result = CliRunner().invoke(build.app, ["recording-request", "--role", "CAPTAIN", "--play", "test"])

    assert result.exit_code == 0
    assert cfg.production_markdown.read_text(encoding="utf-8") == before
    assert "// production_version:" not in cfg.production_markdown.read_text(encoding="utf-8")


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


def test_publish_production_cli_does_not_mutate_on_id_reuse_failure(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(cfg).publish(change_summary="Initial publish.")
    _replace_production_body(
        cfg,
        """# I-0 ACT I
I-1 CAPTAIN: Hold fast.""",
    )
    before = cfg.production_markdown.read_text(encoding="utf-8")
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(
        build.app,
        ["publish-production", "--change-summary", "Change captain line.", "--play", "test"],
    )

    assert result.exit_code != 0
    assert "I-1 -> I-1a" in result.output
    assert cfg.production_markdown.read_text(encoding="utf-8") == before


def test_publish_production_cli_reports_legacy_production_version(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked
// production_version: v0001
// parent_production_version: none

# I-0 ACT I
I-1 CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(
        build.app,
        ["publish-production", "--change-summary", "Initial table read.", "--play", "test"],
    )

    assert result.exit_code != 0
    assert "Legacy production version is not supported: v0001" in result.output


def test_production_diff_cli_reports_structured_versions(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(cfg).publish(change_summary="Initial publish.")
    production_version = _production_version(cfg)
    _replace_production_body(
        cfg,
        """# I-0 ACT I
I-1 CAPTAIN: Hold fast.""",
    )
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["production-diff", "--play", "test"])

    assert result.exit_code == 0
    assert f"Current published production: {production_version}" in result.output
    assert f"Working production version: {production_version}" in result.output
    assert "Working source has unpublished changes: yes" in result.output
    assert f"Production changes since {production_version}:" in result.output


def test_production_diff_cli_reports_stale_lineage(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(cfg).publish(change_summary="Initial publish.")
    version_one_source = cfg.production_markdown.read_text(encoding="utf-8")
    version_one = _production_version(cfg)
    _replace_production_body(
        cfg,
        """# I-0 ACT I
I-1 CAPTAIN: Stand fast.
I-2 CAPTAIN: Hold the line.""",
    )
    ProductionPublisher(cfg).publish(change_summary="Add line.", allow_id_reuse=True)
    version_two = _production_version(cfg)
    cfg.production_markdown.write_text(version_one_source, encoding="utf-8")
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["production-diff", "--play", "test"])

    assert result.exit_code == 0
    assert f"Current published production: {version_two}" in result.output
    assert f"Working production version: {version_one}" in result.output
    assert f"Lineage warning: working production is based on {version_one}, not current {version_two}." in result.output


def test_scriptwright_reconcile_reports_not_implemented(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["scriptwright", "reconcile", "--play", "test"])

    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
    assert "ScriptWright reconcile is not implemented yet" in str(result.exception)
