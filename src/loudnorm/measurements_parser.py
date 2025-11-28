from loudnorm.measurements import Measurement, Measurements, Phase
from loudnorm.metric import Metrics
from dataclasses import dataclass, field
import re
import logging
logger = logging.getLogger(__name__)

@dataclass
class MeasurementsParser:
    metrics: Metrics# = field(default_factory=Metrics)
    """
    Sample output:
    Input Integrated:    -23.9 LUFS
    Input True Peak:      -2.9 dBTP
    Input LRA:             5.0 LU
    Input Threshold:     -34.5 LUFS
    """
    def get_measurements(self, output: str, phase: Phase) -> Measurements:
        match = self.get_pattern(phase).search(output)
        if not match:
            logger.info(output)
            raise ValueError("Could not parse measurements from output.")  # Or handle the error as needed

        measurements: Measurements = Measurements()
        for name, value in match.groupdict().items():
            metric = self.metrics.for_name(name)
            normalizable = True
            if value=="-inf":
                measurement = -100 # should work for LUFS, dBTP, and LU unites
                normalizable = False
            elif value=="+inf":
                measurement = +100
                normalizable = False
            else:
                measurement = float(value)
            measurements[name] = Measurement(
                metric=self.metrics.for_name(name),
                value=float(measurement),
                normalizable=normalizable
                )
        return measurements

    def get_pattern(self, phase: Phase) -> re.Pattern:
        r""" FYI the pattern will look something like this could have Output at the start
^Input Integrated:\s+(?P<lufs>[-+]?\d*(?:\.\d+)?)\s+LUFS$
^Input True Peak:\s+(?P<true_peak>[-+]?\d*(?:\.\d+)?)\s+dBTP$
^Input LRA:\s+(?P<loudness_range>[-+]?\d*(?:\.\d+)?)\s+LU$
^Input Threshold:\s+(?P<loudness_threshold>[-+]?\d*(?:\.\d+)?)\s+LUFS$
        """
        float_pattern = r"(?:[-+]?\d*(?:\.\d+)?|-inf)" #(?:) is for non-capturing group
        # efforts to get this to work with re.VERBOSE did not meet with success...
        metric_patterns = []
        for metric in self.metrics.list():#self.targets.list_metrics():
            metric_patterns.append(
                fr"^{phase.prefix} {metric.output_name}:"\
                fr"\s+(?P<{metric.name}>{float_pattern})\s+{metric.output_unit}$"
            )
        return re.compile("\n".join(metric_patterns), re.MULTILINE)