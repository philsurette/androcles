"""Shared audio splitting utilities."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple
import math

from pydub import AudioSegment, silence

from paths import RECORDINGS_DIR, AUDIO_OUT_DIR


def find_recording(role: str) -> Path | None:
    """Find the recording for a role, preferring WAV, then MP3."""
    for ext in (".wav", ".mp3"):
        candidate = RECORDINGS_DIR / f"{role}{ext}"
        if candidate.exists():
            return candidate
    return None


def detect_spans_ms(
    audio_path: Path,
    min_silence_ms: int,
    silence_thresh: int,
    pad_end_ms: int | None = None,
    chunk_size: int = 25,
) -> List[Tuple[int, int]]:
    """
    Detect non-silent spans (start_ms, end_ms), padding start/end by one chunk of surrounding silence.
    """
    silence_thresh = -abs(silence_thresh)
    chunk_size = max(1, chunk_size)
    pad_end_ms = chunk_size if pad_end_ms is None else pad_end_ms
    audio = AudioSegment.from_file(audio_path)
    silent_spans = silence.detect_silence(
        audio, min_silence_len=min_silence_ms, silence_thresh=silence_thresh, seek_step=chunk_size
    )
    cuts: List[Tuple[int, int]] = []

    last = 0
    for start, end in silent_spans:
        if start > last:
            seg_start = max(0, last - chunk_size)
            seg_end = min(start + chunk_size, len(audio))
            if seg_end > seg_start:
                cuts.append((seg_start, seg_end))
        last = end
    if last < len(audio):
        seg_start = max(0, last - chunk_size)
        cuts.append((seg_start, len(audio)))

    return [(s, e) for s, e in cuts if e > s]


def export_spans_ffmpeg(source: Path, spans_ms: List[Tuple[int, int]], ids: Iterable[str], out_dir: Path) -> None:
    """Export spans to individual WAV files in one ffmpeg call."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.wav"):
        f.unlink()

    filter_parts = []
    maps: List[str] = []
    for idx, ((start_ms, end_ms), eid) in enumerate(zip(spans_ms, ids)):
        label = f"a{idx}"
        start_s = start_ms / 1000.0
        end_s = end_ms / 1000.0
        filter_parts.append(f"[0:a]atrim=start={start_s}:end={end_s},asetpts=PTS-STARTPTS[{label}]")
        maps.extend(["-map", f"[{label}]", str(out_dir / f"{eid}.wav")])

    if not filter_parts:
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        ";".join(filter_parts),
    ] + maps
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Write offsets file for reference
    write_offsets(out_dir, ids, spans_ms)


def write_offsets(out_dir: Path, ids: Iterable[str], spans_ms: List[Tuple[int, int]]) -> None:
    """Persist start offsets for each exported span."""
    lines = []
    for eid, (start_ms, _) in zip(ids, spans_ms):
        start_s = start_ms / 1000.0
        mins = int(start_s // 60)
        secs = start_s - mins * 60
        lines.append(f"{eid} {mins}:{secs:04.1f}")
    (out_dir / "offsets.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
