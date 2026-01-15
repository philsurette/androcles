"""Shared audio splitting utilities."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple
from dataclasses import dataclass, field
from time import perf_counter
import logging

from pydub import AudioSegment, silence

import paths


@dataclass
class AudioSplitter:
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    pad_end_ms: int | None = None
    chunk_size: int = 50
    pad_start_ms: int | None = None
    verbose: bool = False
    chunk_exports: bool = False
    chunk_export_size: int = 25
    last_detect_seconds: float = 0.0
    last_export_seconds: float = 0.0

    def find_recording(self, role: str, paths_config: paths.PathConfig | None = None) -> Path | None:
        """Find the recording for a role."""
        cfg = paths_config or paths.current()
        candidate = cfg.recordings_dir / f"{role}.wav"
        if candidate.exists():
            return candidate
        return None

    def _cuts_from_silence(
        self, silent_spans: List[Tuple[int, int]], audio_len: int, *, offset_ms: int = 0, chunk_size: int
    ) -> List[Tuple[int, int]]:
        """Convert silent spans to audio span tuples, applying an offset for chunked processing."""
        cuts: List[Tuple[int, int]] = []
        last = 0
        for start, end in silent_spans:
            if start > last:
                seg_start = max(0, last - chunk_size) + offset_ms
                seg_end = min(start + chunk_size, audio_len) + offset_ms
                if seg_end > seg_start:
                    cuts.append((seg_start, seg_end))
            last = end
        if last < audio_len:
            seg_start = max(0, last - chunk_size) + offset_ms
            seg_end = audio_len + offset_ms
            cuts.append((seg_start, seg_end))
        return cuts

    @staticmethod
    def _merge_spans(spans: List[Tuple[int, int]], *, merge_gap_ms: int = 0) -> List[Tuple[int, int]]:
        """Merge overlapping or touching spans, optionally allowing a small gap."""
        if not spans:
            return []
        spans_sorted = sorted(spans, key=lambda s: s[0])
        merged: List[Tuple[int, int]] = [spans_sorted[0]]
        for start, end in spans_sorted[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end + merge_gap_ms:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged

    def detect_spans(self, audio_path: Path, *, chunk_duration_ms: int | None = None) -> List[Tuple[int, int]]:
        """Detect non-silent spans using configured thresholds, optionally chunking detection."""
        total_start = perf_counter()
        silence_thresh = -abs(self.silence_thresh)
        chunk_size = max(1, self.chunk_size)
        pad_end_ms = chunk_size if self.pad_end_ms is None else self.pad_end_ms
        t0 = perf_counter()
        audio = AudioSegment.from_file(audio_path)
        load_time = perf_counter() - t0
        if self.verbose:
            logging.getLogger(__name__).info(
                "Loaded audio %s (%.2fs) in %.3fs", audio_path, len(audio) / 1000.0, load_time
            )
        if not chunk_duration_ms or chunk_duration_ms <= 0:
            t1 = perf_counter()
            silent_spans = silence.detect_silence(
                audio, min_silence_len=self.min_silence_ms, silence_thresh=silence_thresh, seek_step=chunk_size
            )
            det_time = perf_counter() - t1
            cuts = self._cuts_from_silence(silent_spans, len(audio), offset_ms=0, chunk_size=chunk_size)
            if self.verbose:
                logging.getLogger(__name__).info(
                    "Detected %d silent spans, %d cuts in %.3fs (no chunking)",
                    len(silent_spans),
                    len(cuts),
                    det_time,
                )
        else:
            cuts: List[Tuple[int, int]] = []
            chunk_duration_ms = max(chunk_duration_ms, chunk_size)
            total_len = len(audio)
            start_ms = 0
            while start_ms < total_len:
                end_ms = min(start_ms + chunk_duration_ms, total_len)
                segment = audio[start_ms:end_ms]
                t_chunk = perf_counter()
                silent_spans = silence.detect_silence(
                    segment, min_silence_len=self.min_silence_ms, silence_thresh=silence_thresh, seek_step=chunk_size
                )
                det_time = perf_counter() - t_chunk
                cuts.extend(self._cuts_from_silence(silent_spans, len(segment), offset_ms=start_ms, chunk_size=chunk_size))
                if self.verbose:
                    logging.getLogger(__name__).info(
                        "Chunk %d-%d ms: %d silent spans -> %d cuts in %.3fs",
                        start_ms,
                        end_ms,
                        len(silent_spans),
                        len(cuts),
                        det_time,
                    )
                start_ms += chunk_duration_ms
            cuts = self._merge_spans(cuts, merge_gap_ms=0)
            if self.verbose:
                logging.getLogger(__name__).info("Merged to %d cuts after chunked detection", len(cuts))

        self.last_detect_seconds = perf_counter() - total_start
        if self.verbose:
            logging.getLogger(__name__).info("Total silence detection time: %.3fs", self.last_detect_seconds)
        return [(s, e) for s, e in cuts if e > s]

    def export_spans(
        self,
        source: Path,
        spans_ms: List[Tuple[int, int]],
        ids: Iterable[str],
        out_dir: Path,
        *,
        chunk_exports: bool | None = None,
        chunk_export_size: int | None = None,
        cleanup_existing: bool = True,
    ) -> None:
        """Export spans to WAV files using configured splitter."""
        chunk_exports = self.chunk_exports if chunk_exports is None else chunk_exports
        chunk_export_size = self.chunk_export_size if chunk_export_size is None else chunk_export_size
        out_dir.mkdir(parents=True, exist_ok=True)
        if cleanup_existing:
            for f in out_dir.glob("*.wav"):
                f.unlink()

        spans_list = list(spans_ms)
        ids_list = list(ids)
        if not spans_list:
            return
        total_export_start = perf_counter()

        def fmt_offset(ms: int) -> str:
            secs = ms / 1000.0
            mins = int(secs // 60)
            rem = secs - mins * 60
            return f"{mins}:{rem:04.1f}"

        def run_batch(batch_spans: List[Tuple[int, int]], batch_ids: List[str], batch_idx: int) -> None:
            if not batch_spans:
                return
            base_start_ms = min(s for s, _ in batch_spans)
            base_seek = max(0, base_start_ms / 1000.0)
            filter_parts = []
            maps: List[str] = []
            for idx, ((start_ms, end_ms), eid) in enumerate(zip(batch_spans, batch_ids)):
                label = f"a{idx}"
                start_s = max(0.0, (start_ms - base_start_ms) / 1000.0)
                end_s = max(start_s, (end_ms - base_start_ms) / 1000.0)
                filter_parts.append(f"[0:a]atrim=start={start_s}:end={end_s},asetpts=PTS-STARTPTS[{label}]")
                maps.extend(["-map", f"[{label}]", str(out_dir / f"{eid}.wav")])
            if not filter_parts:
                return
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{base_seek:.3f}",
                "-i",
                str(source),
                "-filter_complex",
                ";".join(filter_parts),
            ] + maps
            if self.verbose:
                logging.getLogger(__name__).info(
                    "FFmpeg export batch %d (%d clips, seek %.3fs): %s",
                    batch_idx,
                    len(batch_ids),
                    base_seek,
                    " ".join(cmd),
                )
            t0 = perf_counter()
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.verbose:
                logging.getLogger(__name__).info(
                    "FFmpeg export batch %d completed in %.3fs", batch_idx, perf_counter() - t0
                )

        if chunk_exports:
            size = max(1, chunk_export_size)
            batch_no = 1
            for i in range(0, len(spans_list), size):
                run_batch(spans_list[i : i + size], ids_list[i : i + size], batch_no)
                batch_no += 1
        else:
            run_batch(spans_list, ids_list, 1)
        self.last_export_seconds = perf_counter() - total_export_start
        if self.verbose:
            logging.getLogger(__name__).info("Total ffmpeg export time: %.3fs", self.last_export_seconds)

        # Write offsets.txt with start times for all exported spans.
        offsets_path = out_dir / "offsets.txt"
        offsets: dict[str, str] = {}
        if not cleanup_existing and offsets_path.exists():
            for line in offsets_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    offsets[parts[0]] = parts[1]
        for (start_ms, _), eid in zip(spans_list, ids_list):
            offsets[eid] = fmt_offset(start_ms)
        with offsets_path.open("w", encoding="utf-8") as fh:
            for eid, ts in sorted(offsets.items()):
                fh.write(f"{eid} {ts}\n")
