from __future__ import annotations

from dataclasses import dataclass
import re

from stager.production_publication.published_line import PublishedLine
from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change import ProductionChange
from stager.production_publication.production_change_report import ProductionChangeReport


@dataclass
class ProductionChangeAnalyzer:
    def analyze(
        self,
        *,
        previous: PublishedVersion | None,
        current_lines: tuple[PublishedLine, ...],
    ) -> ProductionChangeReport:
        if previous is None:
            return ProductionChangeReport(
                base_version=None,
                changes=tuple(
                    ProductionChange(kind="added", line_id=line.id, current=line)
                    for line in current_lines
                ),
            )

        previous_by_id = {line.id: line for line in previous.lines}
        current_by_id = {line.id: line for line in current_lines}
        all_ids = {line.id for line in previous.lines} | {line.id for line in current_lines}
        changes: list[ProductionChange] = []
        used_ids = set(all_ids)
        for line_id in sorted(all_ids):
            old_line = previous_by_id.get(line_id)
            new_line = current_by_id.get(line_id)
            if old_line is None and new_line is not None:
                changes.append(ProductionChange(kind="added", line_id=line_id, current=new_line))
                continue
            if old_line is not None and new_line is None:
                changes.append(ProductionChange(kind="removed", line_id=line_id, previous=old_line))
                continue
            if old_line is None or new_line is None:
                continue
            if self._recording_hash(old_line) != self._recording_hash(new_line):
                changes.append(
                    ProductionChange(
                        kind="changed_id_reuse",
                        line_id=line_id,
                        previous=old_line,
                        current=new_line,
                        recommended_id=self._next_revision_id(line_id, used_ids),
                    )
                )
                used_ids.add(changes[-1].recommended_id or line_id)
            elif old_line.content_hash != new_line.content_hash:
                changes.append(
                    ProductionChange(
                        kind="context_changed",
                        line_id=line_id,
                        previous=old_line,
                        current=new_line,
                    )
                )
        return ProductionChangeReport(base_version=previous.version, changes=tuple(changes))

    def _recording_hash(self, line: PublishedLine) -> str:
        return line.speech_hash or line.content_hash

    def _next_revision_id(self, production_id: str, used_ids: set[str]) -> str:
        base_id, current_suffix = self._revision_base(production_id)
        suffix_ordinals = [ord(current_suffix) - ord("a") + 1] if current_suffix else [0]
        for candidate in used_ids:
            candidate_base, candidate_suffix = self._revision_base(candidate)
            if candidate_base == base_id and candidate_suffix is not None:
                suffix_ordinals.append(ord(candidate_suffix) - ord("a") + 1)
        next_ordinal = max(suffix_ordinals) + 1
        if next_ordinal > 26:
            raise RuntimeError(f"Cannot recommend revision id after z for {production_id}")
        return f"{base_id}{chr(ord('a') + next_ordinal - 1)}"

    def _revision_base(self, production_id: str) -> tuple[str, str | None]:
        match = re.match(r"^(?P<base>.+?)(?P<revision>[a-z])?$", production_id)
        if match is None:
            raise RuntimeError(f"Malformed production id: {production_id}")
        return match.group("base"), match.group("revision")
