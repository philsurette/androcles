"""Parse canonical production markdown."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from stager.scriptwright.production_script import (
    ProductionEntry,
    ProductionEntryKind,
    ProductionScript,
)
from stager.shared import paths


@dataclass
class ProductionScriptParser:
    """Strict parser for `production.md` files."""

    source_path: Path | None = None

    METADATA_RE = re.compile(r"^//\s*(?P<key>[a-z_]+):\s*(?P<value>.+?)\s*$")
    PRODUCTION_ID_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?$")
    HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<body>.+?)\s*$")
    ROLE_RE = re.compile(r"^(?P<roles>[A-Z][A-Z0-9_ -]*(?:\s*,\s*[A-Z][A-Z0-9_ -]*)*)\s*:\s*(?P<text>.+)$")
    LABEL_RE = re.compile(r"^(?P<label>@[a-z]+)\s*:\s*(?P<text>.+)$")
    REQUIRED_METADATA = {
        "script_format": "quince-production-v1",
        "source_kind": "production",
    }
    ALLOWED_METADATA_KEYS = {"script_format", "source_kind", "production_ids"}
    ALLOWED_PRODUCTION_IDS = {"draft", "locked"}

    def parse_path(self, source_path: Path | None = None) -> ProductionScript:
        path = source_path or self.source_path
        if path is None:
            raise RuntimeError("ProductionScriptParser requires a source path")
        return self.parse_text(path.read_text(encoding="utf-8"), source_path=path)

    def parse_text(self, text: str, source_path: Path | None = None) -> ProductionScript:
        path = source_path or self.source_path
        metadata: dict[str, str] = {}
        entries: list[ProductionEntry] = []
        seen_ids: set[str] = set()
        in_metadata = True

        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("//"):
                if in_metadata:
                    self._parse_metadata_line(line, metadata, index, path)
                continue

            in_metadata = False
            if not metadata:
                self._fail("Missing metadata header", index, path)
            locked = self._metadata_lock_state(metadata, index, path) == "locked"
            entry = self._parse_entry(line, locked, index, path)
            if entry.production_id is not None:
                if entry.production_id in seen_ids:
                    self._fail(f"Duplicate production id: {entry.production_id}", index, path)
                seen_ids.add(entry.production_id)
            entries.append(entry)

        self._validate_metadata(metadata, len(text.splitlines()) or 1, path)
        return ProductionScript(metadata=metadata, entries=tuple(entries))

    def _parse_metadata_line(
        self,
        line: str,
        metadata: dict[str, str],
        line_no: int,
        path: Path | None,
    ) -> None:
        match = self.METADATA_RE.match(line)
        if not match:
            return
        key = match.group("key")
        value = match.group("value")
        if key not in self.ALLOWED_METADATA_KEYS:
            self._fail(f"Unknown metadata key: {key}", line_no, path)
        if key in metadata:
            self._fail(f"Duplicate metadata key: {key}", line_no, path)
        metadata[key] = value

    def _metadata_lock_state(self, metadata: dict[str, str], line_no: int, path: Path | None) -> str:
        if "production_ids" not in metadata:
            self._fail("Missing required metadata: production_ids", line_no, path)
        value = metadata["production_ids"]
        if value not in self.ALLOWED_PRODUCTION_IDS:
            self._fail(f"Unknown production_ids value: {value}", line_no, path)
        return value

    def _validate_metadata(self, metadata: dict[str, str], line_no: int, path: Path | None) -> None:
        for key, value in self.REQUIRED_METADATA.items():
            if metadata.get(key) != value:
                self._fail(f"Missing or invalid metadata: {key}", line_no, path)
        self._metadata_lock_state(metadata, line_no, path)

    def _parse_entry(
        self,
        line: str,
        locked: bool,
        line_no: int,
        path: Path | None,
    ) -> ProductionEntry:
        heading_match = self.HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group("marks"))
            production_id, text = self._extract_optional_id(heading_match.group("body"), locked, line_no, path)
            return ProductionEntry(
                kind=ProductionEntryKind.HEADING,
                production_id=production_id,
                heading_level=level,
                text=text,
                line_no=line_no,
            )

        production_id, body = self._extract_optional_id(line, locked, line_no, path)
        label_match = self.LABEL_RE.match(body)
        if label_match:
            label = label_match.group("label")
            text = label_match.group("text").strip()
            if label == "@description":
                return ProductionEntry(ProductionEntryKind.DESCRIPTION, text, line_no, production_id)
            if label == "@direction":
                return ProductionEntry(ProductionEntryKind.DIRECTION, text, line_no, production_id)
            self._fail(f"Unknown reserved entry label: {label}", line_no, path)

        role_match = self.ROLE_RE.match(body)
        if role_match:
            roles = tuple(role.strip() for role in role_match.group("roles").split(","))
            if any(not role for role in roles):
                self._fail("Empty role tag", line_no, path)
            text = role_match.group("text").strip()
            self._validate_inline_directions(text, line_no, path)
            return ProductionEntry(
                kind=ProductionEntryKind.ROLE,
                text=text,
                line_no=line_no,
                production_id=production_id,
                roles=roles,
            )

        self._fail("Malformed production script entry", line_no, path)

    def _extract_optional_id(
        self,
        body: str,
        locked: bool,
        line_no: int,
        path: Path | None,
    ) -> tuple[str | None, str]:
        first, _, rest = body.partition(" ")
        if self.PRODUCTION_ID_RE.match(first):
            if not rest.strip():
                self._fail("Missing text after production id", line_no, path)
            return first, rest.strip()
        if locked:
            self._fail("Locked production entry is missing a production id", line_no, path)
        return None, body.strip()

    def _validate_inline_directions(self, text: str, line_no: int, path: Path | None) -> None:
        in_direction = False
        index = 0
        while index < len(text):
            if text.startswith("(_", index):
                if in_direction:
                    self._fail("Nested inline direction", line_no, path)
                in_direction = True
                index += 2
                continue
            if text.startswith("_)", index):
                if not in_direction:
                    self._fail("Unopened inline direction", line_no, path)
                in_direction = False
                index += 2
                continue
            index += 1
        if in_direction:
            self._fail("Unclosed inline direction", line_no, path)

    def _fail(self, message: str, line_no: int, path: Path | None) -> None:
        if path is None:
            raise RuntimeError(f"{message} at line {line_no}")
        raise RuntimeError(f"{message} at {paths.display_location(path, line_no)}")
