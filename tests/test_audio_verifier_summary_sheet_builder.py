from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audio_verifier_summary_sheet_builder import AudioVerifierSummarySheetBuilder
from extra_audio_diff import ExtraAudioDiff
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff


def test_summary_builder_counts() -> None:
    diffs_by_role = {
        "ROLE1": [
            MatchAudioDiff(0, 100, "1_1", "a", "a", "a", 0),
            MatchAudioDiff(0, 100, "1_2", "a", "b", "[b/a]", 1),
            MissingAudioDiff(None, None, "1_3", "missing"),
            ExtraAudioDiff(None, None, "extra"),
        ],
        "ROLE2": [
            MatchAudioDiff(0, 100, "2_1", "x", "x", "x", 0),
        ],
    }
    builder = AudioVerifierSummarySheetBuilder()

    rows = builder.build_rows(diffs_by_role, role_order=["ROLE1", "ROLE2"])

    assert rows == [
        {
            "role": "ROLE1",
            "match": 2,
            "delete": 1,
            "extra": 1,
            "inline_diffs": 1,
        },
        {
            "role": "ROLE2",
            "match": 1,
            "delete": 0,
            "extra": 0,
            "inline_diffs": 0,
        },
    ]
