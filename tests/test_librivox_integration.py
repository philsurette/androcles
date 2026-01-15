import pathlib
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import paths
from play_text_parser import PlayTextParser
from play_plan_builder import PlayPlanBuilder
from librivox_play_plan_decorator import LibrivoxPlayPlanDecorator


pytest.importorskip("pydub", reason="pydub required for integration test")


def _sample_play(tmp_path: Path) -> Path:
    text = """
    ## 1: First ##

    ANDROCLES. Hello

    ## 2: Second ##

    MEGAERA. Hi
    """
    path = tmp_path / "play.txt"
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return path


def test_librivox_plan_adds_preambles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _sample_play(tmp_path)
    play = PlayTextParser(source_path=src).parse()

    seg_dir = tmp_path / "segments"
    monkeypatch.setattr(paths, "SEGMENTS_DIR", seg_dir)
    for role, seg_id in (("ANDROCLES", "1_1_1"), ("MEGAERA", "2_1_1")):
        role_dir = seg_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / f"{seg_id}.wav").write_bytes(b"")

    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(lambda path, cache: 500))
    monkeypatch.setattr(paths.Paths, "get_audio_length_ms", lambda self, path: 500)
    monkeypatch.setattr(paths, "RECORDINGS_DIR", tmp_path / "recordings")

    builder = PlayPlanBuilder(play=play, segment_spacing_ms=0, librivox=True)
    plan = builder.build_audio_plan(part_no=1)

    assert plan[0].kind == "silence"
    assert plan[0].length_ms == LibrivoxPlayPlanDecorator.preamble_leading_silence_ms
    assert any(item.kind == "segment" for item in plan)
    assert plan[-1].kind == "silence"
