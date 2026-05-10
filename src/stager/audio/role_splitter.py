#!/usr/bin/env python3
"""
Split role recordings into per-line mp3 snippets based on the role blocks.

Assumptions:
- Input recordings live in plays/.../recordings/<ROLE>.mp3 (exclude names starting with "_").
- Output snippets are written to build/audio/<ROLE>/, named <part>_<block>_<elem>.mp3
  where elem counts all bullet lines in the block (directions included) but only
  speech lines (non-directions) are expected in the role recording.
- Snippets are separated by ~2s of silence; adjust thresholds via CLI flags if needed.
"""
from __future__ import annotations


from typing import List
import logging
from dataclasses import dataclass
from pathlib import Path

from stager.domain.block import RoleBlock
from stager.domain.segment import SpeechSegment, SimultaneousSegment
from stager.audio.segment_splitter import SegmentSplitter
from stager.shared import paths


@dataclass
class RoleSplitter(SegmentSplitter):

    def extra_outputs(self) -> List[Path]:
        readers_dir = self.paths.build_dir / "audio" / "readers"
        return list(readers_dir.glob(f"{self.role}*.wav")) if readers_dir.exists() else []

    def pre_export_spans(self, spans: List[tuple[int, int]], expected_ids: List[str], source_path) -> List[tuple[int, int]]:
        """
        For dramatic readings, peel off the initial \"<role> read by <reader>\" line
        and export it separately to build/audio/readers/{role}_reader.wav.
        """
        rm = getattr(self.play, "reading_metadata", None)
        if not rm or not rm.dramatic_reading:
            return spans

        if not spans:
            logging.warning("Expected reader intro for %s but found no spans to split", self.role)
            return spans

        reader_span, *remaining_spans = spans
        readers_dir = self.paths.build_dir / "audio" / "readers"
        reader_id = f"{self.role}_reader"
        self.splitter.export_spans(
            source_path,
            [reader_span],
            [reader_id],
            readers_dir,
            chunk_exports=False,
            cleanup_existing=False,
        )
        if len(remaining_spans) != len(expected_ids):
            logging.warning(
                "Reader intro split for %s left %d spans vs %d expected ids; verify recording",
                self.role,
                len(remaining_spans),
                len(expected_ids),
            )
        return remaining_spans

    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """
        Return expected segment ids for speech lines of a role, optionally filtered by part.
        Uses in-memory PlayText blocks (directions counted for numbering, only speech for the role emits ids).
        """
        ids: List[str] = []
        role_obj = self.play.getRole(self.role)

        blocks: List[RoleBlock] = role_obj.get_blocks(int(part_filter) if part_filter is not None else None)
        for blk in blocks:
            seq = 0
            for seg in blk.segments:
                text = getattr(seg, "text", "").strip()
                if not text:
                    continue
                # Ignore trivial punctuation (but keep expressive cries like "!!!" or "?!?").
                if text in {".", ",", ":", ";"}:
                    continue
                seq += 1
                if isinstance(seg, SpeechSegment) and seg.role == self.role:
                    ids.append(str(seg.segment_id))
                elif isinstance(seg, SimultaneousSegment) and self.role in getattr(seg, "roles", []):
                    ids.append(str(seg.segment_id))
        return ids


@dataclass
class CalloutSplitter(SegmentSplitter):
    """
    Split the callout recording into per-callout wavs.

    Input: plays/.../recordings/_CALLER.wav and build/markdown/roles/_CALLER.md
    Output: build/audio/callouts/<CALLOUT>.wav (one per callout name)
    """

    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """Callout ids are the callout names listed in _CALLER.md."""
        path = self.paths.markdown_roles_dir / "_CALLER.md"
        if not path.exists():
            raise RuntimeError(f"Missing callout script: {paths.display_path(path)}")
        reader = self.play.reading_metadata.reader_for_id("_CALLER")
        reader_name = reader.reader if reader else None
        if not reader_name:
            raise RuntimeError("Missing _CALLER reader name in play metadata")
        expected_header = f"callouts read by {reader_name}"

        callout_ids: set[str] = set()
        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            if blk.callout is None:
                continue
            callout_ids.add(blk.callout)

        spoken_to_id: dict[str, str] = {}
        for callout_id in callout_ids:
            for variant in {callout_id, callout_id.replace("-", " ")}:
                existing = spoken_to_id.get(variant)
                if existing and existing != callout_id:
                    raise RuntimeError(
                        f"Ambiguous callout name '{variant}' maps to {existing} and {callout_id}"
                    )
                spoken_to_id[variant] = callout_id
        raw_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        lines = [line for line in raw_lines if line]
        if not lines:
            raise RuntimeError(f"Empty callout script: {paths.display_path(path)}")

        def normalize(text: str) -> str:
            return " ".join(text.strip().lower().split())

        if self.play.reading_metadata.dramatic_reading:
            expected_norm = normalize(expected_header)
            header_line: str | None = None
            for line in lines:
                if line.startswith("#"):
                    continue
                if normalize(line).startswith("callouts read by "):
                    header_line = line
                    break
            if header_line is None:
                raise RuntimeError(f"Missing callout header '{expected_header}' in {paths.display_path(path)}")
            if normalize(header_line) != expected_norm:
                raise RuntimeError(
                    f"Unexpected callout header '{header_line}' in {paths.display_path(path)} (expected '{expected_header}')"
                )
            header_index = lines.index(header_line)
            lines = lines[header_index + 1 :]
        ids: List[str] = []
        for line in lines:
            if line.startswith("#"):
                continue
            if normalize(line).startswith("callouts read by "):
                continue
            if line.startswith("-"):
                line = line.lstrip("-").strip()
            if not line:
                continue
            callout_id = spoken_to_id.get(line)
            if not callout_id:
                raise RuntimeError(f"Unknown callout '{line}' in {paths.display_path(path)}")
            ids.append(callout_id)
        return ids

    def output_dir(self) -> Path:
        return self.paths.build_dir / "audio" / "callouts"

    def pre_export_spans(self, spans: List[tuple[int, int]], expected_ids: List[str], source_path) -> List[tuple[int, int]]:
        rm = getattr(self.play, "reading_metadata", None)
        if not rm or not rm.dramatic_reading:
            return spans
        if not spans:
            logging.warning("Expected caller intro but found no spans to split")
            return spans
        readers_dir = self.paths.build_dir / "audio" / "readers"
        readers_dir.mkdir(parents=True, exist_ok=True)
        reader_id = f"{self.role}_reader"
        self.splitter.export_spans(
            source_path,
            [spans[0]],
            [reader_id],
            readers_dir,
            chunk_exports=False,
            cleanup_existing=False,
        )
        remaining_spans = spans[1:]
        if len(remaining_spans) != len(expected_ids):
            logging.warning(
                "Caller intro split left %d spans vs %d expected ids; verify recording",
                len(remaining_spans),
                len(expected_ids),
            )
        return remaining_spans

    def source_path(self) -> Path:
        return self.paths.recordings_dir / "_CALLER.wav"
