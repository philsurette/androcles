from __future__ import annotations

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
import segment_verifier
from chapter_builder import ChapterBuilder
from audio_plan import AudioPlan
from caption_builder import CaptionBuilder
from clip import ParallelClips, SegmentClip, Silence
from play_text_parser import PlayTextParser
from play_plan_builder import PlayPlanBuilder
from segment_verifier import SegmentVerifier


def _write_play(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "play.txt"
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def _sample_play(tmp_path: Path):
    text = """
    ## 1: Part One ##

    [[A quiet room]]

    ANDY/ANDROCLES. Hello there

    MEGAERA. (_aside_) Hmm

    ANDROCLES,MEGAERA. Together now
    """
    src = _write_play(tmp_path, text)
    return PlayTextParser(source_path=src).parse()


def test_build_segment_maps_handles_simultaneous(tmp_path: Path):
    play = _sample_play(tmp_path)

    seg_maps = play.build_segment_maps()

    assert seg_maps["ANDROCLES"][(1, 2)] == ["1_2_1"]
    assert seg_maps["ANDROCLES"][(1, 4)] == ["1_4_1"]
    assert seg_maps["MEGAERA"][(1, 3)] == ["1_3_2"]
    assert seg_maps["MEGAERA"][(1, 4)] == ["1_4_1"]


def test_play_plan_builder_inserts_preamble_and_chapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _sample_play(tmp_path)

    seg_dir = tmp_path / "segments"
    monkeypatch.setattr(paths, "SEGMENTS_DIR", seg_dir)
    for role, ids in {
        "ANDROCLES": ["1_2_1", "1_4_1"],
        "MEGAERA": ["1_3_2", "1_4_1"],
        "_NARRATOR": ["1_3_1"],
    }.items():
        role_dir = seg_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)
        for seg_id in ids:
            (role_dir / f"{seg_id}.wav").write_bytes(b"")

    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(lambda path, cache: 100))

    builder = PlayPlanBuilder(
        play=play,
        segment_spacing_ms=0,
        include_callouts=False,
        chapters=ChapterBuilder(play).build(),
    )
    plan = builder.build_audio_plan(part_no=1)

    assert isinstance(plan[0], Silence)
    assert plan[0].length_ms == 500
    chapters = [item for item in plan if item.__class__.__name__ == "Chapter"]
    assert len(chapters) == 1
    assert chapters[0].title == "Part One"
    assert chapters[0].offset_ms == plan[0].length_ms
    assert any(isinstance(item, ParallelClips) for item in plan)


def test_caption_builder_handles_parallel_group(tmp_path: Path):
    plan = AudioPlan()
    plan.addClip(
        SegmentClip(
            path=Path("a.wav"),
            text="Hello world",
            role="R1",
            clip_id="1:1:1",
            length_ms=500,
        )
    )
    plan.add_parallel(
        [
            SegmentClip(path=Path("b.wav"), text="Together", role="A", clip_id="1:2:1", length_ms=400),
            SegmentClip(path=Path("b.wav"), text="Line", role="B", clip_id="1:2:1", length_ms=200),
        ]
    )

    out_path = tmp_path / "captions.vtt"
    CaptionBuilder(plan, include_callouts=False).build(out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "Hello world" in content
    assert "Together" in content
    assert content.startswith("WEBVTT")


def test_segment_verifier_reports_offsets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    play = _sample_play(tmp_path)

    seg_dir = tmp_path / "segments"
    monkeypatch.setattr(paths, "SEGMENTS_DIR", seg_dir)
    for role, ids in {
        "ANDROCLES": ["1_2_1", "1_4_1"],
        "MEGAERA": ["1_3_2", "1_4_1"],
        "_NARRATOR": ["1_3_1"],
    }.items():
        role_dir = seg_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "offsets.txt").write_text(
            "\n".join(f"{seg_id} 0:00.0" for seg_id in ids), encoding="utf-8"
        )
        for seg_id in ids:
            (role_dir / f"{seg_id}.wav").write_bytes(b"")

    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(lambda path, cache: 1000))
    class _DummyAudio:
        def __len__(self):
            return 1000

    class _DummyAudioSegment:
        @staticmethod
        def from_file(path):
            return _DummyAudio()

    monkeypatch.setattr(segment_verifier, "AudioSegment", _DummyAudioSegment)

    plan = PlayPlanBuilder(play=play, segment_spacing_ms=0).build_audio_plan(part_no=1)
    verifier = SegmentVerifier(plan=plan, play=play)
    rows = verifier.compute_rows()

    sample = next(row for row in rows if row["id"] == "1_3_2")
    assert sample["actual_seconds"] == 1.0
    assert sample["start"] is not None
    assert sample["src_offset"] is not None
    assert sample["src_offset"].startswith("0:")
