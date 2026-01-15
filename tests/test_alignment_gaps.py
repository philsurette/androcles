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
from cue_builder import CueBuilder
from librivox_play_plan_decorator import LibrivoxPlayPlanDecorator
from play import Play, TitleBlock
from block_id import BlockId
from segment import MetaSegment
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


def test_cue_builder_prefers_split_callouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _dummy_play()
    builder = CueBuilder(play)

    monkeypatch.setattr(paths, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr("cue_builder.AudioSegment", type("Audio", (), {"from_file": staticmethod(lambda path: "dummy")}))

    split_callouts = paths.BUILD_DIR / "audio" / "callouts"
    split_callouts.mkdir(parents=True, exist_ok=True)
    (split_callouts / "A_callout.wav").write_bytes(b"")

    # Point CALLOUTS_DIR somewhere else to surface the mismatch.
    monkeypatch.setattr(paths, "CALLOUTS_DIR", tmp_path / "plays_callouts")

    clip = builder._load_callout("A")

    assert clip is not None


def test_librivox_preamble_uses_announcer_segments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _dummy_play()
    plan = AudioPlan()
    decorator = LibrivoxPlayPlanDecorator(play=play, plan=plan)

    monkeypatch.setattr(paths, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr(paths, "SEGMENTS_DIR", paths.BUILD_DIR / "audio")

    split_announcer = paths.SEGMENTS_DIR / "_ANNOUNCER"
    split_announcer.mkdir(parents=True, exist_ok=True)
    for name in ["title.wav", "author.wav", "reader.wav"]:
        (split_announcer / name).write_bytes(b"")

    decorator.paths.get_audio_length_ms = lambda path: 0  # type: ignore[assignment]

    # Keep RECORDINGS_DIR distinct from split outputs to highlight mismatch.
    monkeypatch.setattr(paths, "RECORDINGS_DIR", tmp_path / "recordings")

    decorator.add_project_preamble(part_no=1)

    expected = split_announcer / "title.wav"
    clip_paths = [getattr(item, "path", None) for item in plan if hasattr(item, "path")]
    assert expected in clip_paths
