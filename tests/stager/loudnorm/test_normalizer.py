from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from stager.loudnorm.normalizer import Normalizer


INPUT_SUMMARY = """
Input Integrated:    -23.9 LUFS
Input True Peak:      -2.9 dBTP
Input LRA:             5.0 LU
Input Threshold:     -34.5 LUFS
"""

OUTPUT_SUMMARY = """
Output Integrated:   -21.0 LUFS
Output True Peak:     -1.0 dBTP
Output LRA:           10.0 LU
Output Threshold:    -31.0 LUFS
"""


class FakeRunner:
    def __init__(self, *results: subprocess.CompletedProcess[str]) -> None:
        self.results = list(results)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        assert capture_output is True
        assert text is True
        return self.results.pop(0)


def _completed(stderr: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["ffmpeg"], returncode=returncode, stdout="", stderr=stderr)


def test_normalizer_runs_two_pass_loudnorm_with_measured_values() -> None:
    runner = FakeRunner(_completed(INPUT_SUMMARY), _completed(OUTPUT_SUMMARY))

    result = Normalizer(command_runner=runner).normalize("input.wav", "output.wav")

    assert result.input_measurements["lufs"].value == -23.9
    assert result.normalized_measurements["lufs"].value == -21.0
    assert runner.commands[0] == [
        "ffmpeg",
        "-i",
        "input.wav",
        "-af",
        "loudnorm=print_format=summary:i=-21:tp=-1:lra=10",
        "-f",
        "null",
        "-",
    ]
    assert runner.commands[1] == [
        "ffmpeg",
        "-y",
        "-i",
        "input.wav",
        "-map_metadata",
        "0",
        "-ar",
        "44100",
        "-af",
        "loudnorm=print_format=summary:i=-21:tp=-1:lra=10:measured_i=-23.9:measured_tp=-2.9:measured_lra=5.0:measured_thresh=-34.5",
        "output.wav",
    ]


def test_normalizer_preserves_mp3_bitrate_and_metadata() -> None:
    runner = FakeRunner(_completed(INPUT_SUMMARY), _completed(OUTPUT_SUMMARY))

    Normalizer(command_runner=runner).normalize("input.mp3", "output.mp3")

    assert runner.commands[1][-5:] == ["-b:a", "128k", "-map_metadata", "0", "output.mp3"]


def test_normalizer_raises_when_measure_command_fails() -> None:
    runner = FakeRunner(_completed("ffmpeg exploded", returncode=1))

    with pytest.raises(RuntimeError, match="Failed to measure loudness with ffmpeg: ffmpeg exploded"):
        Normalizer(command_runner=runner).measure("input.wav")


def test_normalizer_copies_unnormalizable_audio(tmp_path: Path) -> None:
    source = tmp_path / "silence.wav"
    output = tmp_path / "normalized.wav"
    source.write_bytes(b"audio")
    runner = FakeRunner(
        _completed(
            """
Input Integrated:     -inf LUFS
Input True Peak:      -inf dBTP
Input LRA:             0.0 LU
Input Threshold:      -inf LUFS
"""
        )
    )

    result = Normalizer(command_runner=runner).normalize(str(source), str(output))

    assert output.read_bytes() == b"audio"
    assert result.normalized_measurements.normalizable is False
    assert len(runner.commands) == 1
