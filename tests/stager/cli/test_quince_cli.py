from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from stager.cli.quince import app
from stager.production_publication.production_publisher import ProductionPublisher
from stager.shared import paths


def test_quince_help_does_not_require_workspace() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Producer workflow CLI" in result.output


def test_quince_status_help_does_not_require_workspace() -> None:
    result = CliRunner().invoke(app, ["status", "--help"])

    assert result.exit_code == 0
    assert "Show production, cast, recording, and Playbook readiness" in result.output


def test_quince_list_shows_workspace_productions(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles", "hamlet")

    result = CliRunner().invoke(app, ["list", "--workspace", tmp_path.as_posix()])

    assert result.exit_code == 0
    assert "androcles" in result.output
    assert "hamlet" in result.output


def test_quince_use_writes_active_play(tmp_path: Path) -> None:
    _workspace(tmp_path, "androcles")

    result = CliRunner().invoke(app, ["use", "androcles", "--workspace", tmp_path.as_posix()])

    assert result.exit_code == 0
    assert "Active production: androcles" in result.output
    assert "active_play: androcles" in (tmp_path / "quince.yaml").read_text(encoding="utf-8")


def test_quince_status_infers_play_from_current_directory(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["status", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["context"]["play_id"] == "androcles"
    assert data["context"]["selection_source"] == "play-directory"
    assert data["status"]["play_id"] == "androcles"


def test_quince_status_rejects_ambiguous_workspace(tmp_path: Path, monkeypatch) -> None:
    _scriptwright_workspace(tmp_path, "androcles")
    _scriptwright_workspace(tmp_path, "hamlet")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code != 0
    assert "Multiple productions found" in result.output


def test_quince_next_recommends_publish_for_unpublished_changes(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["next"])

    assert result.exit_code == 0
    assert "Next: publish" in result.output
    assert "quince publish --play androcles" in result.output


def test_quince_changes_shows_current_diff(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["changes"])

    assert result.exit_code == 0
    assert "Current published production: none" in result.output
    assert "Working source has unpublished changes: yes" in result.output
    assert "No prior published production version." in result.output


def test_quince_publish_requires_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish"], input="\n")

    assert result.exit_code != 0
    assert "Publishing requires --change-summary or --allow-empty-summary" in result.output


def test_quince_publish_prompts_for_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish"], input="Prompted summary.\n")

    assert result.exit_code == 0
    assert "Change summary" in result.output
    assert "Published production" in result.output
    assert "// production_note: Prompted summary." in cfg.production_markdown.read_text(encoding="utf-8")


def test_quince_publish_writes_new_production_version(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish", "--change-summary", "Initial publish."])

    assert result.exit_code == 0
    assert "Published production" in result.output
    assert "// production_version:" in cfg.production_markdown.read_text(encoding="utf-8")


def test_quince_changes_groups_changed_speech_and_blocking(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace(
            "I-1 CAPTAIN: Stand fast.",
            "I-1 CAPTAIN: Stand very fast.\n/CAPTAIN: Cross left.",
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["changes"])

    assert result.exit_code == 0
    assert "Needs recording:" in result.output
    assert "changed speech under reused id: I-1 -> I-1a" in result.output
    assert "Blocking only:" in result.output


def test_quince_publish_reports_id_reuse_error_in_producer_terms(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace("Stand fast.", "Stand very fast."),
        encoding="utf-8",
    )
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish", "--change-summary", "Changed line."])

    assert result.exit_code != 0
    assert "Changed production ids were reused" in result.output
    assert "I-1 -> I-1a" in result.output


def test_quince_publish_can_apply_id_updates_for_speech_change(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace("Stand fast.", "Stand very fast."),
        encoding="utf-8",
    )
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(
        app,
        ["publish", "--apply-id-updates", "--change-summary", "Changed line."],
    )

    assert result.exit_code == 0
    assert "Rewrote changed spoken lines to fresh production ids:" in result.output
    assert "I-1 -> I-1a" in result.output
    assert "I-1a CAPTAIN: Stand very fast." in cfg.production_markdown.read_text(encoding="utf-8")


def test_quince_publish_allows_blocking_only_change(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8") + "/CAPTAIN: Cross left.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["publish", "--change-summary", "Blocking note."])

    assert result.exit_code == 0
    assert "Blocking only:" in result.output
    assert "Published production" in result.output


def test_quince_cast_show_reports_unassigned_roles(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["cast", "show"])

    assert result.exit_code == 0
    assert "Cast:" in result.output
    assert "Unassigned roles: CAPTAIN" in result.output


def test_quince_cast_assign_writes_cast_yaml(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["cast", "assign", "CAPTAIN", "phil"])

    assert result.exit_code == 0
    assert "Assigned phil to CAPTAIN." in result.output
    text = (cfg.play_dir / "cast.yaml").read_text(encoding="utf-8")
    assert "phil:" in text
    assert "CAPTAIN:" in text


def test_quince_cast_assign_rejects_unknown_role(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["cast", "assign", "GHOST", "phil"])

    assert result.exit_code != 0
    assert "Unknown rehearsable role: GHOST" in result.output


def test_quince_send_requests_builds_recording_request(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["send-requests", "--role", "CAPTAIN"])

    assert result.exit_code == 0
    assert "Generated Recording Requests:" in result.output
    assert "CAPTAIN: 1 items, full_role" in result.output
    assert (cfg.build_dir / "linerecorder" / "CAPTAIN.recording-request.zip").exists()


def test_quince_send_requests_reports_skipped_whole_role(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
roles:
  CAPTAIN:
    recording: whole-role
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["send-requests"])

    assert result.exit_code == 0
    assert "No Recording Requests generated." in result.output
    assert "Skipped whole-role roles: CAPTAIN" in result.output


def test_quince_split_recordings_dispatches_whole_role_roles(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
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
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["split-recordings"])

    assert result.exit_code == 0
    assert "Split recordings for: CAPTAIN" in result.output
    assert calls[0]["role"] == "CAPTAIN"


def test_quince_prepare_audio_dry_run_reports_readiness(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    class FakeAudioOutputWorkflowService:
        def __init__(self, *, paths_config, play):
            self.paths_config = paths_config
            self.play = play

        def prepare_audio(self, **kwargs):
            assert kwargs["run"] is False
            return SimpleNamespace(
                dry_run=True,
                status=SimpleNamespace(missing_recording_count=1),
                cleanup_plan=SimpleNamespace(entries=(object(),)),
                cleanup_analysis=None,
                prepared_batches=(),
                rendered_batches=(),
                voice_profile_count=0,
                voice_results=(),
            )

    monkeypatch.setattr("stager.cli.quince.AudioOutputWorkflowService", FakeAudioOutputWorkflowService)

    result = CliRunner().invoke(app, ["prepare-audio", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run audio preparation." in result.output
    assert "Missing canonical segment recordings: 1" in result.output


def test_quince_build_playbook_rejects_working_source_without_confirmation(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    monkeypatch.chdir(cfg.play_dir)

    result = CliRunner().invoke(app, ["build-playbook"])

    assert result.exit_code != 0
    assert "Building from working production.md requires --allow-working-source" in result.output


def test_quince_build_playbook_reports_output_path(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    monkeypatch.chdir(cfg.play_dir)

    class FakeAudioOutputWorkflowService:
        def __init__(self, *, paths_config, play):
            self.paths_config = paths_config
            self.play = play

        def build_playbook(self, **kwargs):
            assert kwargs["audio_format"] == "wav"
            assert kwargs["staging"] is True
            assert kwargs["blocking_diagrams"] is True
            return SimpleNamespace(
                paths=(cfg.build_dir / "androcles.playbook.zip",),
                production_version="1@test",
                production_source="published",
                audio_source=kwargs["audio_source"],
            )

    monkeypatch.setattr("stager.cli.quince.AudioOutputWorkflowService", FakeAudioOutputWorkflowService)

    result = CliRunner().invoke(app, ["build-playbook"])

    assert result.exit_code == 0
    assert "Built Playbook from published source." in result.output
    assert "build/androcles/androcles.playbook.zip" in result.output


def test_quince_build_playbook_can_skip_staging_export(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    monkeypatch.chdir(cfg.play_dir)

    class FakeAudioOutputWorkflowService:
        def __init__(self, *, paths_config, play):
            self.paths_config = paths_config
            self.play = play

        def build_playbook(self, **kwargs):
            assert kwargs["staging"] is False
            assert kwargs["blocking_diagrams"] is True
            return SimpleNamespace(
                paths=(cfg.build_dir / "androcles.playbook.zip",),
                production_version="1@test",
                production_source="published",
                audio_source=kwargs["audio_source"],
            )

    monkeypatch.setattr("stager.cli.quince.AudioOutputWorkflowService", FakeAudioOutputWorkflowService)

    result = CliRunner().invoke(app, ["build-playbook", "--no-staging"])

    assert result.exit_code == 0
    assert "Built Playbook from published source." in result.output


def test_quince_build_playbook_can_skip_blocking_diagrams(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    monkeypatch.chdir(cfg.play_dir)

    class FakeAudioOutputWorkflowService:
        def __init__(self, *, paths_config, play):
            self.paths_config = paths_config
            self.play = play

        def build_playbook(self, **kwargs):
            assert kwargs["staging"] is True
            assert kwargs["blocking_diagrams"] is False
            return SimpleNamespace(
                paths=(cfg.build_dir / "androcles.playbook.zip",),
                production_version="1@test",
                production_source="published",
                audio_source=kwargs["audio_source"],
            )

    monkeypatch.setattr("stager.cli.quince.AudioOutputWorkflowService", FakeAudioOutputWorkflowService)

    result = CliRunner().invoke(app, ["build-playbook", "--no-blocking-diagrams"])

    assert result.exit_code == 0
    assert "Built Playbook from published source." in result.output


def test_quince_build_audioplay_reports_output_path(tmp_path: Path, monkeypatch) -> None:
    cfg = _scriptwright_workspace(tmp_path, "androcles")
    ProductionPublisher(paths_config=cfg).publish(change_summary="Initial.")
    monkeypatch.chdir(cfg.play_dir)

    class FakeAudioOutputWorkflowService:
        def __init__(self, *, paths_config, play):
            self.paths_config = paths_config
            self.play = play

        def build_audioplay(self, **kwargs):
            assert kwargs["audio_format"] == "mp3"
            return SimpleNamespace(
                paths=(cfg.build_dir / "audio" / "androcles.mp3",),
                production_version="1@test",
                production_source=None,
                audio_source=kwargs["audio_source"],
            )

    monkeypatch.setattr("stager.cli.quince.AudioOutputWorkflowService", FakeAudioOutputWorkflowService)

    result = CliRunner().invoke(app, ["build-audioplay", "--audio-format", "mp3"])

    assert result.exit_code == 0
    assert "Built audioplay from published source." in result.output
    assert "build/androcles/audio/androcles.mp3" in result.output


def _workspace(root: Path, *play_ids: str) -> None:
    (root / "plays").mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    for play_id in play_ids:
        (root / "plays" / play_id).mkdir(parents=True, exist_ok=True)


def _scriptwright_workspace(root: Path, play_id: str) -> paths.PathConfig:
    _workspace(root, play_id)
    cfg = paths.PathConfig(
        play_name=play_id,
        root=root / "src",
        build_root=root / "build",
        plays_dir=root / "plays",
        snippets_dir=root / "snippets",
    )
    cfg.play_text.write_text(
        """## 1: ACT I ##

CAPTAIN.
Stand fast.
""",
        encoding="utf-8",
    )
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
