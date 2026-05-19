from __future__ import annotations

from dataclasses import dataclass

from stager.production.production_status import ProductionStatus


@dataclass(frozen=True)
class ProductionRecommendation:
    action: str
    reason: str
    command: str


class ProductionRecommendationService:
    def recommend(self, *, status: ProductionStatus, play_id: str) -> ProductionRecommendation:
        if status.has_unpublished_changes:
            return ProductionRecommendation(
                action="publish",
                reason="production.md has unpublished changes",
                command=f"quince publish --play {play_id}",
            )
        if status.unassigned_roles:
            return ProductionRecommendation(
                action="cast",
                reason="some roles are not assigned",
                command=f"quince cast show --play {play_id}",
            )
        if status.missing_source_recording_roles:
            role = status.missing_source_recording_roles[0]
            return ProductionRecommendation(
                action="record whole role",
                reason=f"{role} is configured for whole-role recording and has no source recording",
                command=f"add a source recording for {role}, then run quince split-recordings --role {role} --play {play_id}",
            )
        if status.missing_recording_count:
            return ProductionRecommendation(
                action="send requests",
                reason="some canonical segment recordings are missing; send requests or import returned recordings",
                command=f"quince send-requests --play {play_id}",
            )
        if status.stale_recording_count:
            return ProductionRecommendation(
                action="refresh recordings",
                reason="some imported recordings were made against older segment text",
                command=f"quince send-requests --play {play_id}",
            )
        if status.cleanup_review.exists and not status.cleanup_review.complete:
            return ProductionRecommendation(
                action="render cleanup",
                reason="a cleanup review exists but does not cover every required segment",
                command=f"quince prepare-audio --play {play_id}",
            )
        if status.voice_profiles.configured_profiles and not status.voice_profiles.complete:
            return ProductionRecommendation(
                action="render voice profiles",
                reason="voice-profile audio is configured but not fully rendered",
                command=f"quince prepare-audio --play {play_id}",
            )
        if status.blocking_changes:
            return ProductionRecommendation(
                action="build playbook",
                reason="blocking changes need a refreshed Playbook",
                command=f"quince build-playbook --play {play_id}",
            )
        if status.playbook.exists and status.playbook.matches_current_published_version is False:
            return ProductionRecommendation(
                action="build playbook",
                reason="the current Playbook does not match the published production version",
                command=f"quince build-playbook --play {play_id}",
            )
        if not status.playbook.exists:
            return ProductionRecommendation(
                action="build playbook",
                reason="no Playbook has been built",
                command=f"quince build-playbook --play {play_id}",
            )
        return ProductionRecommendation(
            action="ready",
            reason="no immediate blocking action was found",
            command=f"quince status --play {play_id}",
        )
