#!/usr/bin/env python3
"""
Lightweight splitter to find word-boundary-friendly breakpoints inside a short clip.

It looks for short low-energy dips (default ~50ms) using a 1ms seek step so we can
crop cues on a quiet boundary rather than mid-word.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pydub import AudioSegment, silence


@dataclass
class WordAudioSplitter:
    """
    Detect short silence spans that are good word boundaries.

    Parameters
    ----------
    min_silence_ms : int
        Minimum length (ms) to consider a dip as a split candidate.
    silence_thresh_db : int | None
        Absolute dBFS threshold for silence. If None, derive from clip loudness.
    chunk_size : int
        Seek step used during detection. Keep at 1ms for finer resolution.
    """

    min_silence_ms: int = 50
    silence_thresh_db: int | None = None
    chunk_size: int = 1

    def _silence_threshold(self, audio: AudioSegment) -> int:
        """
        Choose a silence threshold. If not provided, back off from the clip's
        average loudness to be robust across recordings.
        """
        if self.silence_thresh_db is not None:
            return -abs(self.silence_thresh_db)
        # pydub reports dBFS as a negative number; subtract a cushion to find quiet spots.
        return int(audio.dBFS - 16) if audio.dBFS is not None else -40

    def find_silence_spans(self, audio_path: Path) -> List[Tuple[int, int]]:
        """
        Return silence spans (start_ms, end_ms) suitable for splitting.
        """
        audio = AudioSegment.from_file(audio_path)
        silence_thresh = self._silence_threshold(audio)
        spans = silence.detect_silence(
            audio,
            min_silence_len=self.min_silence_ms,
            silence_thresh=silence_thresh,
            seek_step=self.chunk_size,
        )
        # Normalize to tuples and ensure ascending order.
        return sorted([(int(start), int(end)) for start, end in spans], key=lambda s: s[0])

    def boundary_points(self, audio_path: Path) -> List[int]:
        """
        Return candidate split points (ms) using the midpoint of each detected span.
        """
        spans = self.find_silence_spans(audio_path)
        return [start + (end - start) // 2 for start, end in spans]

    def best_boundary_near(self, audio_path: Path, target_ms: int) -> int | None:
        """
        Choose the candidate boundary closest to `target_ms`.
        """
        points = self.boundary_points(audio_path)
        if not points:
            return None
        return min(points, key=lambda p: abs(p - target_ms))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find word-friendly split points in an audio clip.")
    parser.add_argument("audio", type=Path, help="Path to a WAV/MP3/etc segment")
    parser.add_argument("--target", type=int, default=None, help="Preferred split position (ms)")
    parser.add_argument("--min-silence", type=int, default=50, help="Minimum dip length (ms)")
    parser.add_argument("--silence-thresh", type=int, default=None, help="Silence threshold dBFS (negative)")
    args = parser.parse_args()

    splitter = WordAudioSplitter(min_silence_ms=args.min_silence, silence_thresh_db=args.silence_thresh)
    spans = splitter.find_silence_spans(args.audio)
    points = splitter.boundary_points(args.audio)
    print(f"Detected {len(points)} candidate boundaries in {args.audio}")
    for (start, end), mid in zip(spans, points):
        print(f"{start:>6}-{end:<6} ms -> {mid:>6} ms")
    if args.target is not None:
        best = splitter.best_boundary_near(args.audio, args.target)
        print(f"Closest to {args.target} ms: {best} ms" if best is not None else "No candidate boundary found")
