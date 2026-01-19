#!/usr/bin/env python3
"""Build a summary worksheet for audio verifier diffs."""
from __future__ import annotations

from dataclasses import dataclass, field

from openpyxl.utils import get_column_letter

from audio_verifier_diff import AudioVerifierDiff
from extra_audio_diff import ExtraAudioDiff
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff


@dataclass
class AudioVerifierSummarySheetBuilder:
    headers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.headers:
            self.headers = ["role", "match", "delete", "extra", "inline_diffs"]

    def build_rows(
        self,
        diffs_by_role: dict[str, list[AudioVerifierDiff]],
        role_order: list[str] | None = None,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        order = role_order if role_order is not None else sorted(diffs_by_role)
        for role in order:
            if role not in diffs_by_role:
                raise RuntimeError(f"Missing diffs for role {role}")
            diffs = diffs_by_role[role]
            match_count = sum(isinstance(diff, MatchAudioDiff) for diff in diffs)
            delete_count = sum(isinstance(diff, MissingAudioDiff) for diff in diffs)
            extra_count = sum(isinstance(diff, ExtraAudioDiff) for diff in diffs)
            inline_diff_count = sum(
                isinstance(diff, MatchAudioDiff) and diff.match_quality > 0 for diff in diffs
            )
            rows.append(
                {
                    "role": role,
                    "match": match_count,
                    "delete": delete_count,
                    "extra": extra_count,
                    "inline_diffs": inline_diff_count,
                }
            )
        return rows

    def write_sheet(
        self,
        ws,
        diffs_by_role: dict[str, list[AudioVerifierDiff]],
        role_order: list[str] | None = None,
    ) -> None:
        ws.append(self.headers)
        rows = self.build_rows(diffs_by_role, role_order=role_order)
        for row in rows:
            ws.append([row.get(header, "") for header in self.headers])
        self._format_columns(ws)

    def _format_columns(self, ws) -> None:
        widths = {
            "role": 20,
            "match": 8,
            "delete": 8,
            "extra": 8,
            "inline_diffs": 12,
        }
        for idx, header in enumerate(self.headers, start=1):
            col_letter = get_column_letter(idx)
            if header in widths:
                ws.column_dimensions[col_letter].width = widths[header]
            if header != "role":
                for cell in ws[col_letter]:
                    if cell.row == 1:
                        continue
                    cell.alignment = cell.alignment.copy(horizontal="right")
