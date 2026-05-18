from __future__ import annotations

import pytest
import typer

from stager.cli.build import run_playbook


def test_run_playbook_rejects_unknown_audio_format() -> None:
    with pytest.raises(typer.BadParameter, match="audio-format must be one of: wav, mp3"):
        run_playbook(audio_format="flac")


def test_run_playbook_rejects_unknown_audio_source() -> None:
    with pytest.raises(typer.BadParameter, match="audio-source must be one of: auto, canonical, cleaned"):
        run_playbook(audio_source="mixed")
