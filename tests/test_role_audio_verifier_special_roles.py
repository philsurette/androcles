from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from block import RoleBlock
from block_id import BlockId
from play import Play, ReadingMetadata, Reader, SourceTextMetadata
from role_audio_verifier import RoleAudioVerifier


class DummyWhisperStore:
    def load(self, _model_name: str):
        return object()


def test_collect_expected_segments_for_caller() -> None:
    blocks = [
        RoleBlock(
            block_id=BlockId(0, 1),
            text="line",
            role_names=["KEEPER"],
            callout="CALL-BOY",
        ),
        RoleBlock(
            block_id=BlockId(0, 2),
            text="line",
            role_names=["KEEPER"],
            callout="LAVINIA",
        ),
        RoleBlock(
            block_id=BlockId(0, 3),
            text="line",
            role_names=["KEEPER"],
            callout="CALL-BOY",
        ),
    ]
    play = Play(
        reading_metadata=ReadingMetadata(
            reading_type="dramatic",
            readers=[Reader(id="_CALLER", reader="Caller Name")],
        ),
        source_text_metadata=SourceTextMetadata(
            title="Play",
            authors=["Author"],
        ),
        blocks=blocks,
    )
    verifier = RoleAudioVerifier(
        role="_CALLER",
        play=play,
        whisper_store=DummyWhisperStore(),
    )
    segments = verifier._collect_expected_segments()
    assert segments[0]["segment_id"] == "_CALLER_reader"
    assert segments[0]["expected_text"] == "callouts read by Caller Name"
    assert [seg["segment_id"] for seg in segments[1:]] == ["CALL-BOY", "LAVINIA"]
    assert [seg["expected_text"] for seg in segments[1:]] == ["CALL BOY", "LAVINIA"]


def test_collect_expected_segments_for_announcer() -> None:
    blocks = [
        RoleBlock(
            block_id=BlockId(0, 1),
            text="line",
            role_names=["KEEPER"],
            callout="KEEPER",
        ),
        RoleBlock(
            block_id=BlockId(1, 1),
            text="line",
            role_names=["KEEPER"],
            callout="KEEPER",
        ),
    ]
    play = Play(
        reading_metadata=ReadingMetadata(
            reading_type="dramatic",
            readers=[Reader(id="_ANNOUNCER", reader="Announcer Name")],
        ),
        source_text_metadata=SourceTextMetadata(
            title="The Play",
            authors=["Author"],
            original_publication_year="1912",
        ),
        blocks=blocks,
    )
    verifier = RoleAudioVerifier(
        role="_ANNOUNCER",
        play=play,
        whisper_store=DummyWhisperStore(),
    )
    segments = verifier._collect_expected_segments()
    assert segments[0]["segment_id"] == "_ANNOUNCER_reader"
    assert segments[0]["expected_text"] == "announcements read by Announcer Name"
    assert segments[1]["segment_id"] == "title"
    assert segments[1]["expected_text"] == "The Play"
    assert [seg["expected_text"] for seg in segments[-4:]] == [
        "section 0",
        "end of section 0",
        "section 1",
        "end of section 1",
    ]
