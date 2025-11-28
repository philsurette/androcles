#!/usr/bin/env python3
"""Render audio from a plan and optionally mux captions."""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from play_plan_builder import PlanItem, Silence, Chapter, CalloutClip, SegmentClip, load_audio_by_path


def export_with_chapters(audio: AudioSegment, chapters: List[Tuple[int, int, str]], out_path: Path, fmt: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "wav" or not chapters:
        audio.export(out_path, format=fmt)
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
            str(out_path),
        ]
        subprocess.run(cmd, check=True)


def instantiate_plan(plan: List[PlanItem], out_path: Path, audio_format: str, captions_path: Path | None = None) -> None:
    """Render the audio plan into a single audio file, optionally muxing captions."""
    cache: Dict[Path, AudioSegment | None] = {}
    audio = AudioSegment.empty()
    chapters: List[Tuple[int, int, str]] = []
    current_chapter_title: str | None = None
    current_chapter_start: int | None = None

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

    export_with_chapters(audio, chapters if chapters else [], out_path, fmt=audio_format)

    if captions_path and audio_format == "mp4" and captions_path.exists():
        tmp_out = out_path.with_suffix(".tmp.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(out_path),
            "-i",
            str(captions_path),
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-map",
            "0:a",
            "-map",
            "1:s:0",
            str(tmp_out),
        ]
        logging.info("Muxing captions into %s", out_path)
        subprocess.run(cmd, check=True)
        tmp_out.replace(out_path)
