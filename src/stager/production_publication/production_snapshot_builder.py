from __future__ import annotations

from dataclasses import dataclass, field

from stager.scriptwright.content_hasher import ContentHasher
from stager.scriptwright.production_script import ProductionEntry, ProductionEntryKind, ProductionScript
from stager.production_publication.published_line import PublishedLine


@dataclass
class ProductionSnapshotBuilder:
    content_hasher: ContentHasher = field(default_factory=ContentHasher)

    def build_lines(self, production: ProductionScript) -> tuple[PublishedLine, ...]:
        lines: list[PublishedLine] = []
        for entry in production.entries:
            if entry.production_id is None:
                raise RuntimeError(f"Production entry at line {entry.line_no} is missing an id")
            lines.append(self._line_for_entry(entry))
        return tuple(lines)

    def _line_for_entry(self, entry: ProductionEntry) -> PublishedLine:
        return PublishedLine(
            id=entry.production_id or "",
            kind=entry.kind.value,
            text=entry.text,
            line_no=entry.line_no,
            content_hash=self.content_hasher.hash_line(entry.kind.value, entry.text, entry.roles or entry.targets),
            roles=tuple(entry.roles),
            targets=tuple(entry.targets),
            speech_hash=self._speech_hash(entry),
            context_hash=self._context_hash(entry),
        )

    def _speech_hash(self, entry: ProductionEntry) -> str | None:
        if entry.kind != ProductionEntryKind.ROLE:
            return None
        return self.content_hasher.hash_speech_line(entry.text, entry.roles)

    def _context_hash(self, entry: ProductionEntry) -> str | None:
        if entry.kind in (ProductionEntryKind.DIRECTION, ProductionEntryKind.BLOCKING):
            return self.content_hasher.hash_line(entry.kind.value, entry.text, entry.targets)
        if entry.kind == ProductionEntryKind.ROLE:
            return self.content_hasher.hash_context_line(entry.text)
        return None
