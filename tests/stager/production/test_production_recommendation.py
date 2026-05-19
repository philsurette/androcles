from __future__ import annotations

from stager.production.production_recommendation import ProductionRecommendationService
from stager.production.production_status import (
    CleanupReviewProductionStatus,
    PlaybookProductionStatus,
    ProductionStatus,
    RoleProductionStatus,
    VoiceProfileProductionStatus,
)


def test_recommendation_prefers_publish_for_unpublished_changes() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(has_unpublished_changes=True, roles=(_role(),)),
        play_id="androcles",
    )

    assert recommendation.action == "publish"
    assert recommendation.command == "quince publish --play androcles"


def test_recommendation_reports_unassigned_roles_before_missing_recordings() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(roles=(_role(actor=None, missing_segments=("0_1_1",)),)),
        play_id="androcles",
    )

    assert recommendation.action == "cast"
    assert recommendation.command == "quince cast show --play androcles"


def test_recommendation_reports_whole_role_source_before_segment_requests() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(
            roles=(
                _role(
                    recording="whole-role",
                    missing_segments=("0_1_1",),
                    source_recording_exists=False,
                ),
            )
        ),
        play_id="androcles",
    )

    assert recommendation.action == "record whole role"
    assert "split-recordings --role CAPTAIN --play androcles" in recommendation.command


def test_recommendation_reports_missing_segments() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(roles=(_role(missing_segments=("0_1_1",)),)),
        play_id="androcles",
    )

    assert recommendation.action == "send requests"
    assert recommendation.command == "quince send-requests --play androcles"


def test_recommendation_reports_stale_playbook() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(
            roles=(_role(),),
            playbook=PlaybookProductionStatus(
                exists=True,
                production_version="1@old",
                matches_current_published_version=False,
            ),
        ),
        play_id="androcles",
    )

    assert recommendation.action == "build playbook"
    assert recommendation.reason == "the current Playbook does not match the published production version"


def test_recommendation_reports_ready_when_no_action_needed() -> None:
    recommendation = ProductionRecommendationService().recommend(
        status=_status(
            roles=(_role(),),
            playbook=PlaybookProductionStatus(
                exists=True,
                production_version="1@current",
                matches_current_published_version=True,
            ),
        ),
        play_id="androcles",
    )

    assert recommendation.action == "ready"


def _status(
    *,
    has_unpublished_changes: bool = False,
    roles: tuple[RoleProductionStatus, ...],
    playbook: PlaybookProductionStatus | None = None,
) -> ProductionStatus:
    return ProductionStatus(
        play_id="androcles",
        play_title="Androcles",
        current_published_version="1@current",
        working_production_version="1@current",
        has_unpublished_changes=has_unpublished_changes,
        roles=roles,
        cast_configured=True,
        playbook=playbook or PlaybookProductionStatus(exists=False),
        cleanup_review=CleanupReviewProductionStatus(exists=False, expected_segments=sum(role.expected_segments for role in roles)),
        voice_profiles=VoiceProfileProductionStatus(configured_profiles=0, expected_segments=0, rendered_segments=0),
    )


def _role(
    *,
    actor: str | None = "phil",
    recording: str = "linerecorder",
    missing_segments: tuple[str, ...] = (),
    source_recording_exists: bool | None = None,
) -> RoleProductionStatus:
    return RoleProductionStatus(
        role="CAPTAIN",
        actor=actor,
        recording=recording,
        expected_segments=1,
        recorded_segments=0 if missing_segments else 1,
        missing_segments=missing_segments,
        source_recording_exists=source_recording_exists,
    )
