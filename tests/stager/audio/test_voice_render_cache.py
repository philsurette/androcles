from __future__ import annotations

import json
from pathlib import Path

from stager.audio.voice_profile_config import VoiceProfileConfigParser
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.shared import paths


def test_voice_render_cache_writes_manifest_and_reports_hit(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)
    source = cache.source_identity(layer="canonical", path=source_path)
    segment = cache.segment(
        resolved_profile=resolved,
        source=source,
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={"loudnorm": True},
        production_id="1.abc123",
        production_content_hash="production-hash",
    )

    assert cache.is_hit(segment) is False

    segment.output_path.parent.mkdir(parents=True)
    segment.output_path.write_bytes(b"rendered")
    manifest_path = cache.write_manifest(
        resolved_profile=resolved,
        renderer_backend="ffmpeg",
        renderer_capabilities={"loudnorm": True},
        segments=(segment,),
    )

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["render_profile_id"].startswith("phil@MEGAERA-")
    assert data["segments"][0]["source"]["layer"] == "canonical"
    assert data["segments"][0]["production_id"] == "1.abc123"
    assert cache.is_hit(segment) is True


def test_voice_render_cache_key_changes_when_source_layer_changes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    cleaned_path = cfg.audio_out_dir / "cleaned" / "batch" / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    cleaned_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"same-content")
    cleaned_path.write_bytes(b"same-content")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)

    canonical = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(layer="canonical", path=source_path),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )
    cleaned = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(layer="cleaned", path=cleaned_path),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )

    assert canonical.cache_key != cleaned.cache_key


def test_voice_render_cache_key_includes_cleanup_review_identity(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cleaned_path = cfg.audio_out_dir / "cleaned" / "batch" / "MEGAERA" / "0_1_1.wav"
    review_path = cfg.audio_out_dir / "cleaned" / "cleanup_review.json"
    cleaned_path.parent.mkdir(parents=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_path.write_bytes(b"cleaned")
    review_path.write_text('{"review": 1}', encoding="utf-8")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)

    first = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(
            layer="cleaned",
            path=cleaned_path,
            cleanup_review_id="review-1",
            cleanup_review_path=review_path,
        ),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )
    review_path.write_text('{"review": 2}', encoding="utf-8")
    second = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(
            layer="cleaned",
            path=cleaned_path,
            cleanup_review_id="review-1",
            cleanup_review_path=review_path,
        ),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )

    assert first.cache_key != second.cache_key


def test_voice_render_cache_key_changes_when_transform_changes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    first_resolved = _resolved(tmp_path, pitch_shift=1.5)
    second_resolved = _resolved(tmp_path, pitch_shift=2.0)
    cache = VoiceRenderCache(cfg)
    source = cache.source_identity(layer="canonical", path=source_path)

    first = cache.segment(
        resolved_profile=first_resolved,
        source=source,
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )
    second = cache.segment(
        resolved_profile=second_resolved,
        source=source,
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )

    assert first.cache_key != second.cache_key


def test_voice_render_cache_misses_when_source_audio_changes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    source_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    resolved = _resolved(tmp_path)
    cache = VoiceRenderCache(cfg)
    first = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(layer="canonical", path=source_path),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )
    first.output_path.parent.mkdir(parents=True)
    first.output_path.write_bytes(b"rendered")
    cache.write_manifest(
        resolved_profile=resolved,
        renderer_backend="ffmpeg",
        renderer_capabilities={},
        segments=(first,),
    )

    source_path.write_bytes(b"changed")
    second = cache.segment(
        resolved_profile=resolved,
        source=cache.source_identity(layer="canonical", path=source_path),
        segment_id="0_1_1",
        renderer_backend="ffmpeg",
        renderer_capabilities={},
    )

    assert cache.is_hit(second) is False


def _resolved(tmp_path: Path, *, pitch_shift: float = 1.5):
    path = tmp_path / f"voice_profiles_{pitch_shift}.yaml"
    path.write_text(
        f"""
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: 178
    confidence: 0.9
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: explicit
    transforms:
      - type: pitch
        semitones: {pitch_shift}
        strategy: preserve_tempo
""",
        encoding="utf-8",
    )
    config = VoiceProfileConfigParser().parse(path)
    resolved = VoiceProfileResolver(config).resolve("MEGAERA")
    assert resolved is not None
    return resolved


def _cfg(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    return cfg
