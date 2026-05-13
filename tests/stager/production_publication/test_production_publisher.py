from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from stager.production_publication.production_publisher import ProductionPublisher
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


def test_publish_creates_initial_managed_version(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )

    result = ProductionPublisher(cfg).publish()

    assert result.version.label == "v0001"
    assert result.change_report.base_version is None
    assert (cfg.build_dir / "production-history" / "versions" / "v0001" / "production.md").exists()
    current = json.loads((cfg.build_dir / "production-history" / "current.json").read_text(encoding="utf-8"))
    assert current["version"] == 1


def test_publish_rejects_changed_id_reuse_without_explicit_policy(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )
    ProductionPublisher(cfg).publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do it now.""",
    )

    with pytest.raises(RuntimeError, match="P-1 -> P-1a"):
        ProductionPublisher(cfg).publish()


def test_publish_can_apply_changed_id_updates_and_generate_recording_requests(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 CHRISTINE: Do you mind if I record?
P-2 LILLIAN: Please do.""",
    )
    ProductionPublisher(cfg).publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 CHRISTINE: Do you mind if I record?
P-2 LILLIAN: Please do it now.
P-3 LILLIAN: I am Lillian Barnes.""",
    )

    result = ProductionPublisher(cfg).publish(apply_id_updates=True, recording_requests=True)

    assert result.version.label == "v0002"
    assert result.id_updates == {"P-2": "P-2a"}
    assert "P-2a LILLIAN: Please do it now." in cfg.production_markdown.read_text(encoding="utf-8")
    assert result.recording_request_paths == (cfg.build_dir / "linerecorder" / "LILLIAN.recording-request.zip",)

    manifest = json.loads((cfg.build_dir / "linerecorder" / "LILLIAN" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["request"]["kind"] == "production_update_v0002"
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
    ProductionPublisher(cfg).publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do it now.""",
    )

    ProductionPublisher(cfg).publish(allow_id_reuse=True, recording_requests=True)

    manifest = json.loads((cfg.build_dir / "linerecorder" / "LILLIAN" / "manifest.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in manifest["items"]] == ["P-1:s1"]
    assert [item["reason"] for item in manifest["items"]] == ["script_changed"]


def test_restore_copies_published_version_to_producer_source(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.""",
    )
    ProductionPublisher(cfg).publish()
    _write_production(
        cfg,
        """# P-0 PROLOGUE
P-1 LILLIAN: Please do.
P-2 LILLIAN: I am Lillian Barnes.""",
    )
    ProductionPublisher(cfg).publish()

    ProductionVersionStore(cfg).restore_source("v0001")

    assert "P-2" not in cfg.production_markdown.read_text(encoding="utf-8")
