#!/usr/bin/env python3
"""Generate a multi-sheet XLSX timing report from build/audio/timings.csv."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from paths import AUDIO_OUT_DIR
from segment_verifier import compute_rows


def safe_sheet_name(name: str, existing: set[str]) -> str:
    base = name[:31] if len(name) > 31 else name
    candidate = base
    idx = 1
    while candidate in existing:
        suffix = f"_{idx}"
        candidate = (base[: 31 - len(suffix)] + suffix) if len(base) + len(suffix) > 31 else base + suffix
        idx += 1
    existing.add(candidate)
    return candidate


def write_sheet(ws, headers, rows):
    ws.append(headers)
    for row in rows:
        values = []
        for h in headers:
            val = row.get(h, "")
            if h in {"expected_seconds", "actual_seconds", "percent"} and val not in ("", None):
                try:
                    val = float(val)
                except ValueError:
                    pass
            values.append(val)
        ws.append(values)
    # Apply number formats
    for col in ws.iter_cols(min_row=2, max_row=ws.max_row):
        header = col[0].offset(row=-1).value  # header cell above data
        if header in ("expected_seconds", "actual_seconds"):
            for cell in col:
                cell.number_format = "0.0"
        elif header == "percent":
            for cell in col:
                cell.number_format = "0.0"
    # Widen text column
    if "text" in headers:
        idx = headers.index("text") + 1  # 1-based
        ws.column_dimensions[get_column_letter(idx)].width = 60


def generate_xlsx():
    rows = compute_rows()
    headers = ["id", "warning", "expected_seconds", "actual_seconds", "percent", "start_seconds", "role", "text"]
    wb = Workbook()
    ws = wb.active
    ws.title = "All"
    write_sheet(ws, headers, rows)

    by_role = defaultdict(list)
    for row in rows:
        role = row.get("role", "") or "_NARRATOR"
        by_role[role].append(row)

    used_names: set[str] = {"All"}
    for role, role_rows in sorted(by_role.items()):
        name = safe_sheet_name(role, used_names)
        ws_role = wb.create_sheet(title=name)
        write_sheet(ws_role, headers, role_rows)

    out_path = AUDIO_OUT_DIR / "timings.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    generate_xlsx()
