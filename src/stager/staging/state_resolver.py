from __future__ import annotations

from dataclasses import dataclass, replace

from stager.staging.diagnostics import StagingDiagnostic
from stager.staging.model import Placement, SceneSnapshot, StagingDocument
from stager.staging.resolver import StagingResolver


@dataclass
class StagingStateResolver:
    def resolve_beat(self, document: StagingDocument, scene_id: str, beat_id: str):
        diagnostics = list(document.diagnostics)
        snapshot = document.snapshots.get(scene_id)
        state: dict[str, Placement] = {}
        if snapshot is None:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown scene snapshot {scene_id!r}"))
        else:
            for placement in snapshot.placements:
                state[placement.entity] = placement

        found_target = False
        scene_beats = [beat for beat in document.beats if beat.scene_id == scene_id]
        target_index = None
        for index, beat in enumerate(scene_beats):
            is_target_beat = beat.beat_id == beat_id
            for placement in beat.placements:
                if is_target_beat:
                    state[placement.entity] = self._with_origin(placement, state.get(placement.entity))
                else:
                    state[placement.entity] = self._without_origin(placement)
            if is_target_beat:
                found_target = True
                target_index = index
                break

        if not found_target:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown beat {beat_id!r} for scene {scene_id!r}"))
        elif target_index is not None and target_index + 1 < len(scene_beats):
            self._apply_next_movements(state, scene_beats[target_index + 1].placements)

        effective_document = replace(
            document,
            snapshots={
                **document.snapshots,
                scene_id: SceneSnapshot(
                    scene_id=scene_id,
                    set_id=snapshot.set_id if snapshot is not None else "default",
                    placements=tuple(state.values()),
                    line_no=snapshot.line_no if snapshot is not None else None,
                ),
            },
            diagnostics=tuple(diagnostics),
        )
        resolved = StagingResolver().resolve_snapshot(effective_document, scene_id)
        return replace(resolved, scene_id=f"{scene_id}@{beat_id}")

    def _with_origin(self, placement: Placement, previous: Placement | None) -> Placement:
        if placement.offstage or placement.origin is not None:
            return placement
        if previous is None or previous.location is None:
            return placement
        return replace(placement, origin=previous.location)

    def _without_origin(self, placement: Placement) -> Placement:
        if placement.origin is None:
            return placement
        return replace(placement, origin=None)

    def _apply_next_movements(self, state: dict[str, Placement], next_placements: tuple[Placement, ...]) -> None:
        for next_placement in next_placements:
            if next_placement.offstage or next_placement.location is None:
                continue
            current = state.get(next_placement.entity)
            if current is None or current.offstage or current.location is None:
                continue
            if current.location.source == next_placement.location.source:
                continue
            state[next_placement.entity] = replace(current, next_location=next_placement.location)
