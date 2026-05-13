from __future__ import annotations

from pathlib import Path

from stager.shared import paths
from stager.text.text_artifact_builder import TextArtifactBuilder


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _write_production(cfg: paths.PathConfig) -> None:
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Hello (_/MEGAERA: crosses downstage_) there.
/MEGAERA: Moves behind ANDROCLES.
/*: Everyone freezes.
I-4 MEGAERA: I won't go another step.
""",
        encoding="utf-8",
    )


def test_text_artifacts_include_role_relevant_blocking_when_requested(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(cfg)

    TextArtifactBuilder(paths=cfg).build_all(include_blocking=True)

    play_markdown = (cfg.markdown_dir / "Untitled.md").read_text(encoding="utf-8")
    megaera_markdown = (cfg.markdown_roles_dir / "MEGAERA.md").read_text(encoding="utf-8")
    androcles_markdown = (cfg.markdown_roles_dir / "ANDROCLES.md").read_text(encoding="utf-8")

    assert "1.2 /MEGAERA: Moves behind ANDROCLES." in play_markdown
    assert "1.2 /MEGAERA: Moves behind ANDROCLES." in megaera_markdown
    assert "1.3 /*: Everyone freezes." in megaera_markdown
    assert "1.3 /*: Everyone freezes." in androcles_markdown
    assert "(_/MEGAERA: crosses downstage_)" in androcles_markdown


def test_text_artifacts_exclude_blocking_by_default(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(cfg)

    TextArtifactBuilder(paths=cfg).build_all()

    play_markdown = (cfg.markdown_dir / "Untitled.md").read_text(encoding="utf-8")
    megaera_markdown = (cfg.markdown_roles_dir / "MEGAERA.md").read_text(encoding="utf-8")
    androcles_markdown = (cfg.markdown_roles_dir / "ANDROCLES.md").read_text(encoding="utf-8")

    assert "/MEGAERA: Moves behind ANDROCLES." not in play_markdown
    assert "/MEGAERA: Moves behind ANDROCLES." not in megaera_markdown
    assert "/*: Everyone freezes." not in megaera_markdown
    assert "/*: Everyone freezes." not in androcles_markdown
    assert "(_/MEGAERA: crosses downstage_)" not in androcles_markdown
    assert "Hello there." in androcles_markdown
