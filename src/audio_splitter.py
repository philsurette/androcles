"""Shared audio splitting utilities."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple
from dataclasses import dataclass, field

from pydub import AudioSegment, silence

from paths import RECORDINGS_DIR, AUDIO_OUT_DIR


@dataclass
class AudioSplitter:
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    pad_end_ms: int | None = None
    chunk_size: int = 50
    pad_start_ms: int | None = None

    def find_recording(self, role: str) -> Path | None:
        """Find the recording for a role."""
        candidate = RECORDINGS_DIR / f"{role}.wav"
        if candidate.exists():
            return candidate
        return None

    def detect_spans(self, audio_path: Path) -> List[Tuple[int, int]]:
        """Detect non-silent spans using configured thresholds."""
        silence_thresh = -abs(self.silence_thresh)
        chunk_size = max(1, self.chunk_size)
        pad_end_ms = chunk_size if self.pad_end_ms is None else self.pad_end_ms
        audio = AudioSegment.from_file(audio_path)
        silent_spans = silence.detect_silence(
            audio, min_silence_len=self.min_silence_ms, silence_thresh=silence_thresh, seek_step=chunk_size
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

    def export_spans(self, source: Path, spans_ms: List[Tuple[int, int]], ids: Iterable[str], out_dir: Path) -> None:
        """Export spans to WAV files using configured splitter."""
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
