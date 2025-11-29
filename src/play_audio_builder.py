#!/usr/bin/env python3
"""Render audio from a plan and optionally mux captions."""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from play_plan_builder import PlanItem, Silence, Chapter, load_audio_by_path
from clip import CalloutClip, SegmentClip


def export_with_chapters(
    audio: AudioSegment,
    chapters: List[Tuple[int, int, str]],
    out_path: Path,
    fmt: str,
    metadata: dict[str, str] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not chapters:
        export_kwargs = {}
        if fmt == "mp3":
            export_kwargs["bitrate"] = "128k"
            export_kwargs["tags"] = metadata or {}
            export_kwargs["id3v2_version"] = "3"
        audio.export(out_path, format=fmt, **export_kwargs)
        return

    import tempfile
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "tmp.wav"
        meta_path = Path(tmpdir) / "chapters.txt"
        audio.export(wav_path, format="wav")
        lines = [";FFMETADATA1"]
        for start, end, title in chapters:
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={start}")
            lines.append(f"END={end}")
            lines.append(f"title={title}")
        meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-i",
            str(meta_path),
            "-map_metadata",
            "1",
            "-c:a",
            "aac" if fmt == "mp4" else "libmp3lame",
            "-b:a",
            "128k" if fmt == "mp3" else "192k",
        ]
        for key, val in (metadata or {}).items():
            cmd.extend(["-metadata", f"{key}={val}"])
        if fmt == "mp3":
            cmd.extend(["-id3v2_version", "3", "-write_id3v1", "1"])
        cmd.append(str(out_path))
        subprocess.run(cmd, check=True)


def instantiate_plan(
    plan: List[PlanItem],
    out_path: Path,
    audio_format: str,
    captions_path: Path | None = None,
    prepend_paths: List[Path] | None = None,
    append_paths: List[Path] | None = None,
    metadata: dict[str, str] | None = None,
) -> None:
    """Render the audio plan into a single audio file, optionally muxing captions and a blank video track."""
    cache: Dict[Path, AudioSegment | None] = {}
    audio = AudioSegment.empty()
    chapters: List[Tuple[int, int, str]] = []
    current_chapter_title: str | None = None
    current_chapter_start: int | None = None

    for extra in prepend_paths or []:
        seg = load_audio_by_path(extra, cache)
        if seg:
            audio += seg

    for item in plan:
        if isinstance(item, Chapter):
            logging.info("Inserting chapter: %s", item.title or "")
            if current_chapter_start is not None:
                chapters.append((current_chapter_start, len(audio), current_chapter_title or ""))
            current_chapter_title = item.title or ""
            current_chapter_start = len(audio)
            continue
        if isinstance(item, Silence):
            if item.length_ms > 0:
                audio += AudioSegment.silent(duration=item.length_ms)
            continue
        if isinstance(item, (CalloutClip, SegmentClip)):
            if item.path is None:
                continue
            seg = load_audio_by_path(item.path, cache)
            if seg:
                audio += seg

    if current_chapter_start is not None:
        chapters.append((current_chapter_start, len(audio), current_chapter_title or ""))

    for extra in append_paths or []:
        seg = load_audio_by_path(extra, cache)
        if seg:
            audio += seg

    export_with_chapters(audio, chapters if chapters else [], out_path, fmt=audio_format, metadata=metadata or {})

    if audio_format == "mp4":
        tmp_out = out_path.with_suffix(".tmp.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=size=1280x720:rate=30:color=black",
            "-i",
            str(out_path),
        ]
        map_args = ["-map", "0:v:0", "-map", "1:a:0"]
        if captions_path and captions_path.exists():
            cmd += ["-i", str(captions_path)]
            map_args += ["-map", "2:s:0"]
            cmd += ["-c:s", "mov_text", "-metadata:s:s:0", "language=eng"]
        cmd += map_args
        cmd += ["-shortest", "-c:v", "libx264", "-c:a", "copy", str(tmp_out)]
        logging.info("Muxing video (and captions if present) into %s", out_path)
        subprocess.run(cmd, check=True)
        tmp_out.replace(out_path)
