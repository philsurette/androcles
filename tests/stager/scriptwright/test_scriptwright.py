from __future__ import annotations

import pytest

from stager.scriptwright import ScriptWright
from stager.shared.paths import PathConfig


def _path_config(tmp_path, play_name: str = "test-play") -> PathConfig:
    play_dir = tmp_path / "plays" / play_name
    play_dir.mkdir(parents=True)
    return PathConfig(
        play_name,
        plays_dir=tmp_path / "plays",
        build_root=tmp_path / "build",
    )


def test_render_from_play_text_locks_current_play_format(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.play_text.write_text(
        """## 0: PROLOGUE ##

[[A road outside Rome.]]

__Thunder offstage.__

CAPTAIN.
Hello (_draws sword_) there.

GLADIATORS [GLADIATOR-1, GLADIATOR-2]. Hail!
""",
        encoding="utf-8",
    )

    production = ScriptWright(paths_config=cfg).render_from_play_text()

    assert production == """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# P-0 PROLOGUE
P-1 @description: A road outside Rome.
P-2 @direction: Thunder offstage.
P-3 CAPTAIN: Hello (_draws sword_) there.
P-4 GLADIATOR-1, GLADIATOR-2: Hail!
"""


def test_write_from_play_text_refuses_to_overwrite_locked_output(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.
""",
        encoding="utf-8",
    )
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Refusing to overwrite locked production script"):
        ScriptWright(paths_config=cfg).write_from_play_text()


def test_androcles_play_text_is_ingestable():
    cfg = PathConfig("androcles")

    production = ScriptWright(paths_config=cfg).render_from_play_text()

    assert production.startswith("// script_format: quince-production-v1\n")
    assert "# P-0 PROLOGUE\n" in production
    assert "# I-0 ACT I\n" in production
    assert "# II-0 ACT II\n" in production
    assert "P-5 MEGAERA:" in production
