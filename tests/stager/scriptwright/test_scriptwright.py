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

- P-1 @description: A road outside Rome.
- P-2 @direction: Thunder offstage.
- P-3 CAPTAIN: Hello (_draws sword_) there.
- P-4 GLADIATOR-1, GLADIATOR-2: Hail!
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


def test_write_locked_locks_draft_production_markdown(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
## SCENE I
@description: A dusty Roman road.
CAPTAIN: I will go (_draws sword_) if I must.
CAPTAIN, MEGAERA: Together.
""",
        encoding="utf-8",
    )

    output_path = ScriptWright(paths_config=cfg).write_locked()

    assert output_path == cfg.production_markdown
    assert cfg.production_markdown.read_text(encoding="utf-8") == """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I

## I.1-0 SCENE I

- I.1-1 @description: A dusty Roman road.
- I.1-2 CAPTAIN: I will go (_draws sword_) if I must.
- I.1-3 CAPTAIN, MEGAERA: Together.
"""


def test_write_locked_preserves_draft_comments_and_provisional_ids(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
// Director note: keep this beat.
I-7 CAPTAIN: Stand fast.
MEGAERA: I will.
""",
        encoding="utf-8",
    )

    ScriptWright(paths_config=cfg).write_locked()

    assert cfg.production_markdown.read_text(encoding="utf-8") == """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I

// Director note: keep this beat.
- I-7 CAPTAIN: Stand fast.
- I-8 MEGAERA: I will.
"""


def test_reconcile_reports_clear_not_implemented_message(tmp_path):
    cfg = _path_config(tmp_path)

    with pytest.raises(NotImplementedError, match="ScriptWright reconcile is not implemented yet"):
        ScriptWright(paths_config=cfg).reconcile()


def test_write_locked_rejects_generated_duplicate_production_ids(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
I-0 CAPTAIN: Duplicate the generated heading id.
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Duplicate production id after assignment"):
        ScriptWright(paths_config=cfg).write_locked()


def test_render_from_play_text_supports_markdown_formats(tmp_path):
    cfg = _path_config(tmp_path)
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.

MEGAERA.
I will.
""",
        encoding="utf-8",
    )

    compact = ScriptWright(paths_config=cfg).render_from_play_text(output_format="compact")
    listed = ScriptWright(paths_config=cfg).render_from_play_text(output_format="list")
    doublespaced = ScriptWright(paths_config=cfg).render_from_play_text(output_format="doublespace")

    assert "\nI-1 CAPTAIN: Stand fast.\nI-2 MEGAERA: I will.\n" in compact
    assert "\n# I-0 ACT I\n\n- I-1 CAPTAIN: Stand fast.\n- I-2 MEGAERA: I will.\n" in listed
    assert "\n# I-0 ACT I\n\nI-1 CAPTAIN: Stand fast.\n\nI-2 MEGAERA: I will.\n" in doublespaced


def test_androcles_play_text_is_ingestable():
    cfg = PathConfig("androcles")

    production = ScriptWright(paths_config=cfg).render_from_play_text()

    assert production.startswith("// script_format: quince-production-v1\n")
    assert "# P-0 PROLOGUE\n" in production
    assert "# I-0 ACT I\n" in production
    assert "# II-0 ACT II\n" in production
    assert "P-5 MEGAERA:" in production
