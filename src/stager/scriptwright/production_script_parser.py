"""Parse canonical production markdown."""
from __future__ import annotations

from dataclasses import dataclass, replace
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
    PRODUCTION_ID_CANDIDATE_RE = re.compile(r"^[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?$")
    PRODUCTION_ID_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?$")
    HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<body>.+?)\s*$")
    ROLE_RE = re.compile(r"^(?P<roles>[A-Z][A-Z0-9_ -]*(?:\s*,\s*[A-Z][A-Z0-9_ -]*)*)\s*:\s*(?P<text>.+)$")
    LABEL_RE = re.compile(r"^(?P<label>@[a-z]+)\s*:\s*(?P<text>.+)$")
    BLOCKING_RE = re.compile(r"^/(?P<targets>[^:]+):\s*(?P<text>.*)$")
    INLINE_BLOCKING_RE = re.compile(r"\(_/(?P<targets>[^:]+):(?P<text>.*?)_\)")
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
        seen_non_blocking_ids: set[str] = set()
        in_metadata = True
        pending_comments: list[str] = []

        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if raw_line[:1].isspace() and not line.startswith("//"):
                self._fail("Multiline script entries are not supported", index, path)
            if line.startswith("//"):
                if in_metadata:
                    self._parse_metadata_line(line, metadata, index, path)
                else:
                    pending_comments.append(line)
                continue

            line = self._strip_optional_list_marker(line)
            in_metadata = False
            if not metadata:
                self._fail("Missing metadata header", index, path)
            locked = self._metadata_lock_state(metadata, index, path) == "locked"
            entry = self._parse_entry(line, locked, index, path, tuple(pending_comments))
            pending_comments = []
            if entry.production_id is not None:
                if entry.production_id in seen_non_blocking_ids and entry.kind != ProductionEntryKind.BLOCKING:
                    self._fail(f"Duplicate production id: {entry.production_id}", index, path)
                if entry.kind != ProductionEntryKind.BLOCKING:
                    seen_non_blocking_ids.add(entry.production_id)
            entries.append(entry)

        self._validate_metadata(metadata, len(text.splitlines()) or 1, path)
        return ProductionScript(metadata=metadata, entries=tuple(self._resolve_idless_blocking(entries, path)))

    def _strip_optional_list_marker(self, line: str) -> str:
        if line.startswith("- "):
            return line[2:].strip()
        return line

    def _resolve_idless_blocking(self, entries: list[ProductionEntry], path: Path | None) -> list[ProductionEntry]:
        resolved_entries: list[ProductionEntry] = []
        for index, entry in enumerate(entries):
            if entry.kind != ProductionEntryKind.BLOCKING or entry.production_id is not None:
                resolved_entries.append(entry)
                continue
            associated_id = self._next_script_unit_id(entries, index)
            placement = "before"
            if associated_id is None:
                associated_id = self._previous_script_unit_id(entries, index)
                placement = "after"
            if associated_id is None:
                self._fail("Blocking entry is missing an associated production id", entry.line_no, path)
            resolved_entries.append(replace(entry, production_id=associated_id, placement=placement))
        return resolved_entries

    def _next_script_unit_id(self, entries: list[ProductionEntry], index: int) -> str | None:
        for candidate in entries[index + 1 :]:
            if candidate.kind == ProductionEntryKind.HEADING:
                break
            if candidate.kind == ProductionEntryKind.BLOCKING:
                continue
            if candidate.production_id is not None:
                return candidate.production_id
        return None

    def _previous_script_unit_id(self, entries: list[ProductionEntry], index: int) -> str | None:
        for candidate in reversed(entries[:index]):
            if candidate.kind == ProductionEntryKind.HEADING:
                break
            if candidate.kind == ProductionEntryKind.BLOCKING:
                continue
            if candidate.production_id is not None:
                return candidate.production_id
        return None

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
        leading_comments: tuple[str, ...] = (),
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
                leading_comments=leading_comments,
            )

        idless_blocking_match = self.BLOCKING_RE.match(line)
        if idless_blocking_match:
            targets = self._parse_blocking_targets(idless_blocking_match.group("targets"), line_no, path)
            text = idless_blocking_match.group("text").strip()
            if not text:
                self._fail("Empty blocking text", line_no, path)
            return ProductionEntry(
                kind=ProductionEntryKind.BLOCKING,
                text=text,
                line_no=line_no,
                targets=targets,
                leading_comments=leading_comments,
            )

        production_id, body = self._extract_optional_id(line, locked, line_no, path)
        blocking_match = self.BLOCKING_RE.match(body)
        if blocking_match:
            self._fail("Standalone blocking entries must not use explicit production ids", line_no, path)

        label_match = self.LABEL_RE.match(body)
        if label_match:
            label = label_match.group("label")
            text = label_match.group("text").strip()
            if label == "@description":
                return ProductionEntry(
                    ProductionEntryKind.DESCRIPTION,
                    text,
                    line_no,
                    production_id,
                    leading_comments=leading_comments,
                )
            if label == "@direction":
                return ProductionEntry(
                    ProductionEntryKind.DIRECTION,
                    text,
                    line_no,
                    production_id,
                    leading_comments=leading_comments,
                )
            self._fail(f"Unknown reserved entry label: {label}", line_no, path)

        role_match = self.ROLE_RE.match(body)
        if role_match:
            roles = tuple(role.strip() for role in role_match.group("roles").split(","))
            if any(not role for role in roles):
                self._fail("Empty role tag", line_no, path)
            text = role_match.group("text").strip()
            self._validate_inline_directions(text, line_no, path)
            self._validate_inline_blocking(text, line_no, path)
            return ProductionEntry(
                kind=ProductionEntryKind.ROLE,
                text=text,
                line_no=line_no,
                production_id=production_id,
                roles=roles,
                leading_comments=leading_comments,
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
        if self.PRODUCTION_ID_CANDIDATE_RE.match(first):
            self._fail(f"Malformed production id: {first}", line_no, path)
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

    def _validate_inline_blocking(self, text: str, line_no: int, path: Path | None) -> None:
        for match in self.INLINE_BLOCKING_RE.finditer(text):
            self._parse_blocking_targets(match.group("targets").strip(), line_no, path)
            if not match.group("text").strip():
                self._fail("Empty blocking text", line_no, path)

    def _parse_blocking_targets(self, raw_targets: str, line_no: int, path: Path | None) -> tuple[str, ...]:
        targets = tuple(target.strip() for target in raw_targets.split(",") if target.strip())
        if not targets:
            self._fail("Empty blocking target list", line_no, path)
        if "*" in targets and len(targets) > 1:
            self._fail("Blocking wildcard cannot be combined with role targets", line_no, path)
        for target in targets:
            if target == "*":
                continue
            if not re.match(r"^[A-Z][A-Z0-9_ -]*$", target):
                self._fail(f"Malformed blocking target: {target}", line_no, path)
        return targets

    def _fail(self, message: str, line_no: int, path: Path | None) -> None:
        if path is None:
            raise RuntimeError(f"{message} at line {line_no}")
        raise RuntimeError(f"{message} at {paths.display_location(path, line_no)}")
