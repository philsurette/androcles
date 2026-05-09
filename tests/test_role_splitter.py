from __future__ import annotations

import pathlib
import sys
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import paths
from block_id import BlockId
from play import Play, Reader, ReadingMetadata, RoleBlock
from role_splitter import CalloutSplitter


def _path_config(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _play(reading_metadata: ReadingMetadata) -> Play:
    return Play(
        reading_metadata=reading_metadata,
        blocks=[
            RoleBlock(
                block_id=BlockId(1, 1),
                role_names=["LILLIAN"],
                callout="LILLIAN",
                text="Hello",
            )
        ],
    )


def test_callout_splitter_solo_reading_does_not_require_reader_header(tmp_path: Path) -> None:
    cfg = _path_config(tmp_path)
    cfg.markdown_roles_dir.mkdir(parents=True)
    (cfg.markdown_roles_dir / "_CALLER.md").write_text("# Callouts\n\nLILLIAN\n", encoding="utf-8")

    splitter = CalloutSplitter(
        play=_play(ReadingMetadata(reading_type="solo", readers=[Reader(id="_DEFAULT", reader="Phil")])),
        paths=cfg,
        role="_CALLER",
    )

    assert splitter.expected_ids() == ["LILLIAN"]


def test_callout_splitter_dramatic_reading_uses_reader_header(tmp_path: Path) -> None:
    cfg = _path_config(tmp_path)
    cfg.markdown_roles_dir.mkdir(parents=True)
    (cfg.markdown_roles_dir / "_CALLER.md").write_text(
        "# Callouts\n\ncallouts read by Caller Name\n\nLILLIAN\n",
        encoding="utf-8",
    )

    splitter = CalloutSplitter(
        play=_play(
            ReadingMetadata(
                reading_type="dramatic",
                readers=[
                    Reader(id="_DEFAULT", reader="Phil"),
                    Reader(id="_CALLER", reader="Caller Name"),
                ],
            )
        ),
        paths=cfg,
        role="_CALLER",
    )

    assert splitter.expected_ids() == ["LILLIAN"]
