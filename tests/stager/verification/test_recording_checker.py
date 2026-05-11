from __future__ import annotations

from stager.verification.recording_checker import summarize_rows


def test_summarize_rows_groups_warnings_by_role() -> None:
    rows = [
        {"role": "A", "id": "1_1_1", "warning": ""},
        {"role": "A", "id": "1_2_1", "warning": "<"},
        {"role": "B", "id": "1_3_1", "warning": "-"},
        {"role": "_NARRATOR", "id": "1_4_1", "warning": ""},
    ]

    assert summarize_rows(rows) == [
        "! A: 1_2_1",
        "✖ B: 1_3_1",
        "✓ _NARRATOR: OK",
    ]
