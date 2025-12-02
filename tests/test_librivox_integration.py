import pathlib

import pytest

pytest.importorskip("pydub", reason="pydub required for integration test")

from chapter_builder import ChapterBuilder
from play_plan_builder import PlayPlanBuilder, write_plan
from play_text import PlayTextParser
from callout_director import ConversationAwareCalloutDirector, RoleCalloutDirector, NoCalloutDirector


def _normalize_plan_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if "callouts/" in line:
            continue
        if "[chapter]" in line:
            continue
        if "[silence" in line:
            continue
        # Strip timestamp prefix for comparison.
        parts = line.split(" ", 1)
        lines.append(parts[1] if len(parts) > 1 else line)
    return "\n".join(lines)


def test_librivox_audio_plans_match_expected(tmp_path: pathlib.Path) -> None:
    resources = pathlib.Path(__file__).parent / "resources"
    play = PlayTextParser().parse()
    chapters = ChapterBuilder().build()

    parts = [0, 1, 2]
    include_callouts = True
    minimal_callouts = False

    for idx, part_id in enumerate(parts):
        director = (
            ConversationAwareCalloutDirector(play) if minimal_callouts else RoleCalloutDirector(play)
        )
        builder = PlayPlanBuilder(
            play_text=play,
            director=director if include_callouts else NoCalloutDirector(play),
            chapters=chapters,
            spacing_ms=1000,
            include_callouts=include_callouts,
            callout_spacing_ms=300,
            minimal_callouts=minimal_callouts,
            part_gap_ms=0,
            librivox=True,
        )
        plan, _ = builder.build_audio_plan(parts=[part_id], part_index_offset=idx, total_parts=len(parts))
        plan = [item for item in plan if item.__class__.__name__ != "Chapter"]

        actual_path = tmp_path / f"audio_plan_part_{part_id}.txt"
        write_plan(plan, actual_path)

        expected_path = resources / f"audio_plan_part_{part_id}.txt"
        assert expected_path.exists(), f"Missing expected plan {expected_path}"
        actual_text = _normalize_plan_text(actual_path.read_text(encoding="utf-8"))
        expected_text = _normalize_plan_text(expected_path.read_text(encoding="utf-8"))
        assert actual_text == expected_text, f"Plan mismatch for part {part_id}"
