from __future__ import annotations

import pytest

from stager.loudnorm.measurements import Phase
from stager.loudnorm.measurements_parser import MeasurementsParser
from stager.loudnorm.metric import Metrics


def test_parser_reads_input_measurements() -> None:
    output = """
Input Integrated:    -23.9 LUFS
Input True Peak:      -2.9 dBTP
Input LRA:             5.0 LU
Input Threshold:     -34.5 LUFS
"""

    measurements = MeasurementsParser(metrics=Metrics()).get_measurements(output, Phase.INPUT)

    assert measurements["lufs"].value == -23.9
    assert measurements["true_peak"].value == -2.9
    assert measurements["loudness_range"].value == 5.0
    assert measurements["loudness_threshold"].value == -34.5
    assert measurements.normalizable is True


def test_parser_marks_infinite_measurements_as_not_normalizable() -> None:
    output = """
Input Integrated:     -inf LUFS
Input True Peak:      -inf dBTP
Input LRA:             0.0 LU
Input Threshold:      -inf LUFS
"""

    measurements = MeasurementsParser(metrics=Metrics()).get_measurements(output, Phase.INPUT)

    assert measurements.normalizable is False
    assert measurements["lufs"].value == -100
    assert measurements["true_peak"].value == -100
    assert measurements["loudness_threshold"].value == -100


def test_parser_rejects_missing_measurements() -> None:
    with pytest.raises(ValueError, match="Could not parse measurements"):
        MeasurementsParser(metrics=Metrics()).get_measurements("not loudnorm output", Phase.INPUT)
