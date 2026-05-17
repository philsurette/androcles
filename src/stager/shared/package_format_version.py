from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


_FORMAT_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class FormatVersionDecision(str, Enum):
    ACCEPT = "accept"
    WARN = "warn"
    REJECT = "reject"


@dataclass(frozen=True, order=True)
class PackageFormatVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "PackageFormatVersion":
        match = _FORMAT_VERSION_PATTERN.match(value.strip())
        if not match:
            raise ValueError(f"Invalid package format version: {value}")
        return cls(*(int(part) for part in match.groups()))

    @classmethod
    def from_manifest(cls, manifest: dict) -> "PackageFormatVersion":
        format_version = manifest.get("format_version")
        if isinstance(format_version, str) and format_version:
            return cls.parse(format_version)
        if manifest.get("schema_version") == 1:
            return cls(1, 0, 0)
        raise ValueError("Package manifest is missing a supported format_version")

    def compatibility_with(self, supported: "PackageFormatVersion") -> FormatVersionDecision:
        if self.major != supported.major:
            return FormatVersionDecision.REJECT
        if self.minor > supported.minor:
            return FormatVersionDecision.WARN
        return FormatVersionDecision.ACCEPT

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
