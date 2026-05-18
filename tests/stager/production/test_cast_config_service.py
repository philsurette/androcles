from __future__ import annotations

from pathlib import Path

import pytest

from stager.production.cast_config_service import CastConfigService
from stager.scriptwright import ProductionPlayLoader
from stager.shared import paths


def test_cast_service_assigns_actor_to_role(tmp_path: Path) -> None:
    cfg = _production(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()
    service = CastConfigService(paths_config=cfg, play=play)

    config = service.assign(role="CAPTAIN", actor="phil")

    assert config.actors["phil"].display_name == "phil"
    assert config.roles["CAPTAIN"].actor == "phil"
    assert "CAPTAIN:" in (cfg.play_dir / "cast.yaml").read_text(encoding="utf-8")


def test_cast_service_rejects_unknown_role(tmp_path: Path) -> None:
    cfg = _production(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    with pytest.raises(RuntimeError, match="Unknown rehearsable role"):
        CastConfigService(paths_config=cfg, play=play).assign(role="GHOST", actor="phil")


def test_cast_service_reports_unassigned_roles(tmp_path: Path) -> None:
    cfg = _production(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = CastConfigService(paths_config=cfg, play=play).validate()

    assert result.unknown_roles == ()
    assert result.unassigned_roles == ("CAPTAIN",)


def _production(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    return cfg
