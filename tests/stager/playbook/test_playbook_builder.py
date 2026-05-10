from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from stager.domain.block import RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import MetaSegment, SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.playbook.playbook_builder import PlaybookBuilder
from stager.shared import paths


def _write_wav(path: Path, duration_ms: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_rate = 8_000
    frame_count = int(frame_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _title_block() -> TitleBlock:
    block_id = BlockId(0, 0)
    return TitleBlock(
        block_id=block_id,
        text="## 0: Opening ##",
        segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text="## 0: Opening ##")],
        part_id=0,
        heading="Opening",
    )


def _speech_block(part_id: int, block_no: int, role: str, text: str) -> RoleBlock:
    block_id = BlockId(part_id, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=role,
        text=text,
        segments=[
            SpeechSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
                role=role,
            )
        ],
    )


def _play(blocks) -> Play:
    return Play(
        source_text_metadata=SourceTextMetadata(
            title="Androcles and the Lion",
            authors=["George Bernard Shaw"],
            source="Project Gutenberg",
        ),
        reading_metadata=ReadingMetadata(reading_type="solo"),
        blocks=list(blocks),
    )


def test_playbook_builder_writes_manifest_and_copies_required_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")

    manifest_path = PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    megaera = next(role for role in data["roles"] if role["id"] == "MEGAERA")
    line = megaera["lines"][0]
    assert line["cue"]["speaker"] == "ANDROCLES"
    assert line["cue"]["audio"]["path"] == "audio/segments/ANDROCLES/0_1_1.wav"
    assert line["response"]["segments"][0]["audio"]["path"] == "audio/segments/MEGAERA/0_2_1.wav"
    assert (cfg.build_dir / "app" / line["cue"]["audio"]["path"]).exists()
    assert (cfg.build_dir / "app" / line["response"]["segments"][0]["audio"]["path"]).exists()


def test_playbook_builder_uses_part_title_as_first_line_cue(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    manifest_path = PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    line = data["roles"][0]["lines"][0]
    assert line["cue"]["speaker"] == "_NARRATOR"
    assert line["cue"]["text"] == "Opening"
    assert line["cue"]["audio"]["path"] == "audio/segments/_NARRATOR/0_0_1.wav"


def test_playbook_builder_fails_on_missing_response_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")

    with pytest.raises(RuntimeError, match="Missing required response audio for role MEGAERA segment 0_2_1"):
        PlaybookBuilder(play=play, paths=cfg).build()


def test_playbook_builder_fails_on_missing_cue_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    with pytest.raises(RuntimeError, match="Missing required cue audio for role _NARRATOR segment 0_0_1"):
        PlaybookBuilder(play=play, paths=cfg).build()
