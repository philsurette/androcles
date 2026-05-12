from __future__ import annotations

import pytest

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.segment import DirectionSegment, SimultaneousSegment, SpeechSegment
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared.paths import PathConfig


def _path_config(tmp_path, play_name: str = "test-play") -> PathConfig:
    play_dir = tmp_path / "plays" / play_name
    play_dir.mkdir(parents=True)
    return PathConfig(
        play_name,
        plays_dir=tmp_path / "plays",
        build_root=tmp_path / "build",
    )


def test_load_locked_production_markdown_into_play_model(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 @description: A dusty Roman road.
I-2 @direction: The soldiers move aside.
I-3 CAPTAIN: I will go (_draws sword_) if I must.
I-4 CAPTAIN, MEGAERA: Together.
""",
        encoding="utf-8",
    )

    play = ProductionPlayLoader(paths_config=cfg).load()

    assert [part.title for part in play.parts] == ["ACT I"]
    assert isinstance(play.blocks[0], TitleBlock)
    assert isinstance(play.blocks[1], DescriptionBlock)
    assert isinstance(play.blocks[2], DirectionBlock)
    assert isinstance(play.blocks[3], RoleBlock)
    assert isinstance(play.blocks[4], RoleBlock)
    assert play.blocks[3].block_id == BlockId(1, 3)
    assert [segment.__class__ for segment in play.blocks[3].segments] == [
        SpeechSegment,
        DirectionSegment,
        SpeechSegment,
    ]
    assert isinstance(play.blocks[4].segments[0], SimultaneousSegment)
    assert play.getRole("CAPTAIN") is not None
    assert play.getRole("MEGAERA") is not None
    assert play.to_index_entries() == [
        (1, 0, "_NARRATOR"),
        (1, 1, "_NARRATOR"),
        (1, 2, "_NARRATOR"),
        (1, 3, "_NARRATOR"),
        (1, 3, "CAPTAIN"),
        (1, 4, "CAPTAIN"),
        (1, 4, "MEGAERA"),
    ]


def test_load_rejects_draft_production_markdown(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
CAPTAIN: I will go.
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Stager requires locked production script"):
        ProductionPlayLoader(paths_config=cfg).load()


def test_load_rejects_missing_production_markdown(tmp_path):
    cfg = _path_config(tmp_path)

    with pytest.raises(RuntimeError, match="run './main scriptwright lock' first"):
        ProductionPlayLoader(paths_config=cfg).load()


def test_load_generated_androcles_production_markdown():
    play = ProductionPlayLoader(paths_config=PathConfig("androcles")).load()

    assert play.title == "Androcles and the Lion"
    assert [part.title for part in play.parts][:3] == ["PROLOGUE", "ACT I", "ACT II"]
    assert play.getRole("ANDROCLES") is not None
    assert play.getRole("CAPTAIN") is not None
    assert play.getRole("MEGAERA") is not None
