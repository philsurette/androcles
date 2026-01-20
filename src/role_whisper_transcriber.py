#!/usr/bin/env python3
"""Transcribe a role recording with Whisper and write a plain text transcript."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import subprocess
import tempfile

from faster_whisper import WhisperModel

import paths
from vad_config import VadConfig
from whisper_model_store import WhisperModelStore


@dataclass
class RoleWhisperTranscriber:
    role: str
    paths: paths.PathConfig = field(default_factory=paths.current)
    model_name: str = "medium.en"
    device: str = "cpu"
    compute_type: str = "int8"
    whisper_store: WhisperModelStore | None = None
    vad_filter: bool = True
    vad_config: VadConfig | None = None
    no_speech_threshold: float | None = None
    log_prob_threshold: float | None = None
    condition_on_previous_text: bool = True
    initial_prompt: str | None = None
    clip_from_ms: int = 0
    clip_length_ms: int | None = None

    _logger: logging.Logger = field(init=False, repr=False)
    _model: WhisperModel | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        if self.whisper_store is None:
            self.whisper_store = WhisperModelStore(
                paths=self.paths,
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
            )

    def transcribe(self, recording_path: Path | None = None, out_path: Path | None = None) -> Path:
        path = recording_path or (self.paths.recordings_dir / f"{self.role}.wav")
        if not path.exists():
            raise RuntimeError(f"Recording not found for role {self.role}: {path}")
        clip_path = self._clip_audio(path)
        if clip_path is not None:
            path = clip_path
        vad_parameters = None
        if self.vad_filter and self.vad_config is not None:
            vad_parameters = self.vad_config.to_transcribe_parameters()
        vad_label = self._format_vad_label(vad_parameters)
        model = self._load_model()
        transcribe_kwargs = {
            "vad_filter": self.vad_filter,
            "vad_parameters": vad_parameters,
            "condition_on_previous_text": self.condition_on_previous_text,
        }
        if self.no_speech_threshold is not None:
            transcribe_kwargs["no_speech_threshold"] = self.no_speech_threshold
        if self.log_prob_threshold is not None:
            transcribe_kwargs["log_prob_threshold"] = self.log_prob_threshold
        if self.initial_prompt is not None:
            transcribe_kwargs["initial_prompt"] = self.initial_prompt
        segments, info = model.transcribe(
            str(path),
            **transcribe_kwargs,
        )
        lines: list[str] = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            start_ms = int(round(segment.start * 1000))
            end_ms = int(round(segment.end * 1000))
            lines.append(f"{start_ms}-{end_ms}: {text}")
        target = out_path or (self.paths.audio_out_dir / f"{self.role}_nlp.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        self._logger.info("Wrote whisper transcript to %s (%s)", target, vad_label)
        return target

    def _load_model(self) -> WhisperModel:
        if self.whisper_store is None:
            raise RuntimeError("Whisper model store is not configured")
        if self._model is None:
            self._model = self.whisper_store.load(self.model_name)
        return self._model

    def _clip_audio(self, path: Path) -> Path | None:
        if self.clip_from_ms <= 0 and self.clip_length_ms is None:
            return None
        if self.clip_from_ms < 0:
            raise RuntimeError("clip_from_ms must be >= 0")
        if self.clip_length_ms is not None and self.clip_length_ms <= 0:
            raise RuntimeError("clip_length_ms must be > 0 when provided")
        start_seconds = self.clip_from_ms / 1000.0
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            str(path),
        ]
        if self.clip_length_ms is not None:
            cmd.extend(["-t", f"{self.clip_length_ms / 1000.0:.3f}"])
        cmd.extend(["-ar", "16000", "-ac", "1", str(tmp_path)])
        subprocess.run(cmd, check=True)
        self._logger.info(
            "Clipped audio for %s to %s (from %dms, length %s)",
            self.role,
            tmp_path,
            self.clip_from_ms,
            f"{self.clip_length_ms}ms" if self.clip_length_ms is not None else "full",
        )
        return tmp_path

    def _format_vad_label(self, vad_parameters: dict[str, float | int | None] | None) -> str:
        if not self.vad_filter:
            return "vad_filter=off"
        if vad_parameters:
            return f"vad_filter=on, vad_params={vad_parameters}"
        return "vad_filter=on, vad_params=default"
