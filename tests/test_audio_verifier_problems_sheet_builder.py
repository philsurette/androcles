from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audio_verifier_problems_sheet_builder import AudioVerifierProblemsSheetBuilder
from extra_audio_diff import ExtraAudioDiff
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff


def test_problems_builder_rows() -> None:
    diffs_by_role = {
        "ROLE1": [
            MatchAudioDiff(0, 100, "1_1", "exp", "heard", "[heard/exp]", 1),
            MatchAudioDiff(0, 100, "1_2", "exp", "exp", "exp", 0),
            MissingAudioDiff(None, None, "1_3", "missing"),
            ExtraAudioDiff(None, None, "extra words"),
        ],
        "ROLE2": [
            MatchAudioDiff(0, 100, "2_1", "exp", "exp", "exp", 0),
        ],
    }
    builder = AudioVerifierProblemsSheetBuilder()

    rows = builder.build_rows(diffs_by_role, role_order=["ROLE1", "ROLE2"])

    assert rows == [
        {
            "ROLE": "ROLE1",
            "type": "/",
            "id": "1_1",
            "offset": "",
            "len": 100,
            "dc": 1,
            "diff": "[heard/exp]",
            "heard": "heard",
            "expected": "exp",
        },
        {
            "ROLE": "ROLE1",
            "type": "-",
            "id": "1_3",
            "offset": "",
            "len": "",
            "dc": "",
            "diff": "",
            "heard": "",
            "expected": "missing",
        },
        {
            "ROLE": "ROLE1",
            "type": "+",
            "id": "",
            "offset": "",
            "len": "",
            "dc": "",
            "diff": "",
            "heard": "extra words",
            "expected": "",
        },
    ]


def test_problems_builder_filters_vetted_ids() -> None:
    diffs_by_role = {
        "ROLE1": [
            MatchAudioDiff(0, 100, "1_1", "exp", "heard", "[heard/exp]", 1),
            MissingAudioDiff(None, None, "1_3", "missing"),
            ExtraAudioDiff(None, None, "extra words"),
        ],
    }
    vetted_ids = {"ROLE1": {"1_1", "1_3"}}
    builder = AudioVerifierProblemsSheetBuilder()

    problems = builder.build_rows(diffs_by_role, vetted_ids_by_role=vetted_ids)
    vetted = builder.build_rows(
        diffs_by_role,
        vetted_ids_by_role=vetted_ids,
        include_vetted=True,
    )

    assert problems == [
        {
            "ROLE": "ROLE1",
            "type": "+",
            "id": "",
            "offset": "",
            "len": "",
            "dc": "",
            "diff": "",
            "heard": "extra words",
            "expected": "",
        },
    ]
    assert vetted == [
        {
            "ROLE": "ROLE1",
            "type": "/",
            "id": "1_1",
            "offset": "",
            "len": 100,
            "dc": 1,
            "diff": "[heard/exp]",
            "heard": "heard",
            "expected": "exp",
        },
        {
            "ROLE": "ROLE1",
            "type": "-",
            "id": "1_3",
            "offset": "",
            "len": "",
            "dc": "",
            "diff": "",
            "heard": "",
            "expected": "missing",
        },
    ]
