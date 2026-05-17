from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from stager.production_publication.production_publisher import ProductionPublisher
from stager.production_publication.production_source_resolver import ProductionSourceResolver
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.shared.paths import PathConfig


def _cfg(tmp_path: Path) -> PathConfig:
    play_dir = tmp_path / "plays" / "test-play"
    play_dir.mkdir(parents=True)
    return PathConfig(
        "test-play",
        plays_dir=tmp_path / "plays",
        build_root=tmp_path / "build",
        snippets_dir=tmp_path / "snippets",
    )


def _write_production(cfg: PathConfig, body: str) -> None:
    cfg.production_markdown.write_text(
        f"""// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

{body}
""",
        encoding="utf-8",
    )


class _PublicationIds:
    def __init__(self, *ids: str) -> None:
        self.ids = list(ids)

    def generate(self) -> str:
        return self.ids.pop(0)


def _publisher(cfg: PathConfig, *ids: str) -> ProductionPublisher:
    return ProductionPublisher(cfg, publication_id_generator=_PublicationIds(*ids or ("k9f4p2x8m1qd",)))


def test_publish_creates_initial_managed_version(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )

    result = _publisher(cfg, "k9f4p2x8m1qd").publish(change_summary="Initial publish.")

    assert result.version.label == "1@k9f4p2x8m1qd"
    assert result.change_report.base_version is None
    assert (cfg.build_dir / "production-history" / "versions" / "0001-k9f4p2x8m1qd" / "production.md").exists()
    current = json.loads((cfg.build_dir / "production-history" / "current.json").read_text(encoding="utf-8"))
    assert current["sequence"] == 1
    assert current["production_version"] == "1@k9f4p2x8m1qd"
    assert current["parent_production_version"] is None
    assert current["change_summary"] == "Initial publish."
    manifest = json.loads(
        (cfg.build_dir / "production-history" / "versions" / "0001-k9f4p2x8m1qd" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["change_summary"] == "Initial publish."
    production_text = cfg.production_markdown.read_text(encoding="utf-8")
    assert "// production_version: 1@k9f4p2x8m1qd" in production_text
    assert "// parent_production_version: none" in production_text
    assert "// production_note: Initial publish." in production_text


def test_publish_rejects_changed_id_reuse_without_explicit_policy(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do it now.""",
    )

    with pytest.raises(RuntimeError, match="P-1 -> P-1a"):
        _publisher(cfg, "z8n3d5q1w6te").publish()


def test_publish_can_apply_changed_id_updates_and_generate_recording_requests(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 CHRISTINE: Do you mind if I record?
P-2 LILLIAN: Please do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 CHRISTINE: Do you mind if I record?
P-2 LILLIAN: Please do it now.
P-3 LILLIAN: I am Lillian Barnes.""",
    )

    result = _publisher(cfg, "z8n3d5q1w6te").publish(
        apply_id_updates=True,
        recording_requests=True,
        change_summary="Changed Lillian's line.",
    )

    assert result.version.label == "2@z8n3d5q1w6te"
    assert result.id_updates == {"P-2": "P-2a"}
    assert "P-2a LILLIAN: Please do it now." in cfg.production_markdown.read_text(encoding="utf-8")
    assert "// production_version: 2@z8n3d5q1w6te" in cfg.production_markdown.read_text(encoding="utf-8")
    assert "// parent_production_version: 1@k9f4p2x8m1qd" in cfg.production_markdown.read_text(encoding="utf-8")
    assert "// production_note: Changed Lillian's line." in cfg.production_markdown.read_text(encoding="utf-8")
    assert result.recording_request_paths == (cfg.build_dir / "linerecorder" / "LILLIAN.recording-request.zip",)

    manifest = json.loads((cfg.build_dir / "linerecorder" / "LILLIAN" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["request"]["kind"] == "production_update_2@z8n3d5q1w6te"
    assert [item["id"] for item in manifest["items"]] == ["P-2a:s1", "P-3:s1"]
    assert [item["reason"] for item in manifest["items"]] == ["script_changed", "script_added"]
    with zipfile.ZipFile(result.recording_request_paths[0]) as archive:
        assert archive.namelist() == ["manifest.json"]


def test_publish_can_generate_recording_request_when_id_reuse_is_allowed(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do it now.""",
    )

    _publisher(cfg, "z8n3d5q1w6te").publish(allow_id_reuse=True, recording_requests=True)

    manifest = json.loads((cfg.build_dir / "linerecorder" / "LILLIAN" / "manifest.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in manifest["items"]] == ["P-1:s1"]
    assert [item["reason"] for item in manifest["items"]] == ["script_changed"]


def test_publish_treats_inline_direction_changes_as_context_not_recording_work(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please (_crossing_) do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please (_sitting_) do.""",
    )

    result = _publisher(cfg, "z8n3d5q1w6te").publish(recording_requests=True)

    assert [change.kind for change in result.change_report.changes] == ["context_changed"]
    assert result.recording_request_paths == ()


def test_publish_treats_inline_blocking_changes_as_context_not_recording_work(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please (_/CHRISTINE: crosses_) do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please (_/CHRISTINE: sits_) do.""",
    )

    result = _publisher(cfg, "z8n3d5q1w6te").publish(recording_requests=True)

    assert [change.kind for change in result.change_report.changes] == ["context_changed"]
    assert result.recording_request_paths == ()


def test_publish_assigns_internal_ids_to_idless_standalone_blocking(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
/CHRISTINE: crosses.
P-1 LILLIAN: Please do.""",
    )
    result = _publisher(cfg, "k9f4p2x8m1qd").publish()

    assert [line.id for line in result.version.lines] == ["P-0", "P-1:b1", "P-1"]


def test_publish_attaches_trailing_idless_standalone_blocking_to_previous_line(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.
/CHRISTINE: exits.""",
    )
    result = _publisher(cfg, "k9f4p2x8m1qd").publish()

    assert [line.id for line in result.version.lines] == ["P-0", "P-1", "P-1:b1"]


def test_restore_copies_published_version_to_producer_source(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.
P-2 LILLIAN: I am Lillian Barnes.""",
    )
    _publisher(cfg, "z8n3d5q1w6te").publish()

    ProductionVersionStore(cfg).restore_source("1@k9f4p2x8m1qd")

    assert "P-2" not in cfg.production_markdown.read_text(encoding="utf-8")


def test_production_source_resolver_auto_prefers_published_version(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Published text.""",
    )
    _publisher(cfg, "k9f4p2x8m1qd").publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Working text.""",
    )

    resolved = ProductionSourceResolver(cfg).resolve("auto")

    assert resolved.kind == "published"
    assert resolved.path == cfg.build_dir / "production-history" / "versions" / "0001-k9f4p2x8m1qd" / "production.md"


def test_production_source_resolver_auto_falls_back_to_working_without_published_version(tmp_path: Path, caplog) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Working text.""",
    )

    resolved = ProductionSourceResolver(cfg).resolve("auto")

    assert resolved.kind == "working"
    assert resolved.path == cfg.production_markdown
    assert "No published production version exists; using working production source" in caplog.text
