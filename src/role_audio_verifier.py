#!/usr/bin/env python3
"""Verify a role recording by aligning transcript words to expected script words."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from faster_whisper import WhisperModel
from rapidfuzz import fuzz

import paths
from block import RoleBlock, TitleBlock, DescriptionBlock, DirectionBlock
from play import Play
from play_text_parser import PlayTextParser
from segment import SpeechSegment, SimultaneousSegment, DirectionSegment
from whisper_model_store import WhisperModelStore
from inline_text_differ import InlineTextDiffer
from audio_verifier_diff import AudioVerifierDiff
from audio_verifier_diff_builder import AudioVerifierDiffBuilder
from audio_verifier_xlsx_writer import AudioVerifierXlsxWriter
from announcer import LibrivoxAnnouncer
from vad_config import VadConfig
from equivalencies import Equivalencies
from whisper_transcription_cache import WhisperTranscriptionCache


@dataclass
class RoleAudioVerifier:
    role: str
    paths: paths.PathConfig = field(default_factory=paths.current)
    play: Play | None = None
    model_name: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    whisper_store: WhisperModelStore | None = None
    vad_filter: bool = True
    vad_config: VadConfig | None = None
    transcription_cache: WhisperTranscriptionCache | None = None
    remove_fillers: bool = False
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
    diff_window_before: int = 3
    diff_window_after: int = 1
    extra_audio_padding_ms: int = 150
    homophone_max_words: int = 2

    _logger: logging.Logger = field(init=False, repr=False)
    _model: WhisperModel = field(init=False, repr=False)
    _inline_differ: InlineTextDiffer = field(init=False, repr=False)
    _name_tokens: set[str] = field(init=False, repr=False)
    _equivalencies: Equivalencies = field(init=False, repr=False)
    _punct_re: re.Pattern[str] = field(init=False, repr=False)
    _space_re: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._punct_re = re.compile(r"[^\w\s]+")
        self._space_re = re.compile(r"\s+")
        if self.play is None:
            self.play = PlayTextParser(paths_config=self.paths).parse()
        if self.whisper_store is None:
            self.whisper_store = WhisperModelStore(
                paths=self.paths,
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
            )
        if self.transcription_cache is None:
            self.transcription_cache = WhisperTranscriptionCache(paths=self.paths)
        self._model = self._load_model()
        self._name_tokens = self._build_name_tokens()
        self._equivalencies = self._load_equivalencies()
        self._inline_differ = InlineTextDiffer(
            window_before=self.diff_window_before,
            window_after=self.diff_window_after,
            name_tokens=self._name_tokens,
            equivalencies=self._equivalencies,
            homophone_max_words=self.homophone_max_words,
        )

    def verify(self, recording_path: Path | None = None) -> dict:
        path = recording_path or (self.paths.recordings_dir / f"{self.role}.wav")
        project_root = self.paths.root.parent
        rel_path = path.relative_to(project_root)
        self._logger.info("Verifying audio file %s", rel_path)
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
        self._logger.debug(
            "Aligned %d segments for %s (%d script words, %d audio words)",
            len(expected_segments),
            self.role,
            len(script_words),
            len(audio_words),
        )
        return results

    def build_diffs(self, results: dict) -> list[AudioVerifierDiff]:
        builder = AudioVerifierDiffBuilder(
            window_before=self.diff_window_before,
            window_after=self.diff_window_after,
            name_tokens=self._name_tokens,
            equivalencies=self._equivalencies,
            homophone_max_words=self.homophone_max_words,
        )
        return builder.build(results)

    def unresolved_replacements(self, results: dict) -> list[tuple[str, str, str | None]]:
        replacements: list[tuple[str, str, str | None]] = []
        for segment in results.get("segments", []):
            if segment.get("status") != "matched":
                continue
            expected = segment.get("expected_text", "")
            heard = segment.get("matched_audio_text", "")
            segment_id = segment.get("segment_id")
            for replacement in self._inline_differ.replacement_pairs(
                expected,
                heard,
                segment_id=segment_id,
            ):
                replacements.append(
                    (replacement.expected, replacement.actual, replacement.segment_id)
                )
        return replacements

    def _load_equivalencies(self) -> Equivalencies:
        play_path = self.paths.play_dir / "substitutions.yaml"
        role_path = self.paths.recordings_dir / f"{self.role}_substitutions.yaml"
        return Equivalencies.load_many([play_path, role_path])

    def _build_name_tokens(self) -> set[str]:
        tokens: set[str] = set()
        if self.play is None:
            return tokens
        for role in self.play.roles:
            if role.name.startswith("_"):
                continue
            tokens.update(self._tokenize_name(role.name))
            reader = self.play.reading_metadata.reader_for_id(role.name)
            if reader and reader.role_name:
                tokens.update(self._tokenize_name(reader.role_name))
        return tokens

    def _tokenize_name(self, name: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9']+", name)
        tokens: list[str] = []
        for token in raw_tokens:
            token = token.lower().replace("\u2019", "'").replace("\u2018", "'")
            token = token.replace("'", "")
            if token:
                tokens.append(token)
        return tokens

    def write_xlsx(self, results: dict, out_path: Path | None = None) -> Path:
        target = out_path or (self.paths.audio_out_dir / f"{self.role}_audio_verification.xlsx")
        diffs = self.build_diffs(results)
        writer = AudioVerifierXlsxWriter()
        return writer.write(diffs, target, sheet_name=self.role)

    def _load_model(self) -> WhisperModel:
        if self.whisper_store is None:
            raise RuntimeError("Whisper model store is not configured")
        return self.whisper_store.load(self.model_name)

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
        if self.role == "_CALLER":
            return self._collect_caller_segments()
        if self.role == "_ANNOUNCER":
            return self._collect_announcer_segments()
        role_obj = self.play.getRole(self.role)
        if role_obj is None:
            raise RuntimeError(f"Role not found: {self.role}")
        segments: list[dict] = []
        if role_obj.reader_block is not None:
            segments.append(
                {
                    "segment_id": f"{self.role}_reader",
                    "expected_text": role_obj.reader_block.text,
                }
            )
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

    def _collect_caller_segments(self) -> list[dict]:
        if self.play is None:
            raise RuntimeError("Play is not loaded")
        reader = self.play.reading_metadata.reader_for_id("_CALLER")
        reader_name = reader.reader
        segments: list[dict] = [
            {
                "segment_id": f"{self.role}_reader",
                "expected_text": f"callouts read by {reader_name}",
            }
        ]
        callouts: list[str] = []
        seen: set[str] = set()
        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            if blk.callout is None:
                continue
            if blk.callout in seen:
                continue
            seen.add(blk.callout)
            callouts.append(blk.callout)
        for name in sorted(callouts):
            segments.append(
                {
                    "segment_id": name,
                    "expected_text": name.replace("-", " "),
                }
            )
        return segments

    def _collect_announcer_segments(self) -> list[dict]:
        if self.play is None:
            raise RuntimeError("Play is not loaded")
        reader = self.play.reading_metadata.reader_for_id("_ANNOUNCER")
        reader_name = reader.reader or "<name>"
        segments: list[dict] = [
            {
                "segment_id": f"{self.role}_reader",
                "expected_text": f"announcements read by {reader_name}",
            }
        ]
        announcer = LibrivoxAnnouncer(self.play)
        for announcement in announcer.announcements():
            segments.append(
                {
                    "segment_id": announcement.key_as_filename(),
                    "expected_text": announcement.text,
                }
            )
        return segments

    def _transcribe_words(self, path: Path) -> list[dict]:
        vad_parameters = None
        if self.vad_filter and self.vad_config is not None:
            vad_parameters = self.vad_config.to_transcribe_parameters()
        cache_key = self._build_transcription_cache_key(path, vad_parameters)
        if self.transcription_cache is not None:
            cached = self.transcription_cache.load(cache_key, path)
            if cached is not None:
                return cached
        segments, _info = self._model.transcribe(
            str(path),
            word_timestamps=True,
            vad_filter=self.vad_filter,
            vad_parameters=vad_parameters,
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
        if self.transcription_cache is not None:
            self.transcription_cache.save(cache_key, path, words)
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
        skipped_audio_indices: list[int] = []

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
                skipped_audio_indices.append(step["audio_index"])

        segment_windows: list[dict] = []
        if skipped_audio_indices:
            pad_seconds = self.extra_audio_padding_ms / 1000.0
            for segment in expected_segments:
                match_info = segment_matches[segment["segment_index"]]
                matched_indices = match_info["matched_audio_indices"]
                if not matched_indices:
                    continue
                start = min(audio_words[i]["start"] for i in matched_indices)
                end = max(audio_words[i]["end"] for i in matched_indices)
                segment_windows.append(
                    {
                        "segment_index": segment["segment_index"],
                        "start": start - pad_seconds,
                        "end": end + pad_seconds,
                        "mid": (start + end) / 2.0,
                    }
                )

        segment_extra_indices: dict[int, list[int]] = {}
        reassigned_audio_indices: set[int] = set()
        if segment_windows:
            for audio_index in skipped_audio_indices:
                word = audio_words[audio_index]
                word_mid = (word["start"] + word["end"]) / 2.0
                candidates = [
                    window
                    for window in segment_windows
                    if window["start"] <= word_mid <= window["end"]
                ]
                if not candidates:
                    continue
                best = min(candidates, key=lambda window: abs(word_mid - window["mid"]))
                segment_extra_indices.setdefault(best["segment_index"], []).append(audio_index)
                reassigned_audio_indices.add(audio_index)

        segments_out: list[dict] = []
        matched_segments = 0
        missing_segments = 0
        for segment in expected_segments:
            match_info = segment_matches[segment["segment_index"]]
            matched_indices = sorted(match_info["matched_audio_indices"])
            scores = match_info["scores"]
            if matched_indices:
                matched_segments += 1
                extra_indices = segment_extra_indices.get(segment["segment_index"], [])
                combined_indices = sorted(set(matched_indices + extra_indices))
                start = min(audio_words[i]["start"] for i in combined_indices)
                end = max(audio_words[i]["end"] for i in combined_indices)
                similarity = sum(scores) / len(scores)
                matched_text = " ".join(audio_words[i]["word"] for i in combined_indices)
                status = "matched"
            else:
                missing_segments += 1
                start = None
                end = None
                similarity = 0.0
                matched_text = ""
                status = "missing"
            diff_result = self._inline_differ.diff(
                segment["expected_text"],
                matched_text,
                segment_id=segment["segment_id"],
            )
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
                    "inline_diff": diff_result.inline_diff,
                    "windowed_diffs": diff_result.windowed_diffs,
                }
            )

        extra_entries = self._build_extra_audio_entries(
            audio_words,
            alignment,
            reassigned_audio_indices,
        )
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
        excluded_indices: set[int] | None = None,
    ) -> list[dict]:
        extra_indices = [
            step["audio_index"]
            for step in alignment
            if step["op"] == "skip_audio"
            and (excluded_indices is None or step["audio_index"] not in excluded_indices)
        ]
        extra_entries: list[dict] = []
        if not extra_indices:
            return extra_entries
        current: list[int] = []
        for idx in extra_indices:
            if not current or idx == current[-1] + 1:
                current.append(idx)
                continue
            entry = self._extra_entry_for_indices(audio_words, current)
            if entry is not None:
                extra_entries.append(entry)
            current = [idx]
        if current:
            entry = self._extra_entry_for_indices(audio_words, current)
            if entry is not None:
                extra_entries.append(entry)
        return extra_entries

    def _extra_entry_for_indices(self, audio_words: list[dict], indices: list[int]) -> dict | None:
        start = audio_words[indices[0]]["start"]
        end = audio_words[indices[-1]]["end"]
        recognized_text = " ".join(audio_words[i]["word"] for i in indices)
        if self._equivalencies.is_ignorable_extra(recognized_text):
            return None
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

    def _build_transcription_cache_key(
        self,
        path: Path,
        vad_parameters: dict[str, float | int | None] | None,
    ) -> dict[str, object]:
        return {
            "cache_version": "1",
            "audio_path": str(path.resolve()),
            "model_name": self.model_name,
            "compute_type": self.compute_type,
            "vad_filter": self.vad_filter,
            "vad_parameters": vad_parameters,
            "remove_fillers": self.remove_fillers,
            "filler_words": sorted(self.filler_words),
            "transcriber": "faster_whisper",
        }

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
