from __future__ import annotations

import json
from pathlib import Path

from stager.production.recording_workflow_service import RecordingWorkflowService
from stager.linerecorder.role_recordings_importer import RoleRecordingsImportResult
from stager.production_publication.production_publisher import ProductionPublisher
from stager.scriptwright import ProductionPlayLoader
from stager.shared import paths


def test_send_requests_builds_linerecorder_request_with_actor_notes(tmp_path: Path) -> None:
    cfg = _workspace(tmp_path)
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  CAPTAIN:
    actor: phil
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).send_requests()

    assert [request.role for request in result.requests] == ["CAPTAIN"]
    assert result.requests[0].actor == "phil"
    manifest = json.loads((cfg.build_dir / "linerecorder" / "CAPTAIN" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["request"]["notes"] == "Actor: phil"
    assert manifest["items"][0]["id"] == "I-1:s1"


def test_send_requests_skips_whole_role_assignments(tmp_path: Path) -> None:
    cfg = _workspace(tmp_path)
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

    result = RecordingWorkflowService(paths_config=cfg, play=play).send_requests()

    assert result.requests == ()
    assert result.skipped_whole_role_roles == ("CAPTAIN",)
    assert not (cfg.build_dir / "linerecorder" / "CAPTAIN.recording-request.zip").exists()


def test_send_requests_missing_only_selects_missing_segments(tmp_path: Path) -> None:
    cfg = _workspace(tmp_path)
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).send_requests(missing_only=True)

    assert result.requests[0].item_count == 1
    manifest = json.loads((cfg.build_dir / "linerecorder" / "CAPTAIN" / "manifest.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in manifest["items"]] == ["I-1:s1"]
    assert manifest["request"]["kind"] == "missing_segments"


def test_send_requests_changed_only_selects_changed_role_lines(tmp_path: Path) -> None:
    cfg = _workspace(tmp_path)
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace("Stand fast.", "Stand very fast."),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).send_requests(changed_only=True)

    assert result.requests[0].item_count == 1
    manifest = json.loads((cfg.build_dir / "linerecorder" / "CAPTAIN" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["request"]["kind"] == "changed_segments"
    assert manifest["items"][0]["reason"] == "script_changed"


def test_split_recordings_restricts_to_whole_role_roles(tmp_path: Path, monkeypatch) -> None:
    cfg = _workspace(tmp_path)
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
roles:
  CAPTAIN:
    recording: whole-role
""",
        encoding="utf-8",
    )
    calls = []

    class FakeSegmentBuildService:
        def __init__(self, *, paths):
            self.paths = paths

        def build(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        "stager.production.recording_workflow_service.SegmentBuildService",
        FakeSegmentBuildService,
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).split_recordings()

    assert result.roles == ("CAPTAIN",)
    assert calls == [
        {
            "role": "CAPTAIN",
            "silence_thresh": -60,
            "separator_len_ms": 1700,
            "chunk_size": 50,
            "force": False,
        }
    ]


def test_receive_recordings_dispatches_package_import(tmp_path: Path, monkeypatch) -> None:
    cfg = _workspace(tmp_path)
    calls = []

    class FakeRoleRecordingsImporter:
        def __init__(self, *, paths, play):
            calls.append((paths, play))

        def import_package(self, package_path, processing_options):
            calls.append((package_path, processing_options))
            return RoleRecordingsImportResult(
                role="CAPTAIN",
                imported_count=1,
                missing_segment_ids=[],
                complete=True,
                transaction_manifest_path=cfg.build_dir / "recording_imports" / "tx" / "manifest.json",
            )

    monkeypatch.setattr(
        "stager.production.recording_workflow_service.RoleRecordingsImporter",
        FakeRoleRecordingsImporter,
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).receive_recordings(
        package_path=tmp_path / "recordings.zip",
        denoise=True,
        trim_silence=True,
    )

    assert result.imported_count == 1
    assert calls[1][0] == tmp_path / "recordings.zip"
    assert calls[1][1].denoise is True
    assert calls[1][1].trim_silence is True


def test_split_recordings_skips_linerecorder_roles_by_default(tmp_path: Path, monkeypatch) -> None:
    cfg = _workspace(tmp_path)
    calls = []
    monkeypatch.setattr(
        "stager.production.recording_workflow_service.SegmentBuildService",
        lambda **kwargs: calls.append(kwargs),
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    result = RecordingWorkflowService(paths_config=cfg, play=play).split_recordings()

    assert result.roles == ()
    assert result.skipped_linerecorder_roles == ("CAPTAIN",)
    assert calls == []


def _workspace(root: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=root / "src",
        build_root=root / "build",
        plays_dir=root / "plays",
        snippets_dir=root / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 CAPTAIN: Stand fast.
""",
        encoding="utf-8",
    )
    (cfg.play_dir / "source_text_metadata.yaml").write_text("title: Test Play\n", encoding="utf-8")
    (cfg.play_dir / "reading_metadata.yaml").write_text("reading_type: solo\n", encoding="utf-8")
    return cfg
