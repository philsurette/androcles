from __future__ import annotations

import pathlib
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stager.shared import paths
from stager.audio.announcer_splitter import AnnouncerSplitter
from stager.cli.build import run_audioplay, run_playbook, run_text, run_write_announcer
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.scriptwright import ScriptWright


def _config(tmp_path: Path, build_type: str = "custom") -> paths.PathConfig:
    (tmp_path / "play-config.yaml").write_text(
        f"play_id: test\nbuild_type: {build_type}\n",
        encoding="utf-8",
    )
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    cfg.play_text.write_text(
        textwrap.dedent(
            """
            ## 1: First ##

            ANDROCLES. Hello
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    ScriptWright(paths_config=cfg).write_locked()
    return cfg


def test_run_write_announcer_uses_configured_librivox_build_type(tmp_path: Path) -> None:
    cfg = _config(tmp_path, build_type="librivox")

    path = run_write_announcer(paths_config=cfg)

    content = path.read_text(encoding="utf-8")
    assert "This is a Librivox Recording." in content
    assert "section 1" in content


def test_run_write_announcer_can_be_forced_to_custom(tmp_path: Path) -> None:
    cfg = _config(tmp_path, build_type="librivox")

    path = run_write_announcer(paths_config=cfg, build_type="custom")

    content = path.read_text(encoding="utf-8")
    assert "This is a Librivox Recording." not in content
    assert "End of" in content


def test_run_text_writes_caller_script_but_not_callouts_index(tmp_path: Path) -> None:
    cfg = _config(tmp_path)

    run_text(paths_config=cfg)

    caller_content = (cfg.markdown_roles_dir / "_CALLER.md").read_text(encoding="utf-8")
    announcer_content = (cfg.markdown_roles_dir / "_ANNOUNCER.md").read_text(encoding="utf-8")
    narrator_content = (cfg.markdown_roles_dir / "_NARRATOR.md").read_text(encoding="utf-8")

    assert "callouts read by" not in caller_content
    assert "announcements read by" not in announcer_content
    assert narrator_content.startswith("Read by Anonymous")
    assert not (cfg.markdown_dir / "_CALLOUTS.md").exists()


def test_announcer_splitter_uses_librivox_build_type() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(),
        source_text_metadata=SourceTextMetadata(title="The Play", authors=["Author"]),
    )
    splitter = AnnouncerSplitter(play=play, build_type="librivox")

    expected_ids = splitter.expected_ids()

    assert "librivox-this_is_a_librivox_recording" in expected_ids


def test_run_audioplay_passes_librivox_build_type_to_preparation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config(tmp_path, build_type="custom")
    calls: list[tuple[str, str | None]] = []

    def fake_build_text(self, *, line_no_prefix: bool, build_type: str) -> None:
        calls.append(("text", build_type))

    def fake_build_segments(self, *, build_type: str, **kwargs) -> None:
        calls.append(("segments", build_type))

    @dataclass
    class FakePlayBuilder:
        librivox: bool

        def __init__(self, **kwargs):
            self.librivox = kwargs["librivox"]

        def build_audio(self, part_no: int | None):
            calls.append(("builder", "librivox" if self.librivox else "custom"))
            return []

    monkeypatch.setattr("stager.audiobook.audio_play_build_service.TextArtifactBuilder.build_all", fake_build_text)
    monkeypatch.setattr("stager.audiobook.audio_play_build_service.SegmentBuildService.build", fake_build_segments)
    monkeypatch.setattr("stager.audiobook.audio_play_build_service.PlayBuilder", FakePlayBuilder)

    run_audioplay(
        paths_config=cfg,
        librivox=True,
        generate_audio=False,
        normalize_output=False,
    )

    assert calls == [
        ("text", "librivox"),
        ("segments", "librivox"),
        ("builder", "librivox"),
    ]


def test_run_playbook_passes_build_type_to_builder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config(tmp_path, build_type="librivox")
    calls: list[str] = []

    @dataclass
    class FakePlaybookBuilder:
        build_type: str

        def __init__(self, **kwargs):
            self.build_type = kwargs["build_type"]

        def build(self) -> Path:
            calls.append(self.build_type)
            return cfg.build_dir / "test-play.playbook.zip"

    monkeypatch.setattr("stager.cli.build.PlaybookBuilder", FakePlaybookBuilder)

    path = run_playbook(paths_config=cfg)

    assert path == cfg.build_dir / "test-play.playbook.zip"
    assert calls == ["librivox"]
