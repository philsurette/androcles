from __future__ import annotations

from dataclasses import dataclass

from stager.production_publication.production_change import ProductionChange


@dataclass(frozen=True)
class ProductionChangeReport:
    base_version: int | None
    changes: tuple[ProductionChange, ...]

    @property
    def changed_id_reuse(self) -> tuple[ProductionChange, ...]:
        return tuple(change for change in self.changes if change.kind == "changed_id_reuse")

    @property
    def added(self) -> tuple[ProductionChange, ...]:
        return tuple(change for change in self.changes if change.kind == "added")

    @property
    def removed(self) -> tuple[ProductionChange, ...]:
        return tuple(change for change in self.changes if change.kind == "removed")

    @property
    def changed_or_added_role_line_ids(self) -> set[str]:
        ids: set[str] = set()
        for change in self.added:
            if change.current is not None and change.current.roles:
                ids.add(change.current.id)
        for change in self.changed_id_reuse:
            if change.current is not None and change.current.roles:
                ids.add(change.recommended_id or change.current.id)
        return ids

    def to_dict(self) -> dict:
        return {
            "base_version": self.base_version,
            "changes": [change.to_dict() for change in self.changes],
        }
