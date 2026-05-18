from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import wave

from stager.domain.play import Play, Role
from stager.domain.segment import SimultaneousSegment, SpeechSegment
from stager.shared import paths


@dataclass(frozen=True)
class VoiceAnalysisResult:
    actor: str
    role: str
    segment_count: int
    word_count: int
    total_duration_seconds: float
    speech_active_seconds: float
    speaking_rate_wpm: float | None
    pitch_center_hz: float | None
    confidence: float
    confidence_reason: str

    def to_dict(self) -> dict:
        return {
            "actor": self.actor,
            "role": self.role,
            "segment_count": self.segment_count,
            "word_count": self.word_count,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "speech_active_seconds": round(self.speech_active_seconds, 3),
            "speaking_rate_wpm": round(self.speaking_rate_wpm, 2) if self.speaking_rate_wpm is not None else None,
            "pitch_center_hz": round(self.pitch_center_hz, 2) if self.pitch_center_hz is not None else None,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
        }


@dataclass(frozen=True)
class VoiceAnalysisReport:
    results: tuple[VoiceAnalysisResult, ...]
    json_path: Path


@dataclass
class VoiceProfileAnalyzer:
    paths_config: paths.PathConfig
    play: Play
    silence_threshold: int = 500

    def analyze(self, *, actor: str, role: str | None = None) -> VoiceAnalysisReport:
        roles = [role] if role is not None else [
            candidate.name for candidate in self.play.roles if not candidate.meta and not candidate.name.startswith("_")
        ]
        results = tuple(self._analyze_role(actor=actor, role_name=role_name) for role_name in roles)
        path = self.paths_config.audio_out_dir / "voice_analysis" / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "play_id": self.paths_config.play_name,
                    "results": [result.to_dict() for result in results],
                    "voice_profiles_yaml_suggestions": {
                        f"{result.actor}@{result.role}": {
                            "speaking_rate_wpm": result.to_dict()["speaking_rate_wpm"],
                            "confidence": result.confidence,
                            "source": "analysis",
                            "speech_active_seconds": result.to_dict()["speech_active_seconds"],
                            "word_count": result.word_count,
                        }
                        for result in results
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return VoiceAnalysisReport(results=results, json_path=path)

    def _analyze_role(self, *, actor: str, role_name: str) -> VoiceAnalysisResult:
        role = self.play.getRole(role_name)
        if role is None:
            raise RuntimeError(f"Unknown role {role_name!r}")
        segment_text = self._role_segment_text(role)
        segment_ids = list(role.segments().values())
        flat_segment_ids = [segment_id for ids in segment_ids for segment_id in ids]
        word_count = self._word_count(" ".join(segment_text))
        total_frames = 0
        active_frames = 0
        sample_rate = None
        pitch_samples: list[int] = []
        for segment_id in flat_segment_ids:
            path = self.paths_config.segments_dir / role_name / f"{segment_id}.wav"
            if not path.exists():
                raise RuntimeError(f"Audio file missing: {paths.display_path(path)}")
            audio = self._read_wav(path)
            if sample_rate is None:
                sample_rate = audio.sample_rate_hz
            elif sample_rate != audio.sample_rate_hz:
                raise RuntimeError(
                    f"Voice analysis expected consistent sample rates but found {audio.sample_rate_hz} Hz "
                    f"in {paths.display_path(path)}"
                )
            total_frames += len(audio.samples)
            active = [sample for sample in audio.samples if abs(sample) >= self.silence_threshold]
            active_frames += len(active)
            pitch_samples.extend(audio.samples)
        sample_rate = sample_rate or 1
        total_duration_seconds = total_frames / sample_rate
        speech_active_seconds = active_frames / sample_rate
        speaking_rate_wpm = None
        if speech_active_seconds > 0 and word_count > 0:
            speaking_rate_wpm = word_count / (speech_active_seconds / 60)
        confidence, reason = self._confidence(
            word_count=word_count,
            speech_active_seconds=speech_active_seconds,
            segment_count=len(flat_segment_ids),
        )
        return VoiceAnalysisResult(
            actor=actor,
            role=role_name,
            segment_count=len(flat_segment_ids),
            word_count=word_count,
            total_duration_seconds=total_duration_seconds,
            speech_active_seconds=speech_active_seconds,
            speaking_rate_wpm=speaking_rate_wpm,
            pitch_center_hz=self._pitch_center(pitch_samples, sample_rate),
            confidence=confidence,
            confidence_reason=reason,
        )

    def _role_segment_text(self, role: Role) -> list[str]:
        texts = []
        for block in role.blocks:
            for segment in block.segments:
                if isinstance(segment, SpeechSegment) and segment.role == role.name:
                    texts.append(segment.text)
                elif isinstance(segment, SimultaneousSegment) and role.name in segment.roles:
                    texts.append(segment.text)
        return texts

    def _word_count(self, text: str) -> int:
        return len(re.findall(r"[A-Za-z0-9']+", text))

    def _confidence(self, *, word_count: int, speech_active_seconds: float, segment_count: int) -> tuple[float, str]:
        if speech_active_seconds >= 60 or word_count >= 150:
            if segment_count >= 5:
                return 0.9, "enough speech-active audio or words across multiple segments"
            return 0.7, "enough speech-active audio or words, but few segments"
        return 0.35, "sparse role; tempo estimate should not drive automatic strategy selection"

    def _pitch_center(self, samples: list[int], sample_rate_hz: int) -> float | None:
        active_indices = [index for index, sample in enumerate(samples) if abs(sample) >= self.silence_threshold]
        if len(samples) < 2 or not active_indices:
            return None
        voiced_samples = samples[active_indices[0] : active_indices[-1] + 1]
        crossings = 0
        previous = voiced_samples[0]
        for sample in voiced_samples[1:]:
            if (previous < 0 <= sample) or (previous > 0 >= sample):
                crossings += 1
            previous = sample
        duration_seconds = len(voiced_samples) / sample_rate_hz
        if duration_seconds <= 0 or crossings == 0:
            return None
        return crossings / (2 * duration_seconds)

    def _read_wav(self, path: Path) -> "_WavAudio":
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            if sample_width != 2:
                raise RuntimeError(f"Voice analysis supports 16-bit WAV files: {paths.display_path(path)}")
            frames = wav.readframes(wav.getnframes())
            samples = []
            frame_width = sample_width * channels
            for offset in range(0, len(frames), frame_width):
                samples.append(int.from_bytes(frames[offset : offset + sample_width], "little", signed=True))
            return _WavAudio(sample_rate_hz=wav.getframerate(), samples=tuple(samples))


@dataclass(frozen=True)
class _WavAudio:
    sample_rate_hz: int
    samples: tuple[int, ...]
