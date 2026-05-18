from __future__ import annotations
from dataclasses import dataclass, field
from stager.loudnorm.target import Target
from stager.loudnorm.result import Result


@dataclass(frozen=True)
class LoudnessProfile:
    lufs: Target
    true_peak: Target
    loudness_range: Target
    loudness_threshold: Target

    @classmethod
    def librivox(cls) -> "LoudnessProfile":
        return cls(
            lufs=Target(too_low=-27, low=-23, high=-21, too_high=-17, target=-21),
            true_peak=Target(target=-1, too_low=-3, low=-2, high=-1, too_high=0),
            loudness_range=Target(target=10, too_low=5, low=7, high=12, too_high=15),
            loudness_threshold=Target(target=-40, too_low=-90, low=-40, high=-25, too_high=-20),
        )

    @classmethod
    def podcast(cls) -> "LoudnessProfile":
        return cls(
            lufs=Target(too_low=-20, low=-16, high=-14, too_high=-10, target=-14),
            true_peak=Target(target=-1, too_low=-3, low=-2, high=-1, too_high=0),
            loudness_range=Target(target=10, too_low=5, low=7, high=12, too_high=15),
            loudness_threshold=Target(target=-40, too_low=-90, low=-40, high=-25, too_high=-20),
        )

    @classmethod
    def voice_profile(cls) -> "LoudnessProfile":
        return cls.librivox()


@dataclass
class Metric:
    name: str # identifier with no meaning in ffmpeg
    abbrev: str # for rendering
    output_name: str # name displaced in ffmpeg outputs
    output_unit: str # units displayed in ffmpeg output
    option: str # name of option in ffmpeg filter
    is_controllable: bool # not all options can be used to control the algorithm
    target_range: Target

    def check(self, value: float) -> Result:
        return self.target_range.check(value)
    
    def as_filter_option(self):
        return f"{self.option}={self.target_range.target}"
    
    def __str__(self):
        return self.abbrev

@dataclass
class Metrics:
    profile: LoudnessProfile = field(default_factory=LoudnessProfile.librivox)

    @classmethod
    def for_profile(cls, profile: LoudnessProfile) -> "Metrics":
        return cls(profile=profile)

    def _create_metrics(self) -> list[Metric]:
        return [
            Metric(
                name="lufs",
                abbrev="lufs",
                output_name="Integrated",
                output_unit="LUFS",
                option='i',  
                is_controllable=True,
                target_range=self.profile.lufs,
            ),
            Metric(
                name="true_peak",
                abbrev="peak",
                output_name="True Peak",
                output_unit="dBTP",
                option='tp',
                is_controllable=True,
                target_range=self.profile.true_peak,
            ), 
            Metric(
                name="loudness_range",
                abbrev="range",
                output_name="LRA",
                output_unit="LU",
                option='lra',
                is_controllable=True,
                target_range=self.profile.loudness_range,
            ), 
            Metric(
                name="loudness_threshold",
                abbrev="thresh",
                output_name="Threshold",
                output_unit="LUFS",
                option='thresh',
                is_controllable=False,
                target_range=self.profile.loudness_threshold,
            )
        ]

    def __post_init__(self):
        self.metrics = self._create_metrics()
    
    def for_name(self, name: str) -> Metric:
        return next(m for m in self.metrics if (m.name == name or m.abbrev == name))
    
    def list(self) -> list[Metric]:
        return self.metrics
    
    def controllable_metrics(self):
        return [m for m in self.metrics if m.is_controllable]
