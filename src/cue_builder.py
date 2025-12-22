#!/usr/bin/env python3
"""Build role cue MP4s with chapter markers for cues and responses."""
from __future__ import annotations

import logging
import tempfile
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from play import Play, RoleBlock
import paths


@dataclass
class CueBuilder:
    """Build cues using in-memory PlayText data."""

    play: Play
    response_delay_ms: int = 2000
    max_cue_size_ms: int = 5000
    include_prompts: bool = True
    callout_spacing_ms: int = 300
    segment_maps: Dict[str, Dict[Tuple[int | None, int], List[str]]] = field(init=False)

    def __post_init__(self) -> None:
        self.segment_maps = self.play.build_segment_maps()

    def _concat_segments(self, role: str, seg_ids: List[str]) -> AudioSegment:
        """Concatenate audio segments for a role."""
        audio = AudioSegment.empty()
        for sid in seg_ids:
            path = paths.SEGMENTS_DIR / role / f"{sid}.wav"
            if not path.exists():
                logging.warning("Missing snippet %s for role %s", sid, role)
                continue
            audio += AudioSegment.from_file(path)
        return audio

    def _load_callout(self, role: str) -> AudioSegment | None:
        """Return the callout clip for a role if it exists."""
        path = paths.CALLOUTS_DIR / f"{role}_callout.wav"
        if not path.exists():
            logging.warning("Missing callout for role %s at %s", role, path)
            return None
        return AudioSegment.from_file(path)

    @staticmethod
    def _crop_cue(
        audio: AudioSegment,
        tail_ms: int = 5000,
        extend_ms: int = 2000,
        head_ms: int = 2000,
        gap_ms: int = 500,
    ) -> AudioSegment:
        """
        Keep the last `tail_ms` (configurable). If the total cue is shorter than
        tail_ms + extend_ms, keep it whole. Otherwise keep the first `head_ms`,
        a gap, then the last `tail_ms`.
        """
        total = len(audio)
        if total <= tail_ms + extend_ms:
            return audio
        head = audio[: min(head_ms, total)]
        tail = audio[-tail_ms:] if tail_ms < total else audio
        gap = AudioSegment.silent(duration=gap_ms) if gap_ms > 0 else AudioSegment.empty()
        return head + gap + tail

    def _previous_speech_block(self, part_blocks: List[RoleBlock], idx: int) -> RoleBlock | None:
        for j in range(idx - 1, -1, -1):
            prev = part_blocks[j]
            if not isinstance(prev, RoleBlock):
                continue
            if prev.primary_role.startswith("_"):
                continue
            return prev
        return None

    def build_cues_for_role(
        self,
        role: str,
    ) -> Tuple[AudioSegment, List[Tuple[int, int, str]]]:
        """
        Return combined audio and chapter tuples (start_ms, end_ms, title)
        for the given role.
        """
        combined = AudioSegment.empty()
        chapters: List[Tuple[int, int, str]] = []

        for part in self.play.getParts():
            self._build_cues_for_role_and_part(role, part, combined, chapters)

        return combined, chapters

    def _build_cues_for_role_and_part(
        self,
        role: str,
        part: "Part",
        combined: AudioSegment,
        chapters: List[Tuple[int, int, str]],
    ) -> None:
        """Append cues for a role within a part to combined audio and chapters."""
        callout_cache: Dict[str, AudioSegment | None] = {}
        callout_gap = AudioSegment.silent(duration=self.callout_spacing_ms) if self.callout_spacing_ms > 0 else None

        speech_blocks = [b for b in part.blocks if isinstance(b, RoleBlock)]
        for idx, blk in enumerate(speech_blocks):
            self._append_block_cues(
                role=role,
                block=blk,
                speech_blocks=speech_blocks,
                idx=idx,
                combined=combined,
                chapters=chapters,
                callout_cache=callout_cache,
                callout_gap=callout_gap,
            )

    def _append_block_cues(
        self,
        role: str,
        block: RoleBlock,
        speech_blocks: List[RoleBlock],
        idx: int,
        combined: AudioSegment,
        chapters: List[Tuple[int, int, str]],
        callout_cache: Dict[str, AudioSegment | None],
        callout_gap: AudioSegment | None,
    ) -> None:
        """Append cues for a single block to the combined audio and chapters."""
        if block.primary_role != role:
            return

        prev_block = self._previous_speech_block(speech_blocks, idx)

        if prev_block and self.include_prompts:
            cue_role = prev_block.primary_role
            key = (prev_block.block_id.part_id, prev_block.block_id.block_no)
            cue_ids = self.segment_maps.get(cue_role, {}).get(key, [])
            if cue_ids:
                if cue_role not in callout_cache:
                    callout_cache[cue_role] = self._load_callout(cue_role)
                call = callout_cache[cue_role]
                if call:
                    combined += call
                    if callout_gap:
                        combined += callout_gap

                cue_audio = self._concat_segments(cue_role, cue_ids)
                cue_audio = self._crop_cue(cue_audio, tail_ms=self.max_cue_size_ms)

                cue_start = len(combined)
                combined += cue_audio
                cue_end = len(combined)
                chapters.append((cue_start, cue_end, f"CUE {cue_role} {cue_ids[0]}"))

                combined += AudioSegment.silent(duration=self.response_delay_ms)

        key = (block.block_id.part_id, block.block_id.block_no)
        resp_ids = self.segment_maps.get(role, {}).get(key, [])
        if not resp_ids:
            logging.warning("No response segment ids for %s %s:%s", role, block.block_id.part_id, block.block_id.block_no)
            return

        resp_audio = self._concat_segments(role, resp_ids)
        resp_start = len(combined)
        combined += resp_audio
        resp_end = len(combined)
        chapters.append((resp_start, resp_end, f"LINE {role} {resp_ids[0]}"))

        combined += AudioSegment.silent(duration=self.response_delay_ms)

    def build_cues(self, role: str) -> Path:
        """Build cue MP4 for a role using builder configuration."""
        audio, chapters = self.build_cues_for_role(role)
        # drop trailing silence from last gap if present
        if chapters:
            total = chapters[-1][1]
            audio = audio[:total]
        out_path = paths.AUDIO_OUT_DIR / "cues" / f"{role}_cue.mp4"
        self._export_mp4(audio, chapters, out_path)
        logging.info("Wrote cue file %s with %d chapters", out_path, len(chapters))
        return out_path


    @staticmethod
    def _write_ffmetadata(chapters: List[Tuple[int, int, str]], path: Path) -> None:
        lines = [";FFMETADATA1"]
        for start, end, title in chapters:
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={start}")
            lines.append(f"END={end}")
            lines.append(f"title={title}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _export_mp4(self, audio: AudioSegment, chapters: List[Tuple[int, int, str]], out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "tmp.wav"
            meta_path = Path(tmpdir) / "chapters.txt"
            audio.export(wav_path, format="wav")
            self._write_ffmetadata(chapters, meta_path)
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
                "aac",
                str(out_path),
            ]
            subprocess.run(cmd, check=True)
