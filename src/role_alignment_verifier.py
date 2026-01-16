#!/usr/bin/env python3
"""Verify a role recording by aligning transcript words to expected script words."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from faster_whisper import WhisperModel
from rapidfuzz import fuzz

import paths
from block import RoleBlock, TitleBlock, DescriptionBlock, DirectionBlock
from play import Play
from play_text_parser import PlayTextParser
from segment import SpeechSegment, SimultaneousSegment, DirectionSegment


@dataclass
class RoleAlignmentVerifier:
    role: str
    paths: paths.PathConfig = field(default_factory=paths.current)
    play: Play | None = None
    model_name: str = "tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"
    remove_fillers: bool = True
    filler_words: set[str] = field(
        default_factory=lambda: {
            "uh",
            "um",
            "er",
            "ah",
            "eh",
            "hmm",
            "mm",
            "mhm",
            "uhh",
            "umm",
            "huh",
            "uhhuh",
            "mmhmm",
        }
    )
    skip_audio_penalty: float = -0.35
    skip_text_penalty: float = -0.5
    match_weight: float = 1.0
    min_match_similarity: float = 0.55
    low_match_penalty: float = -0.9
    next_word_boost_threshold: float = 0.9

    _model_cache: ClassVar[dict[tuple[str, str, str], WhisperModel]] = {}
    _logger: logging.Logger = field(init=False, repr=False)
    _model: WhisperModel = field(init=False, repr=False)
    _punct_re: re.Pattern[str] = field(init=False, repr=False)
    _space_re: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._punct_re = re.compile(r"[^\w\s]+")
        self._space_re = re.compile(r"\s+")
        if self.play is None:
            self.play = PlayTextParser(paths_config=self.paths).parse()
        self._model = self._load_model()

    def verify(self, recording_path: Path | None = None) -> dict:
        path = recording_path or (self.paths.recordings_dir / f"{self.role}.wav")
        if not path.exists():
            raise RuntimeError(f"Recording not found for role {self.role}: {path}")
        expected_segments, script_words, word_to_segment = self._build_expected_words()
        if not expected_segments:
            raise RuntimeError(f"No expected segments found for role {self.role}")
        audio_words = self._transcribe_words(path)
        alignment = self._align_words(script_words, audio_words)
        results = self._build_results(
            path,
            expected_segments,
            script_words,
            audio_words,
            word_to_segment,
            alignment,
        )
        self._logger.info(
            "Aligned %d segments for %s (%d script words, %d audio words)",
            len(expected_segments),
            self.role,
            len(script_words),
            len(audio_words),
        )
        return results

    def _load_model(self) -> WhisperModel:
        key = (self.model_name, self.device, self.compute_type)
        if key not in self._model_cache:
            self._model_cache[key] = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model_cache[key]

    def _build_expected_words(self) -> tuple[list[dict], list[str], list[int]]:
        expected_segments = self._collect_expected_segments()
        segments_out: list[dict] = []
        script_words: list[str] = []
        word_to_segment: list[int] = []

        for segment in expected_segments:
            tokens = self._normalize_text_to_words(segment["expected_text"])
            if not tokens:
                continue
            segment_index = len(segments_out)
            word_start = len(script_words)
            for token in tokens:
                script_words.append(token)
                word_to_segment.append(segment_index)
            segments_out.append(
                {
                    "segment_index": segment_index,
                    "segment_id": segment["segment_id"],
                    "expected_text": segment["expected_text"],
                    "expected_word_count": len(tokens),
                    "word_start": word_start,
                    "word_end": len(script_words),
                }
            )
        return segments_out, script_words, word_to_segment

    def _collect_expected_segments(self) -> list[dict]:
        if self.play is None:
            raise RuntimeError("Play is not loaded")
        if self.role == "_NARRATOR":
            return self._collect_narrator_segments()
        role_obj = self.play.getRole(self.role)
        if role_obj is None:
            raise RuntimeError(f"Role not found: {self.role}")
        segments: list[dict] = []
        for blk in role_obj.blocks:
            for seg in blk.segments:
                text = getattr(seg, "text", "").strip()
                if not text or text in {".", ",", ":", ";"}:
                    continue
                if isinstance(seg, SpeechSegment) and seg.role == self.role:
                    segments.append({"segment_id": str(seg.segment_id), "expected_text": text})
                elif isinstance(seg, SimultaneousSegment) and self.role in getattr(seg, "roles", []):
                    segments.append({"segment_id": str(seg.segment_id), "expected_text": text})
        return segments

    def _collect_narrator_segments(self) -> list[dict]:
        if self.play is None:
            raise RuntimeError("Play is not loaded")
        segments: list[dict] = []
        for blk in self.play.blocks:
            if isinstance(blk, (TitleBlock, DescriptionBlock, DirectionBlock)):
                relevant = blk.segments
            elif isinstance(blk, RoleBlock):
                relevant = []
                for seg in blk.segments:
                    if isinstance(seg, SpeechSegment) and seg.role == "_NARRATOR":
                        relevant.append(seg)
                    elif isinstance(seg, DirectionSegment):
                        relevant.append(seg)
            else:
                continue
            for seg in relevant:
                text = getattr(seg, "text", "").strip()
                if not text or text in {".", ",", ":", ";"}:
                    continue
                segments.append({"segment_id": str(seg.segment_id), "expected_text": text})
        return segments

    def _transcribe_words(self, path: Path) -> list[dict]:
        segments, _info = self._model.transcribe(
            str(path),
            word_timestamps=True,
            vad_filter=True,
        )
        words: list[dict] = []
        for segment in segments:
            for word in segment.words:
                raw = word.word.strip()
                normalized = self._normalize_token(raw)
                if not normalized:
                    continue
                words.append(
                    {
                        "word": raw,
                        "norm": normalized,
                        "start": float(word.start),
                        "end": float(word.end),
                    }
                )
        return words

    def _align_words(self, script_words: list[str], audio_words: list[dict]) -> list[dict]:
        script_len = len(script_words)
        audio_len = len(audio_words)
        dp = [[0.0] * (audio_len + 1) for _ in range(script_len + 1)]
        back = [[""] * (audio_len + 1) for _ in range(script_len + 1)]

        for i in range(1, script_len + 1):
            dp[i][0] = dp[i - 1][0] + self.skip_text_penalty
            back[i][0] = "skip_text"
        for j in range(1, audio_len + 1):
            dp[0][j] = dp[0][j - 1] + self.skip_audio_penalty
            back[0][j] = "skip_audio"

        for i in range(1, script_len + 1):
            expected = script_words[i - 1]
            for j in range(1, audio_len + 1):
                sim = self._match_similarity(script_words, audio_words, i - 1, j - 1)
                if sim < self.min_match_similarity:
                    score_match = dp[i - 1][j - 1] + self.low_match_penalty
                else:
                    score_match = dp[i - 1][j - 1] + (sim * self.match_weight)
                score_skip_text = dp[i - 1][j] + self.skip_text_penalty
                score_skip_audio = dp[i][j - 1] + self.skip_audio_penalty
                if score_match >= score_skip_text and score_match >= score_skip_audio:
                    dp[i][j] = score_match
                    back[i][j] = "match"
                elif score_skip_text >= score_skip_audio:
                    dp[i][j] = score_skip_text
                    back[i][j] = "skip_text"
                else:
                    dp[i][j] = score_skip_audio
                    back[i][j] = "skip_audio"

        steps: list[dict] = []
        i = script_len
        j = audio_len
        while i > 0 or j > 0:
            op = back[i][j]
            if op == "match":
                i -= 1
                j -= 1
                sim = self._match_similarity(script_words, audio_words, i, j) * 100.0
                steps.append(
                    {
                        "op": "match",
                        "script_index": i,
                        "audio_index": j,
                        "similarity": sim,
                    }
                )
            elif op == "skip_text":
                i -= 1
                steps.append(
                    {
                        "op": "skip_text",
                        "script_index": i,
                        "audio_index": None,
                        "similarity": 0.0,
                    }
                )
            elif op == "skip_audio":
                j -= 1
                steps.append(
                    {
                        "op": "skip_audio",
                        "script_index": None,
                        "audio_index": j,
                        "similarity": 0.0,
                    }
                )
            else:
                raise RuntimeError("Alignment backtrack failed")
        steps.reverse()
        return steps

    def _build_results(
        self,
        path: Path,
        expected_segments: list[dict],
        script_words: list[str],
        audio_words: list[dict],
        word_to_segment: list[int],
        alignment: list[dict],
    ) -> dict:
        segment_matches = [
            {"matched_audio_indices": [], "scores": []} for _ in expected_segments
        ]
        matched_word_scores: list[float] = []
        skipped_text_words = 0
        skipped_audio_words = 0

        for step in alignment:
            if step["op"] == "match":
                seg_index = word_to_segment[step["script_index"]]
                segment_matches[seg_index]["matched_audio_indices"].append(step["audio_index"])
                segment_matches[seg_index]["scores"].append(step["similarity"])
                matched_word_scores.append(step["similarity"])
            elif step["op"] == "skip_text":
                skipped_text_words += 1
            elif step["op"] == "skip_audio":
                skipped_audio_words += 1

        segments_out: list[dict] = []
        matched_segments = 0
        missing_segments = 0
        for segment in expected_segments:
            match_info = segment_matches[segment["segment_index"]]
            matched_indices = sorted(match_info["matched_audio_indices"])
            scores = match_info["scores"]
            if matched_indices:
                matched_segments += 1
                start = min(audio_words[i]["start"] for i in matched_indices)
                end = max(audio_words[i]["end"] for i in matched_indices)
                similarity = sum(scores) / len(scores)
                matched_text = " ".join(audio_words[i]["word"] for i in matched_indices)
                status = "matched"
            else:
                missing_segments += 1
                start = None
                end = None
                similarity = 0.0
                matched_text = ""
                status = "missing"
            expected_count = segment["expected_word_count"]
            matched_count = len(matched_indices)
            coverage = (matched_count / expected_count) if expected_count else 0.0
            segments_out.append(
                {
                    "segment_index": segment["segment_index"],
                    "segment_id": segment["segment_id"],
                    "expected_text": segment["expected_text"],
                    "matched_audio_start": start,
                    "matched_audio_end": end,
                    "similarity_score": round(similarity, 2),
                    "status": status,
                    "expected_word_count": expected_count,
                    "matched_word_count": matched_count,
                    "coverage": round(coverage, 3),
                    "matched_audio_text": matched_text,
                }
            )

        extra_entries = self._build_extra_audio_entries(audio_words, alignment)
        avg_similarity = (
            sum(matched_word_scores) / len(matched_word_scores) if matched_word_scores else 0.0
        )
        diagnostics = {
            "role": self.role,
            "recording_path": str(path),
            "expected_segments": len(expected_segments),
            "matched_segments": matched_segments,
            "missing_segments": missing_segments,
            "extra_audio_regions": len(extra_entries),
            "expected_words": len(script_words),
            "transcribed_words": len(audio_words),
            "matched_words": len(matched_word_scores),
            "skipped_text_words": skipped_text_words,
            "skipped_audio_words": skipped_audio_words,
            "avg_similarity": round(avg_similarity, 2),
        }
        return {
            "role": self.role,
            "recording_path": str(path),
            "segments": segments_out,
            "extra_audio": extra_entries,
            "diagnostics": diagnostics,
        }

    def _build_extra_audio_entries(
        self,
        audio_words: list[dict],
        alignment: list[dict],
    ) -> list[dict]:
        extra_indices = [
            step["audio_index"]
            for step in alignment
            if step["op"] == "skip_audio"
        ]
        extra_entries: list[dict] = []
        if not extra_indices:
            return extra_entries
        current: list[int] = []
        for idx in extra_indices:
            if not current or idx == current[-1] + 1:
                current.append(idx)
                continue
            extra_entries.append(self._extra_entry_for_indices(audio_words, current))
            current = [idx]
        if current:
            extra_entries.append(self._extra_entry_for_indices(audio_words, current))
        return extra_entries

    def _extra_entry_for_indices(self, audio_words: list[dict], indices: list[int]) -> dict:
        start = audio_words[indices[0]]["start"]
        end = audio_words[indices[-1]]["end"]
        recognized_text = " ".join(audio_words[i]["word"] for i in indices)
        return {
            "segment_index": None,
            "segment_id": None,
            "expected_text": None,
            "matched_audio_start": start,
            "matched_audio_end": end,
            "similarity_score": 0.0,
            "status": "extra",
            "recognized_text": recognized_text,
            "matched_word_count": len(indices),
        }

    def _normalize_text_to_words(self, text: str) -> list[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []
        words = normalized.split()
        if self.remove_fillers:
            words = [word for word in words if word not in self.filler_words]
        return words

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = self._punct_re.sub(" ", text)
        text = self._space_re.sub(" ", text).strip()
        return text

    def _normalize_token(self, token: str) -> str:
        token = token.lower().strip()
        token = self._punct_re.sub("", token)
        token = self._space_re.sub(" ", token).strip()
        if not token:
            return ""
        if self.remove_fillers and token in self.filler_words:
            return ""
        return token

    def _similarity(self, expected: str, actual: str) -> float:
        return float(fuzz.token_set_ratio(expected, actual))

    def _match_similarity(
        self,
        script_words: list[str],
        audio_words: list[dict],
        script_index: int,
        audio_index: int,
    ) -> float:
        expected = script_words[script_index]
        actual = audio_words[audio_index]["norm"]
        base = self._similarity(expected, actual) / 100.0
        next_script = script_index + 1
        next_audio = audio_index + 1
        if next_script < len(script_words) and next_audio < len(audio_words):
            next_expected = script_words[next_script]
            next_actual = audio_words[next_audio]["norm"]
            next_sim = self._similarity(next_expected, next_actual) / 100.0
            if next_sim >= self.next_word_boost_threshold:
                bigram_expected = f"{expected} {next_expected}"
                bigram_actual = f"{actual} {next_actual}"
                bigram_sim = fuzz.ratio(bigram_expected, bigram_actual) / 100.0
                if bigram_sim > base:
                    return bigram_sim
        return base
