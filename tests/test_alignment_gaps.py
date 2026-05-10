from __future__ import annotations

import pathlib
import sys
from pathlib import Path

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import paths
from audio_plan import AudioPlan
from block import RoleBlock
from block_id import BlockId
from cue_builder import CueBuilder
from librivox_play_plan_decorator import LibrivoxPlayPlanDecorator
from play import Play, TitleBlock
from pydub import AudioSegment
from segment import MetaSegment, SpeechSegment
from segment_id import SegmentId


def _dummy_play() -> Play:
    tb = TitleBlock(
        block_id=BlockId(1, 0),
        text="## 1: One ##",
        segments=[MetaSegment(segment_id=SegmentId(BlockId(1, 0), 1), text="## 1: One ##")],
        part_id=1,
        heading="One",
    )
    return Play(blocks=[tb])


def _role_block(part: int, block_no: int, role: str, text: str) -> RoleBlock:
    block_id = BlockId(part, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=role,
        text=text,
        segments=[SpeechSegment(segment_id=SegmentId(block_id, 1), text=text, role=role)],
    )


def _write_wav(path: Path, duration_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    AudioSegment.silent(duration=duration_ms).export(path, format="wav")


def test_cue_builder_loads_split_callouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _dummy_play()
    cfg = paths.PathConfig(play_name="test", build_root=tmp_path / "build", plays_dir=tmp_path / "plays", snippets_dir=tmp_path / "snippets")
    builder = CueBuilder(play, paths=cfg)

    monkeypatch.setattr("cue_builder.AudioSegment", type("Audio", (), {"from_file": staticmethod(lambda path: "dummy")}))

    split_callouts = cfg.build_dir / "audio" / "callouts"
    split_callouts.mkdir(parents=True, exist_ok=True)
    (split_callouts / "A.wav").write_bytes(b"")

    clip = builder._load_callout("A")

    assert clip is not None


def test_cue_builder_returns_combined_audio_and_chapters(tmp_path: Path):
    play = Play(
        blocks=[
            _role_block(0, 1, "A", "Your cue."),
            _role_block(0, 2, "B", "My line."),
        ]
    )
    cfg = paths.PathConfig(play_name="test", build_root=tmp_path / "build", plays_dir=tmp_path / "plays", snippets_dir=tmp_path / "snippets")
    _write_wav(cfg.segments_dir / "A" / "0_1_1.wav", 100)
    _write_wav(cfg.segments_dir / "B" / "0_2_1.wav", 120)
    _write_wav(cfg.build_dir / "audio" / "callouts" / "A.wav", 30)
    builder = CueBuilder(play, paths=cfg, response_delay_ms=10, callout_spacing_ms=0)

    audio, chapters = builder.build_cues_for_role("B")

    assert len(audio) > 0
    assert [chapter[2] for chapter in chapters] == ["CUE A 0_1_1", "LINE B 0_2_1"]
    assert chapters[0][0] < chapters[0][1] <= chapters[1][0] < chapters[1][1]


def test_cue_builder_works_when_prompts_are_disabled(tmp_path: Path):
    play = Play(
        blocks=[
            _role_block(0, 1, "A", "Your cue."),
            _role_block(0, 2, "B", "My line."),
        ]
    )
    cfg = paths.PathConfig(play_name="test", build_root=tmp_path / "build", plays_dir=tmp_path / "plays", snippets_dir=tmp_path / "snippets")
    _write_wav(cfg.segments_dir / "B" / "0_2_1.wav", 120)
    builder = CueBuilder(play, paths=cfg, response_delay_ms=10, include_prompts=False)

    audio, chapters = builder.build_cues_for_role("B")

    assert len(audio) > 0
    assert [chapter[2] for chapter in chapters] == ["LINE B 0_2_1"]


def test_librivox_preamble_uses_announcer_segments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _dummy_play()
    plan = AudioPlan()
    cfg = paths.PathConfig(play_name="test", build_root=tmp_path / "build", plays_dir=tmp_path / "plays", snippets_dir=tmp_path / "snippets")
    decorator = LibrivoxPlayPlanDecorator(play=play, plan=plan, paths=cfg)

    split_announcer = cfg.segments_dir / "_ANNOUNCER"
    split_announcer.mkdir(parents=True, exist_ok=True)
    for name in ["title.wav", "author.wav"]:
        (split_announcer / name).write_bytes(b"")

    decorator.paths.get_audio_length_ms = lambda path: 0  # type: ignore[assignment]

    decorator.add_project_preamble(part_no=1)

    expected = split_announcer / "title.wav"
    clip_paths = [getattr(item, "path", None) for item in plan if hasattr(item, "path")]
    assert expected in clip_paths
