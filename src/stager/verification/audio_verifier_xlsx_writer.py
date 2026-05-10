#!/usr/bin/env python3
"""Write audio verifier diffs to an XLSX file."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook

from audio_verifier_diff import AudioVerifierDiff
from audio_verifier_sheet_builder import AudioVerifierSheetBuilder


@dataclass
class AudioVerifierXlsxWriter:
    headers: list[str] | None = None
    sheet_builder: AudioVerifierSheetBuilder = field(default_factory=AudioVerifierSheetBuilder)

    def write(self, diffs: list[AudioVerifierDiff], out_path: Path, sheet_name: str = "Verification") -> Path:
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name[:31]
        builder = self.sheet_builder
        if self.headers is not None:
            builder = AudioVerifierSheetBuilder(headers=self.headers)
        builder.write_sheet(ws, diffs)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(out_path)
        return out_path
