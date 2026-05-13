from __future__ import annotations

import pytest

from stager.domain.block import BlockingBlock, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.segment import BlockingSegment, DirectionSegment, SimultaneousSegment, SpeechSegment
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
/MEGAERA: crosses downstage.
I-6 CAPTAIN: Wait (_/MEGAERA: takes CAPTAIN's hand_) now.
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
    assert isinstance(play.blocks[5], BlockingBlock)
    assert play.blocks[3].block_id == BlockId(1, 3)
    assert [segment.__class__ for segment in play.blocks[3].segments] == [
        SpeechSegment,
        DirectionSegment,
        SpeechSegment,
    ]
    assert isinstance(play.blocks[4].segments[0], SimultaneousSegment)
    assert isinstance(play.blocks[5].segments[0], BlockingSegment)
    assert play.blocks[5].targets == ["MEGAERA"]
    assert [segment.__class__ for segment in play.blocks[6].segments] == [
        SpeechSegment,
        BlockingSegment,
        SpeechSegment,
    ]
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
        (1, 5, "_NARRATOR"),
        (1, 6, "CAPTAIN"),
    ]
    assert play.blocks[0].production_id == "I-0"
    assert play.blocks[0].content_hash.startswith("sha256:")
    assert play.blocks[1].production_id == "I-1"
    assert play.blocks[1].segments[0].production_id == "I-1:d1"
    assert play.blocks[3].production_id == "I-3"
    assert play.blocks[3].segments[0].production_id == "I-3:s1"
    assert play.blocks[3].segments[1].production_id == "I-3:d1"
    assert play.blocks[3].segments[2].production_id == "I-3:s2"
    assert play.blocks[4].segments[0].production_id == "I-4:s1"
    assert play.blocks[5].production_id == "I-6:b1"
    assert play.blocks[5].placement == "before"
    assert play.blocks[5].segments[0].production_id == "I-6:b1"
    assert play.blocks[5].segments[0].placement == "before"
    assert play.blocks[6].segments[1].production_id == "I-6:b2"
    assert play.blocks[6].segments[1].placement == "inline"


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
