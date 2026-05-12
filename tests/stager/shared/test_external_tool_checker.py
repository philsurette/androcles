from __future__ import annotations

import pytest

from stager.shared import external_tool_checker
from stager.shared.external_tool_checker import ExternalToolChecker


def test_external_tool_checker_allows_available_audio_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(external_tool_checker.shutil, "which", lambda tool: f"/usr/bin/{tool}")

    ExternalToolChecker().require_audio_tools()


def test_external_tool_checker_reports_missing_audio_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(external_tool_checker.shutil, "which", lambda tool: None)

    with pytest.raises(RuntimeError, match="Missing required audio tool\\(s\\): ffmpeg, ffprobe"):
        ExternalToolChecker().require_audio_tools()
