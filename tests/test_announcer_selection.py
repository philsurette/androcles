from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from announcer import Announcer, LibrivoxAnnouncer, select_announcer
from play import Play, ReadingMetadata, SourceTextMetadata


def test_select_announcer_uses_custom_target_by_default() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(),
        source_text_metadata=SourceTextMetadata(
            title="The Play",
            authors=["Author"],
        ),
    )

    announcer = select_announcer(play)

    assert isinstance(announcer, Announcer)
    assert not isinstance(announcer, LibrivoxAnnouncer)


def test_select_announcer_honors_explicit_build_type() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(target="librivox"),
        source_text_metadata=SourceTextMetadata(
            title="The Play",
            authors=["Author"],
        ),
    )

    announcer = select_announcer(play, build_type="custom")

    assert isinstance(announcer, Announcer)
    assert not isinstance(announcer, LibrivoxAnnouncer)


def test_select_announcer_uses_librivox_build_type() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(),
        source_text_metadata=SourceTextMetadata(
            title="The Play",
            authors=["Author"],
        ),
    )

    announcer = select_announcer(play, build_type="librivox")

    assert isinstance(announcer, LibrivoxAnnouncer)
