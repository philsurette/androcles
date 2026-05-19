from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from stager.cli import build
from stager.production.production_recommendation import ProductionRecommendationService
from stager.production.production_status import ProductionStatusService
from stager.production_publication.production_publisher import ProductionPublisher
from stager.scriptwright import ProductionPlayLoader, ScriptWright
from stager.shared import paths


def test_production_status_reports_cast_and_segment_coverage(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  CAPTAIN:
    actor: phil
    recording: whole-role
    voice_profile: phil@CAPTAIN
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    segment_id = next(segment_id for ids in play.getRole("CAPTAIN").segments().values() for segment_id in ids)
    segment_path = cfg.segments_dir / "CAPTAIN" / f"{segment_id}.wav"
    segment_path.parent.mkdir(parents=True, exist_ok=True)
    segment_path.write_bytes(b"wav")
    cfg.recordings_dir.mkdir(parents=True, exist_ok=True)
    (cfg.recordings_dir / "CAPTAIN.wav").write_bytes(b"whole-role")

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.cast_configured is True
    assert status.roles[0].role == "CAPTAIN"
    assert status.roles[0].actor == "phil"
    assert status.roles[0].recording == "whole-role"
    assert status.roles[0].voice_profile == "phil@CAPTAIN"
    assert status.roles[0].recorded_segments == 1
    assert status.roles[0].missing_segments == ()
    assert status.roles[0].source_recording_exists is True


def test_production_status_reports_missing_whole_role_sources_separately(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  CAPTAIN:
    actor: phil
    recording: whole-role
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.missing_source_recording_roles == ("CAPTAIN",)
    _patch_path_config(monkeypatch, cfg)
    result = CliRunner().invoke(build.app, ["production-status", "--play", "test"])
    assert result.exit_code == 0
    assert "Missing segment recordings: 1" in result.output
    assert "Missing whole-role source recordings: CAPTAIN" in result.output


def test_production_status_cli_renders_basic_readiness(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["production-status", "--play", "test"])

    assert result.exit_code == 0
    assert "Production status for test: Untitled" in result.output
    assert "Cast config: missing" in result.output
    assert "CAPTAIN: unassigned, linerecorder, 0/1 segments, 1 missing" in result.output
    assert "Unassigned roles: CAPTAIN" in result.output
    assert "Missing segment recordings: 1" in result.output
    assert "Playbook:" in result.output
    assert "exists: no" in result.output
    assert "Next:" in result.output
    assert "action: publish" in result.output


def test_production_status_rejects_cast_roles_that_are_not_in_the_play(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  GHOST:
    actor: phil
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    try:
        ProductionStatusService(paths_config=cfg, play=play).build()
    except RuntimeError as exc:
        assert "unknown rehearsable role(s): GHOST" in str(exc)
    else:
        raise AssertionError("Expected unknown cast role to fail")


def test_production_status_reports_playbook_version_freshness(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    published = ProductionPublisher(paths_config=cfg).publish(change_summary="Initial")
    (cfg.build_dir / "app").mkdir(parents=True, exist_ok=True)
    (cfg.build_dir / "app" / "manifest.json").write_text(
        json.dumps(
            {
                "production": {
                    "source": "published",
                    "version": str(published.version.production_version),
                },
                "build": {
                    "buildId": "build-1",
                    "buildTimestamp": "2026-05-18T12:00:00Z",
                },
            }
        ),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.current_published_version == str(published.version.production_version)
    assert status.playbook.exists is True
    assert status.playbook.production_version == str(published.version.production_version)
    assert status.playbook.build_id == "build-1"
    assert status.playbook.matches_current_published_version is True


def test_production_status_reports_audioplay_version_freshness(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    published = ProductionPublisher(paths_config=cfg).publish(change_summary="Initial")
    cfg.audio_play_dir.mkdir(parents=True, exist_ok=True)
    (cfg.audio_play_dir / "audioplay_manifest.json").write_text(
        json.dumps(
            {
                "build": {
                    "buildTimestamp": "2026-05-18T12:00:00Z",
                },
                "production": {
                    "source": "published",
                    "version": str(published.version.production_version),
                },
                "options": {
                    "audioFormat": "mp4",
                    "audioSource": "cleaned",
                },
            }
        ),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.audioplay.exists is True
    assert status.audioplay.production_version == str(published.version.production_version)
    assert status.audioplay.build_timestamp == "2026-05-18T12:00:00Z"
    assert status.audioplay.audio_format == "mp4"
    assert status.audioplay.audio_source == "cleaned"
    assert status.audioplay.matches_current_published_version is True


def test_production_status_reports_unpublished_blocking_changes(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# P-0 PROLOGUE
P-1 CAPTAIN: Stand fast.
/CAPTAIN: Cross left.
""",
        encoding="utf-8",
    )
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace("Cross left", "Cross right"),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.blocking_changes == ("P-1:b1",)
    _patch_path_config(monkeypatch, cfg)
    result = CliRunner().invoke(build.app, ["production-status", "--play", "test", "--production-source", "working"])
    assert result.exit_code == 0
    assert "Blocking changes needing Playbook rebuild: 1" in result.output
    assert "P-1:b1" in result.output


def test_production_status_reports_stale_imported_recordings(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial")
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil: {}
roles:
  CAPTAIN:
    actor: phil
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    role = play.getRole("CAPTAIN")
    segment_id = next(segment_id for ids in role.segments().values() for segment_id in ids)
    current_hash = next(segment.content_hash for block in role.blocks for segment in block.segments if segment.content_hash)
    segment_path = cfg.segments_dir / "CAPTAIN" / f"{segment_id}.wav"
    segment_path.parent.mkdir(parents=True, exist_ok=True)
    segment_path.write_bytes(b"wav")
    transaction_dir = cfg.build_dir / "linerecorder" / "imports" / "20260519T120000Z"
    transaction_dir.mkdir(parents=True, exist_ok=True)
    (transaction_dir / "import.json").write_text(
        json.dumps(
            {
                "imported": [
                    {
                        "target_path": f"CAPTAIN/{segment_id}.wav",
                        "segment_content_hash": current_hash + "-old",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.stale_recording_count == 1
    assert status.roles[0].stale_segments == (segment_id,)
    recommendation = ProductionRecommendationService().recommend(status=status, play_id="test")
    assert recommendation.action == "refresh recordings"


def test_production_status_reports_cleanup_review_coverage(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    play = ProductionPlayLoader(paths_config=cfg).load()
    segment_id = next(segment_id for ids in play.getRole("CAPTAIN").segments().values() for segment_id in ids)
    cleaned_path = cfg.audio_out_dir / "cleaned" / "CAPTAIN" / f"{segment_id}.wav"
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_path.write_bytes(b"cleaned")
    review_path = cfg.audio_out_dir / "cleaned" / "cleanup_review.json"
    review_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "role": "CAPTAIN",
                        "segment_id": segment_id,
                        "output_path": str(cleaned_path),
                        "warnings": ["end_moved"],
                        "fallback": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = ProductionStatusService(paths_config=cfg, play=play).build()

    assert status.cleanup_review.exists is True
    assert status.cleanup_review.complete is True
    assert status.cleanup_review.reviewed_segments == 1
    assert status.cleanup_review.warning_count == 1
    assert status.cleanup_review.fallback_count == 1


def test_production_status_reports_voice_profile_render_coverage(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "voice_profiles.yaml").write_text(
        """
version: 1
actors:
  phil: {}
role_targets:
  CAPTAIN: {}
cast_profiles:
  phil@CAPTAIN:
    actor: phil
    role: CAPTAIN
    mode: explicit
    transforms:
      - type: gain
        params:
          db: 1
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    segment_id = next(segment_id for ids in play.getRole("CAPTAIN").segments().values() for segment_id in ids)

    status = ProductionStatusService(paths_config=cfg, play=play).build()
    assert status.voice_profiles.configured_profiles == 1
    assert status.voice_profiles.expected_segments == 1
    assert status.voice_profiles.rendered_segments == 0
    assert status.voice_profiles.missing_segments == (f"phil@CAPTAIN/{segment_id}",)

    rendered_path = cfg.audio_out_dir / "rendered" / "phil@CAPTAIN-cache" / "CAPTAIN" / f"{segment_id}.wav"
    rendered_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_path.write_bytes(b"rendered")
    (rendered_path.parents[1] / "manifest.json").write_text(
        json.dumps(
            {
                "actor": "phil",
                "role": "CAPTAIN",
                "segments": [
                    {
                        "segment_id": segment_id,
                        "output_path": str(rendered_path),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = ProductionStatusService(paths_config=cfg, play=play).build()
    assert status.voice_profiles.complete is True
    assert status.voice_profiles.rendered_segments == 1


def test_production_status_rejects_unknown_cast_voice_profile(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil: {}
roles:
  CAPTAIN:
    actor: phil
    voice_profile: phil@CAPTAIN
""",
        encoding="utf-8",
    )
    (cfg.play_dir / "voice_profiles.yaml").write_text(
        """
version: 1
actors:
  phil: {}
role_targets:
  CAPTAIN: {}
cast_profiles: {}
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    try:
        ProductionStatusService(paths_config=cfg, play=play).build()
    except RuntimeError as exc:
        assert "unknown voice profile(s): phil@CAPTAIN" in str(exc)
    else:
        raise AssertionError("Expected unknown voice profile to fail")


def test_production_status_cli_can_render_yaml(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    ScriptWright(paths_config=cfg).write_locked()
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["production-status", "--play", "test", "--format", "yaml"])

    assert result.exit_code == 0
    assert "play_id: test" in result.output
    assert "missing_recording_count: 1" in result.output
    assert "roles:" in result.output
    assert "playbook:" in result.output


def _config(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.
""",
        encoding="utf-8",
    )
    return cfg


def _patch_path_config(monkeypatch, cfg: paths.PathConfig) -> None:
    monkeypatch.setattr(build.paths, "PathConfig", lambda play_name: cfg)
