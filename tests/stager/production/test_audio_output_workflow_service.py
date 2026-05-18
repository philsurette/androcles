from __future__ import annotations

from pathlib import Path

import pytest

from stager.production.audio_output_workflow_service import AudioOutputWorkflowService
from stager.scriptwright import ProductionPlayLoader
from stager.shared import paths


def test_build_playbook_preserves_strict_missing_audio_failure(tmp_path: Path) -> None:
    cfg = _workspace(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    with pytest.raises(RuntimeError, match="Missing required"):
        AudioOutputWorkflowService(paths_config=cfg, play=play).build_playbook()


def test_build_playbook_returns_output_path_with_mocked_builder(tmp_path: Path, monkeypatch) -> None:
    cfg = _workspace(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    class FakePlaybookBuilder:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def build(self):
            return cfg.build_dir / "test.playbook.zip"

    monkeypatch.setattr("stager.production.audio_output_workflow_service.PlaybookBuilder", FakePlaybookBuilder)

    result = AudioOutputWorkflowService(paths_config=cfg, play=play).build_playbook(audio_source="canonical")

    assert result.paths == (cfg.build_dir / "test.playbook.zip",)
    assert result.audio_source == "canonical"


def test_build_audioplay_returns_output_paths_with_mocked_builder(tmp_path: Path, monkeypatch) -> None:
    cfg = _workspace(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    class FakeToolChecker:
        def require_audio_tools(self):
            return object()

    class FakeAudioPlayBuildService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def build(self, **kwargs):
            return [cfg.build_dir / "audio" / "test.mp3"]

    monkeypatch.setattr(
        "stager.production.audio_output_workflow_service.AudioPlayBuildService",
        FakeAudioPlayBuildService,
    )

    result = AudioOutputWorkflowService(
        paths_config=cfg,
        play=play,
        tool_checker=FakeToolChecker(),
    ).build_audioplay(audio_format="mp3")

    assert result.paths == (cfg.build_dir / "audio" / "test.mp3",)
    assert result.audio_source == "auto"


def _workspace(root: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=root / "src",
        build_root=root / "build",
        plays_dir=root / "plays",
        snippets_dir=root / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    (cfg.play_dir / "source_text_metadata.yaml").write_text("title: Test Play\n", encoding="utf-8")
    (cfg.play_dir / "reading_metadata.yaml").write_text("reading_type: solo\n", encoding="utf-8")
    return cfg
