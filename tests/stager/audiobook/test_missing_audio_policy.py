from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from stager.audiobook.play_plan_builder import PlayPlanBuilder
from stager.cues.callout_director import RoleCalloutDirector
from stager.shared import paths
from stager.text.play_text_parser import PlayTextParser


def _config(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _parse_play(tmp_path: Path, cfg: paths.PathConfig, content: str):
    play_path = tmp_path / "play.txt"
    play_path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return PlayTextParser(source_path=play_path, paths_config=cfg).parse()


def _write_segment(cfg: paths.PathConfig, role: str, segment_id: str) -> None:
    path = cfg.segments_dir / role / f"{segment_id}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")


def _existing_audio_length(path: Path, cache: dict[Path, int] | None = None) -> int:
    if not path.exists():
        raise RuntimeError(f"Audio file missing: {paths.display_path(path)}")
    return 100


def test_audioplay_plan_fails_when_role_segment_audio_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    play = _parse_play(
        tmp_path,
        cfg,
        """
        ## 1: Part One ##

        ANDROCLES. Hello.
        """,
    )
    _write_segment(cfg, "_NARRATOR", "1_0_1")
    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(_existing_audio_length))

    builder = PlayPlanBuilder(play=play, paths=cfg, segment_spacing_ms=0)

    with pytest.raises(RuntimeError, match=r"Audio file missing: .*ANDROCLES/1_1_1\.wav"):
        builder.build_audio_plan(part_no=1)


def test_audioplay_plan_fails_when_simultaneous_segment_audio_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    play = _parse_play(
        tmp_path,
        cfg,
        """
        ## 1: Part One ##

        ANDROCLES,MEGAERA. Together.
        """,
    )
    _write_segment(cfg, "_NARRATOR", "1_0_1")
    _write_segment(cfg, "ANDROCLES", "1_1_1")
    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(_existing_audio_length))

    builder = PlayPlanBuilder(play=play, paths=cfg, segment_spacing_ms=0)

    with pytest.raises(RuntimeError, match=r"Audio file missing: .*MEGAERA/1_1_1\.wav"):
        builder.build_audio_plan(part_no=1)


def test_audioplay_plan_fails_when_enabled_callout_audio_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    play = _parse_play(
        tmp_path,
        cfg,
        """
        ## 1: Part One ##

        ANDROCLES. Hello.
        """,
    )
    _write_segment(cfg, "_NARRATOR", "1_0_1")
    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(_existing_audio_length))
    builder = PlayPlanBuilder(
        play=play,
        paths=cfg,
        director=RoleCalloutDirector(play, paths_config=cfg),
        include_callouts=True,
        segment_spacing_ms=0,
    )

    with pytest.raises(RuntimeError, match=r"Callout missing for role ANDROCLES"):
        builder.build_audio_plan(part_no=1)


def test_librivox_plan_fails_when_required_snippet_audio_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    play = _parse_play(
        tmp_path,
        cfg,
        """
        ## 1: Part One ##

        ANDROCLES. Hello.
        """,
    )
    _write_segment(cfg, "_NARRATOR", "1_0_1")
    _write_segment(cfg, "ANDROCLES", "1_1_1")
    snippets_dir = cfg.general_snippets_dir
    snippets_dir.mkdir(parents=True, exist_ok=True)
    (snippets_dir / "section 1 of.wav").write_bytes(b"placeholder")
    announcer_dir = cfg.segments_dir / "_ANNOUNCER"
    announcer_dir.mkdir(parents=True, exist_ok=True)
    (announcer_dir / "title.wav").write_bytes(b"placeholder")
    monkeypatch.setattr(PlayPlanBuilder, "get_audio_length_ms", staticmethod(_existing_audio_length))
    monkeypatch.setattr(paths.PathConfig, "get_audio_length_ms", lambda self, path: _existing_audio_length(path))

    builder = PlayPlanBuilder(play=play, paths=cfg, segment_spacing_ms=0, librivox=True)

    with pytest.raises(RuntimeError, match=r"Audio file missing: .*librivox/this is a LibriVox recording\.wav"):
        builder.build_audio_plan(part_no=1)
