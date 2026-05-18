from __future__ import annotations

from pathlib import Path

import pytest

from stager.production.quince_context import QuinceContextResolver, QuinceWorkspaceConfig


def test_context_infers_play_from_play_directory(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")

    context = QuinceContextResolver(cwd=tmp_path / "plays" / "hamlet").resolve()

    assert context.workspace_root == tmp_path
    assert context.play_id == "hamlet"
    assert context.selection_source == "play-directory"
    assert context.path_config.play_dir == tmp_path / "plays" / "hamlet"


def test_context_infers_play_from_nested_play_directory(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")
    nested = tmp_path / "plays" / "androcles" / "notes"
    nested.mkdir()

    context = QuinceContextResolver(cwd=nested).resolve()

    assert context.play_id == "androcles"
    assert context.selection_source == "play-directory"


def test_context_infers_play_from_build_directory(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")
    build_dir = tmp_path / "build" / "androcles" / "app"
    build_dir.mkdir(parents=True)

    context = QuinceContextResolver(cwd=build_dir).resolve()

    assert context.play_id == "androcles"
    assert context.selection_source == "build-directory"


def test_context_uses_explicit_play_over_directory(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")

    context = QuinceContextResolver(cwd=tmp_path / "plays" / "hamlet").resolve(play_id="androcles")

    assert context.play_id == "androcles"
    assert context.selection_source == "explicit"


def test_context_uses_quince_yaml_active_play(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")
    QuinceContextResolver(cwd=tmp_path).save_workspace_config(
        tmp_path,
        QuinceWorkspaceConfig(active_play="hamlet"),
    )

    context = QuinceContextResolver(cwd=tmp_path).resolve()

    assert context.play_id == "hamlet"
    assert context.selection_source == "quince.yaml"


def test_context_rejects_ambiguous_multi_play_workspace(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")

    with pytest.raises(RuntimeError, match="Multiple productions found"):
        QuinceContextResolver(cwd=tmp_path).resolve()


def test_context_uses_single_play_fallback(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")

    context = QuinceContextResolver(cwd=tmp_path).resolve()

    assert context.play_id == "androcles"
    assert context.selection_source == "single-play"


def test_context_uses_workspace_environment_variable(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")
    outside = tmp_path / "outside"
    outside.mkdir()

    context = QuinceContextResolver(
        cwd=outside,
        environ={"QUINCE_WORKSPACE": tmp_path.as_posix()},
    ).resolve()

    assert context.workspace_root == tmp_path
    assert context.play_id == "androcles"


def _workspace(root: Path, *play_ids: str) -> None:
    (root / "plays").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    for play_id in play_ids:
        (root / "plays" / play_id).mkdir(parents=True)
