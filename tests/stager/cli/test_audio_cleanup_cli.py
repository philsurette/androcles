from __future__ import annotations

from pathlib import Path
import wave

from typer.testing import CliRunner

from stager.cli import build
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation


def test_audio_cleanup_doctor_reports_capabilities(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "doctor", "--play", "test"])

    assert result.exit_code == 0
    assert "required cleanup filters: found" in result.output
    assert "optional cleanup filters found: adeclick, deesser, afftdn" in result.output


def test_audio_cleanup_plan_resolves_default_profile(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.segments_dir / "MEGAERA").mkdir(parents=True)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code == 0
    assert "cleanup approach: profile-based" in result.output
    assert "MEGAERA: profile gentle_voice_cleanup" in result.output
    assert "adeclick" in result.output


def test_audio_cleanup_plan_reports_missing_optional_filters(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.segments_dir / "MEGAERA").mkdir(parents=True)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker(filters={"loudnorm", "atrim", "asetpts"}))

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code == 0
    assert "MEGAERA: missing optional filters adeclick, deesser, afftdn" in result.output


def test_audio_cleanup_analyze_writes_report(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "analyze", "--play", "test"])

    assert result.exit_code == 0
    assert "Analyzed 1 segments." in result.output
    assert "build/test/audio/cleanup_analysis/report.json" in result.output


def test_audio_cleanup_plan_fails_for_analysis_without_report(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.play_dir / "audio_cleanup.yaml").write_text(
        """
version: 1
cleanup_approach: analysis-based
""",
        encoding="utf-8",
    )
    (cfg.segments_dir / "MEGAERA").mkdir(parents=True)
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code != 0
    assert "Analysis-based audio cleanup requires an accepted analysis report" in result.output


def test_audio_cleanup_plan_uses_analysis_after_report_exists(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    (cfg.play_dir / "audio_cleanup.yaml").write_text(
        """
version: 1
cleanup_approach: analysis-based
""",
        encoding="utf-8",
    )
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())
    analyze_result = CliRunner().invoke(build.app, ["audio-cleanup", "analyze", "--play", "test"])
    assert analyze_result.exit_code == 0

    result = CliRunner().invoke(build.app, ["audio-cleanup", "plan", "--play", "test"])

    assert result.exit_code == 0
    assert "MEGAERA: analysis" in result.output


def test_audio_cleanup_prepare_writes_batch_manifest(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "prepare", "--play", "test"])

    assert result.exit_code == 0
    assert "Prepared 1 cleanup batches: 1 segments, 0 cache hits" in result.output
    assert "MEGAERA-gentle_voice_cleanup" in result.output
    assert "build/test/audio/cleaned/MEGAERA-gentle_voice_cleanup/batch_manifest.json" in result.output


def test_audio_cleanup_prepare_reports_missing_optional_filter_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker(filters={"loudnorm", "atrim", "asetpts"}))

    result = CliRunner().invoke(build.app, ["audio-cleanup", "prepare", "--play", "test"])

    assert result.exit_code == 0
    assert "Missing optional cleanup filters:" in result.output
    assert "adeclick (MEGAERA)" in result.output
    assert "deesser (MEGAERA)" in result.output
    assert "afftdn (MEGAERA)" in result.output


def test_audio_cleanup_render_writes_cleaned_segment_with_no_filter_profile(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(build.app, ["audio-cleanup", "render", "--play", "test", "--profile", "none"])

    assert result.exit_code == 0
    assert "Rendered 1 cleanup batches; skipped 0 cache hits: 1/1 segments rendered" in result.output
    assert (cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "MEGAERA" / "0_1_1.wav").exists()


def test_audio_cleanup_render_dry_run_prepares_without_rendering_audio(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())

    result = CliRunner().invoke(
        build.app,
        ["audio-cleanup", "render", "--play", "test", "--profile", "none", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Dry run prepared 1 cleanup batches" in result.output
    assert (cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "batch_manifest.json").exists()
    assert not (cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "MEGAERA" / "0_1_1.wav").exists()


def test_audio_cleanup_render_dry_run_reports_missing_optional_filter_summary(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker(filters={"loudnorm", "atrim", "asetpts"}))

    result = CliRunner().invoke(build.app, ["audio-cleanup", "render", "--play", "test", "--dry-run"])

    assert result.exit_code == 0
    assert "Missing optional cleanup filters:" in result.output
    assert "adeclick (MEGAERA)" in result.output
    assert "Dry run prepared 1 cleanup batches" in result.output


def test_audio_cleanup_render_skips_rendered_cache_hits_unless_forced(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _patch_path_config(monkeypatch, cfg)
    monkeypatch.setattr(build, "AUDIO_TOOL_CHECKER", FakeAudioToolChecker())
    first = CliRunner().invoke(build.app, ["audio-cleanup", "render", "--play", "test", "--profile", "none"])
    assert first.exit_code == 0

    second = CliRunner().invoke(build.app, ["audio-cleanup", "render", "--play", "test", "--profile", "none"])
    forced = CliRunner().invoke(
        build.app,
        ["audio-cleanup", "render", "--play", "test", "--profile", "none", "--force"],
    )

    assert second.exit_code == 0
    assert "Rendered 0 cleanup batches; skipped 1 cache hits" in second.output
    assert "MEGAERA-none: skipped cache hit" in second.output
    assert forced.exit_code == 0
    assert "Rendered 1 cleanup batches; skipped 0 cache hits" in forced.output


def test_audio_cleanup_promote_requires_confirm(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    _write_cleanup_review(cfg)
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["audio-cleanup", "promote", "--play", "test"])

    assert result.exit_code != 0
    assert "requires --confirm" in result.output


def test_audio_cleanup_promote_copies_cleaned_audio(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    target_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    cleaned_path = cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "MEGAERA" / "0_1_1.wav"
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(b"canonical")
    cleaned_path.parent.mkdir(parents=True)
    cleaned_path.write_bytes(b"cleaned")
    _write_cleanup_review(cfg, output_path=cleaned_path)
    _patch_path_config(monkeypatch, cfg)

    result = CliRunner().invoke(build.app, ["audio-cleanup", "promote", "--play", "test", "--confirm"])

    assert result.exit_code == 0
    assert "Promoted 1 cleaned segments" in result.output
    assert "build/test/audio/cleaned/promotions/" in result.output
    assert target_path.read_bytes() == b"cleaned"


def _config(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def _patch_path_config(monkeypatch, cfg: paths.PathConfig) -> None:
    monkeypatch.setattr(build.paths, "PathConfig", lambda play_name: cfg)


class FakeAudioToolChecker:
    def __init__(self, filters: set[str] | None = None) -> None:
        self.filters = filters or {
            "loudnorm",
            "atrim",
            "asetpts",
            "adeclick",
            "deesser",
            "afftdn",
        }

    def require_audio_tools(self) -> FfmpegInstallation:
        return FfmpegInstallation(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            ffprobe_path=Path("/usr/bin/ffprobe"),
            source="PATH",
            config_path=None,
            filters=frozenset(self.filters),
        )


def _write_wav(path: Path, *, samples: list[int], sample_rate: int = 48_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))


def _write_cleanup_review(cfg: paths.PathConfig, *, output_path: Path | None = None) -> None:
    path = cfg.audio_out_dir / "cleaned" / "cleanup_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
{
  "play_id": "test",
  "entries": [
    {
      "batch_id": "MEGAERA-none",
      "role": "MEGAERA",
      "segment_id": "0_1_1",
      "analysis_recommendation_id": null,
      "output_path": "%s",
      "warnings": [],
      "fallback": false
    }
  ]
}
"""
        % ((output_path or Path("/tmp/cleaned.wav")).as_posix()),
        encoding="utf-8",
    )
