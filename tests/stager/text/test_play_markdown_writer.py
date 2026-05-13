from __future__ import annotations

from stager.domain.play import Play, SourceTextMetadata
from stager.shared import paths
from stager.text.play_markdown_writer import PlayMarkdownWriter


def test_play_markdown_writer_uses_file_safe_title(tmp_path):
    cfg = paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    play = Play(
        source_text_metadata=SourceTextMetadata(
            title="The Curious Case of the Cottingley Fairies",
        )
    )

    path = PlayMarkdownWriter(play=play, paths=cfg).to_markdown()

    assert path == cfg.markdown_dir / "The_Curious_Case_of_the_Cottingley_Fairies.md"
