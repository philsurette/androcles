from dataclasses import dataclass, field
from pathlib import Path

from play_plan_decorator import PlayPlanDecorator


@dataclass
class LibrivoxPlayPlanDecorator(PlayPlanDecorator):
    preamble_leading_silence_ms = 1000
    epilog_trailing_silence_ms = 5000
    librivox_snippets: Path = field(init=False)

    def __post_init__(self):
        self.librivox_snippets = self.paths.audio_snippets / "librivox"

    def add_section_preamble(self, part_no: int):
        self.plan.add_silence(self.preamble_leading_silence_ms)
        self._add_words(f"section {part_no} of", sentence_start=True)
        self._add_title_by_author()
        self.plan.add_silence(self.spacings.segment)
        self._add_sentence(
            "this librivox recording is in the public domain",
            folder=self.librivox_snippets,
        )
        self.plan.add_silence(self.spacings.paragraph)

    def add_project_preamble(self, part_no: int):
        self.plan.add_silence(self.preamble_leading_silence_ms)
        self._add_words(f"section {part_no} of", sentence_start=True)
        self._add_recording(
            file_name="_TITLE",
            text=f"{self.play.title}. ",
            silence_ms=self.spacings.segment,
        )
        self._add_sentence(
            "this is a LibriVox recording",
            folder=self.librivox_snippets,
        )
        self._add_sentence(
            "all LibriVox recordings are in the public domain",
            folder=self.librivox_snippets,
        )
        self._add_words(
            "for more information or to volunteer",
            sentence_start=True,
            phrase_end=True,
            folder=self.librivox_snippets,
        )
        self._add_words(
            "please visit librivox dot org",
            sentence_end=True,
            folder=self.librivox_snippets,
        )
        self._add_words(
            file_name="read by",
            sentence_start=True,
        )
        self._add_recording(
            file_name="_READER",
            text="Phil Surette.",
            silence_ms=self.spacings.segment,
        )
        self.plan.add_silence(self.spacings.paragraph)
        self._add_title_by_author()
        self.plan.add_silence(self.spacings.paragraph)

    def add_section_epilog(self, part_no: int):
        self.plan.add_silence(self.spacings.paragraph)
        self._add_sentence(f"end of section {part_no}")
        self.plan.add_silence(self.epilog_trailing_silence_ms)

    def add_project_epilog(self, part_no: int):
        self.plan.add_silence(self.spacings.paragraph)
        self._add_sentence(f"end of section {part_no}")
        self.plan.add_silence(self.spacings.paragraph)
        self._add_words("end of", sentence_start=True)
        self._add_title_by_author()
        self.plan.add_silence(self.epilog_trailing_silence_ms)
