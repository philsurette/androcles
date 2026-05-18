from __future__ import annotations
from dataclasses import dataclass, field
import subprocess
import logging
import shutil
from typing import Protocol

from stager.loudnorm.measurements_parser import MeasurementsParser
from stager.loudnorm.measurements import Measurements, Phase
from stager.loudnorm.metric import Metrics
from stager.loudnorm.score import Score
from stager.shared import paths
logger = logging.getLogger(__name__)    

EXECUTABLE="ffmpeg"
FILTER="loudnorm"


class CommandRunner(Protocol):
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        ...


@dataclass
class Normalizer:
    metrics: Metrics = field(default_factory=Metrics)
    command_runner: CommandRunner = subprocess.run
    measures_parser: MeasurementsParser = field(init=False)

    def __post_init__(self):
        self.measures_parser = MeasurementsParser(metrics = self.metrics)

    def measure(self, input_file: str) -> Measurements:
        options = [
            f"{FILTER}=print_format=summary",
        ]
        options.extend([m.as_filter_option() for m in self.metrics.controllable_metrics()])
        filter_spec = ":".join(options)
        measure_command = [
            EXECUTABLE,
            "-i", input_file,
            "-af", #audio format 
            filter_spec,
            "-f", "null", #don't capture output
            "-"
        ]

        logger.info(F"{' '.join(measure_command)}")
        measure_process = self._run_command(measure_command, "measure loudness")
        output = measure_process.stderr  # ffmpeg outputs loudness info to stderr
        logger.debug(output)

        return self.measures_parser.get_measurements(output, Phase.INPUT)


    def _normalize_audio(self,
                        input_file: str, 
                        output_file: str, 
                        measurements: Measurements) -> Measurements:
        if not measurements.normalizable:
            unmeasurable = Measurements()
            unmeasurable.score = Score.BAD
            unmeasurable.normalizable = False
            shutil.copy(input_file, output_file)
            return unmeasurable
        options = [
            f"{FILTER}=print_format=summary",
        ]
        options.extend([m.as_filter_option() for m in self.metrics.controllable_metrics()])
        options.extend([m.as_filter_option() for m in measurements.values()])
        filter_spec = ":".join(options)

        normalize_command = [
            EXECUTABLE,
            "-y", #answer yes to all questions
            "-i", input_file,
            "-map_metadata",
            "0",
            "-ar", "44100",
            "-af", #audio format
            filter_spec,
        ]
        # Preserve/force bitrate for mp3 outputs.
        if output_file.lower().endswith(".mp3"):
            normalize_command.extend(["-b:a", "128k"])
            # Preserve metadata from input.
            normalize_command.extend(["-map_metadata", "0"])
        normalize_command.append(output_file)
        logger.info(F"{' '.join(normalize_command)}")

        normalize_process = self._run_command(normalize_command, "normalize loudness")
        output = normalize_process.stderr  # ffmpeg outputs loudness info to stderr
        logger.debug(output)
        output_measures: Measurements = self.measures_parser.get_measurements(
            output, Phase.OUTPUT)
        return output_measures

    def _run_command(self, command: list[str], action: str) -> subprocess.CompletedProcess[str]:
        result = self.command_runner(command, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            detail = f": {stderr}" if stderr else ""
            raise RuntimeError(f"Failed to {action} with ffmpeg{detail}")
        return result
    
    def normalize(self, input_file: str, output_file:str=None) -> NormalizationResult:
        if not output_file:
            output_file = input_file.replace(".mp3", ".norm.mp3")
        
        initial: Measurements = self.measure(input_file)
        normalized: Measurements = self._normalize_audio(
            input_file=input_file,
            output_file=output_file,
            measurements=initial
        )
        return NormalizationResult(
            input_path=input_file, 
            normalized_path=output_file, 
            input_measurements=initial, 
            normalized_measurements=normalized)
    
@dataclass
class NormalizationResult:
    input_path: str
    normalized_path: str
    input_measurements: Measurements
    normalized_measurements: Measurements

    def render(self):
        r = [self.normalized_measurements.score.checkmark]
        r.append(f"{paths.display_path(self.normalized_path)}←{paths.display_path(self.input_path)}")
        for m in self.normalized_measurements.values():
            r.append(f"{m.score.checkmark}{m.metric.abbrev}:{m.value}")
        if not self.normalized_measurements.normalizable:
            r.append(f"copied from un-normalizable input")
            for m in [i for i in self.input_measurements.values() if not i.normalizable]:
                r.append(f"{m.score.checkmark}{m.metric.abbrev}:{m.value}")

        return " ".join(r)
