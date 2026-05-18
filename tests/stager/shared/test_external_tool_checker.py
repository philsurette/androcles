from __future__ import annotations

import pytest

from stager.shared.external_tool_checker import ExternalToolChecker


def test_external_tool_checker_allows_available_audio_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    class Probe:
        def find_installation(self):
            return object()

    assert ExternalToolChecker(probe=Probe()).require_audio_tools() is not None


def test_external_tool_checker_reports_missing_audio_tools() -> None:
    class Probe:
        def find_installation(self):
            raise RuntimeError("Missing required audio tool(s): ffmpeg, ffprobe")

    with pytest.raises(RuntimeError, match="Missing required audio tool\\(s\\): ffmpeg, ffprobe"):
        ExternalToolChecker(probe=Probe()).require_audio_tools()
