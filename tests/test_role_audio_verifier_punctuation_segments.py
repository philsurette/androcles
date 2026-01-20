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
from segment import SpeechSegment
from segment_id import SegmentId


class DummyWhisperStore:
    def load(self, _model_name: str):
        return object()


def test_punctuation_only_segments_are_kept() -> None:
    block_id = BlockId(0, 1)
    seg = SpeechSegment(
        segment_id=SegmentId(block_id, 1),
        text="!!!",
        role="ANDROCLES",
    )
    block = RoleBlock(
        block_id=block_id,
        text="!!!",
        role_names=["ANDROCLES"],
        segments=[seg],
    )
    play = Play(
        reading_metadata=ReadingMetadata(
            reading_type="dramatic",
            readers=[Reader(id="_DEFAULT", reader="Reader")],
        ),
        source_text_metadata=SourceTextMetadata(
            title="Play",
            authors=["Author"],
        ),
        blocks=[block],
    )
    verifier = RoleAudioVerifier(
        role="ANDROCLES",
        play=play,
        whisper_store=DummyWhisperStore(),
    )

    segments, script_words, word_to_segment = verifier._build_expected_words()

    assert len(segments) == 1
    assert segments[0]["expected_text"] == "!!!"
    assert segments[0]["expected_word_count"] == 0
    assert script_words == []
    assert word_to_segment == []
