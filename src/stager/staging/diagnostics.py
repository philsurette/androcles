from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StagingDiagnostic:
    severity: str
    message: str
    line_no: int | None = None

    def to_dict(self) -> dict:
        data = {
            "severity": self.severity,
            "message": self.message,
        }
        if self.line_no is not None:
            data["line_no"] = self.line_no
        return data
