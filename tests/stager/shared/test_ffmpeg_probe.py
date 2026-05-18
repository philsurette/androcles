from __future__ import annotations

import subprocess
from pathlib import Path
import logging

import pytest

from stager.shared.ffmpeg_probe import FfmpegProbe


FILTER_OUTPUT = """
Filters:
 TSC aresample         A->A       Resample audio data.
 ... asetrate          A->A       Change sample rate.
 ... atempo            A->A       Adjust audio tempo.
 ... highpass          A->A       Apply a high-pass filter.
 ... lowpass           A->A       Apply a low-pass filter.
 ... equalizer         A->A       Apply two-pole peaking equalization.
 ... acompressor       A->A       Audio compressor.
 ... volume            A->A       Change input volume.
 ... alimiter          A->A       Audio lookahead limiter.
 ... aecho             A->A       Add echoing.
 ... atrim             A->A       Pick one continuous section from the input.
 ... asetpts           A->A       Set PTS for audio frames.
 ... concat            N->N       Concatenate audio and video streams.
 ... loudnorm          A->A       EBU R128 loudness normalization
 ... adeclick          A->A       Remove impulsive noise from input audio.
 ... deesser           A->A       Apply de-essing to input audio.
 ... afftdn            A->A       Denoise audio samples with FFT.
 ... afwtdn            A->A       Denoise audio stream using Wavelets.
 ... anlmdn            A->A       Reduce broadband noise from stream.
 ... agate             A->A       Audio gate.
"""


class FakeRunner:
    def __init__(self, stdout: str = FILTER_OUTPUT, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=self.returncode,
            stdout=self.stdout,
            stderr="ffmpeg failed" if self.returncode else "",
        )


def test_probe_uses_project_config_and_prepends_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    bin_dir = tmp_path / "ffmpeg-full" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "ffmpeg").write_text("", encoding="utf-8")
    (bin_dir / "ffprobe").write_text("", encoding="utf-8")
    config_dir = tmp_path / ".quince"
    config_dir.mkdir()
    (config_dir / "ffmpeg.conf").write_text(f"ffmpeg_bin_dir={bin_dir}\n", encoding="utf-8")
    runner = FakeRunner()
    monkeypatch.setattr("stager.shared.ffmpeg_probe.subprocess.run", runner)
    monkeypatch.setenv("PATH", "/usr/bin")
    caplog.set_level(logging.INFO)

    installation = FfmpegProbe(working_dir=tmp_path, home_dir=tmp_path / "home").find_installation()

    assert installation.source == "config"
    assert installation.ffmpeg_path == bin_dir / "ffmpeg"
    assert installation.has_filter("adeclick") is True
    assert installation.missing_required_voice_profile_filters() == []
    assert runner.commands == [[str(bin_dir / "ffmpeg"), "-hide_banner", "-filters"]]
    assert str(bin_dir) == __import__("os").environ["PATH"].split(__import__("os").pathsep)[0]


def test_probe_warns_and_falls_back_to_path_when_config_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = FakeRunner(stdout=FILTER_OUTPUT.replace(" ... adeclick          A->A       Remove impulsive noise from input audio.\n", ""))
    monkeypatch.setattr("stager.shared.ffmpeg_probe.subprocess.run", runner)
    monkeypatch.setattr("stager.shared.ffmpeg_probe.shutil.which", lambda tool: f"/usr/bin/{tool}")
    caplog.set_level(logging.INFO)

    installation = FfmpegProbe(working_dir=tmp_path, home_dir=tmp_path / "home").find_installation()

    assert installation.source == "PATH"
    assert installation.ffmpeg_path == Path("/usr/bin/ffmpeg")
    assert installation.has_filter("adeclick") is False
    assert "No Quince FFmpeg config file found" in caplog.text
    assert "FFmpeg optional filter adeclick: not found" in caplog.text


def test_probe_fails_when_no_config_or_path_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("stager.shared.ffmpeg_probe.shutil.which", lambda tool: None)

    with pytest.raises(RuntimeError, match="Missing required audio tool\\(s\\): ffmpeg, ffprobe"):
        FfmpegProbe(working_dir=tmp_path, home_dir=tmp_path / "home").find_installation()


def test_probe_fails_when_configured_tools_are_missing(tmp_path: Path) -> None:
    config_dir = tmp_path / ".quince"
    config_dir.mkdir()
    (config_dir / "ffmpeg.conf").write_text(f"ffmpeg_bin_dir={tmp_path / 'missing'}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Configured FFmpeg tool\\(s\\) not found"):
        FfmpegProbe(working_dir=tmp_path, home_dir=tmp_path / "home").find_installation()
