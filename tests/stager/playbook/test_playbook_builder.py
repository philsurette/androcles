from __future__ import annotations

import json
import wave
import zipfile
from pathlib import Path

import pytest

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DescriptionSegment, DirectionSegment, MetaSegment, SpeechSegment
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


def _named_cfg(tmp_path: Path, play_name: str) -> paths.PathConfig:
    return paths.PathConfig(
        play_name=play_name,
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


def _description_block(part_id: int, block_no: int, text: str) -> DescriptionBlock:
    block_id = BlockId(part_id, block_no)
    return DescriptionBlock(
        block_id=block_id,
        text=text,
        segments=[
            DescriptionSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
            )
        ],
    )


def _direction_block(part_id: int, block_no: int, text: str) -> DirectionBlock:
    block_id = BlockId(part_id, block_no)
    return DirectionBlock(
        block_id=block_id,
        text=text,
        segments=[
            DirectionSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
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

    zip_path = PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert zip_path == cfg.build_dir / "test-play.playbook.zip"
    assert zip_path.exists()
    megaera = next(role for role in data["roles"] if role["id"] == "MEGAERA")
    line = megaera["lines"][0]
    assert line["cue"]["speaker"] == "ANDROCLES"
    assert line["cue"]["audio"]["path"] == "audio/segments/ANDROCLES/0_1_1.wav"
    assert line["response"]["segments"][0]["audio"]["path"] == "audio/segments/MEGAERA/0_2_1.wav"
    assert (cfg.build_dir / "app" / line["cue"]["audio"]["path"]).exists()
    assert (cfg.build_dir / "app" / line["response"]["segments"][0]["audio"]["path"]).exists()
    assert data["context"][0]["kind"] == "heading"
    assert data["context"][0]["speaker"] == "_NARRATOR"
    assert data["context"][0]["audio"]["path"] == "audio/segments/_NARRATOR/0_0_1.wav"
    with zipfile.ZipFile(zip_path) as archive:
        assert "manifest.json" in archive.namelist()
        assert line["cue"]["audio"]["path"] in archive.namelist()
        assert line["response"]["segments"][0]["audio"]["path"] in archive.namelist()


def test_playbook_builder_exports_narrator_context_blocks(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    title_block = _title_block()
    description_block = _description_block(0, 1, "A path through a forest.")
    direction_block = _direction_block(0, 2, "Androcles enters.")
    response_block = _speech_block(0, 3, "MEGAERA", "I won't go another step.")
    play = _play([title_block, description_block, direction_block, response_block])
    for segment_id in ("0_0_1", "0_1_1", "0_2_1"):
        _write_wav(cfg.segments_dir / "_NARRATOR" / f"{segment_id}.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_3_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert [block["kind"] for block in data["context"]] == ["heading", "description", "direction"]
    assert [block["text"] for block in data["context"]] == [
        "Opening",
        "A path through a forest.",
        "Androcles enters.",
    ]
    assert data["context"][1]["audio"]["path"] == "audio/segments/_NARRATOR/0_1_1.wav"
    assert data["context"][2]["audio"]["path"] == "audio/segments/_NARRATOR/0_2_1.wav"
    assert "_ANNOUNCER" not in {block["speaker"] for block in data["context"]}


def test_playbook_builder_uses_part_title_as_first_line_cue(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
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


def test_playbook_builder_keeps_path_configs_isolated(tmp_path: Path) -> None:
    first_cfg = _named_cfg(tmp_path, "first-play")
    second_cfg = _named_cfg(tmp_path, "second-play")
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    for cfg in (first_cfg, second_cfg):
        _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
        _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    first_zip = PlaybookBuilder(play=play, paths=first_cfg).build()
    second_zip = PlaybookBuilder(play=play, paths=second_cfg).build()

    assert first_zip == first_cfg.build_dir / "first-play.playbook.zip"
    assert second_zip == second_cfg.build_dir / "second-play.playbook.zip"
    assert first_zip.exists()
    assert second_zip.exists()
    assert (first_cfg.build_dir / "app" / "manifest.json").exists()
    assert (second_cfg.build_dir / "app" / "manifest.json").exists()
