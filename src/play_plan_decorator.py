from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from audio_plan import AudioPlan, PlanItem

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Union

from play_text import PlayText, Block, MetaBlock
from chapter_builder import Chapter
from clip import SegmentClip, CalloutClip, SegmentClip, Silence
from audio_plan import AudioPlan, PlanItem
import paths
from paths import Paths
from spacing import Spacings

@dataclass
class PlayPlanDecorator(ABC):
    play: PlayText
    plan: AudioPlan
    paths: Paths = field(default_factory=Paths)
    spacings: Spacings = field(default_factory=Spacings)
    preamble_leading_silence_ms = 500
    epilogue_trailing_silence_ms = 1000

    @abstractmethod
    def add_section_preamble(self, part_no: int):
        raise RuntimeError("not implemented")
    
    @abstractmethod
    def add_project_preamble(self, part_no: int):
        raise RuntimeError("not implemented")

    @abstractmethod
    def add_section_epilog(self, part_no: int):
        raise RuntimeError("not implemented")

    @abstractmethod
    def add_project_epilog(self, part_no: int):
        raise RuntimeError("not implemented")
    
    def _add_recording(self, 
                           file_name: str, 
                           text: str, 
                           silence_ms: int) -> None:
        self._add_clip(
            folder=paths.RECORDINGS_DIR,
            file_name=file_name,
            text=text,
            following_silence_ms=silence_ms      
        )
    
    def _add_clip(self, 
            folder: Path, 
            file_name: str, 
            text: str, 
            following_silence_ms: int = 0,
            ) -> None:
        path = folder / f"{file_name}.wav"
        self.plan.addClip(
            SegmentClip(
                path=path,
                text=text,
                role=None,
                clip_id=None,
                length_ms=self.paths.get_audio_length_ms(path),
            ),
            following_silence_ms
        )

    def _add_snippet(self,
            file_name: str, 
            text: str = None, 
            following_silence_ms: int = 0,
        ) -> None:
        if text is None:
            text = file_name
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=self.paths.audio_snippets
        )

    def _add_words(self,
            file_name: str, 
            text: str = None, 
            sentence_start = False,
            sentence_end = False,
            phrase_end = False,
            following_silence_ms: int = None,
            folder: Path = None
        ) -> None:
        if folder is None:
            folder = self.paths.audio_snippets
        if text is None:
            text = file_name
            if sentence_start is True:
                text = text.capitalize()
            if sentence_end is True:
                text = f"{text}."
            elif phrase_end is True:
                text = f"{text},"
        if following_silence_ms is None:
            if sentence_end is True:
                following_silence_ms = self.spacings.segment
            elif phrase_end is True:
                following_silence_ms = self.spacings.comma
            else:
                following_silence_ms = self.spacings.word
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=folder
        )

    def _add_sentence(self,
            file_name: str, 
            text: str = None, 
            following_silence_ms: int = None,
            folder: Path = None
        ) -> None:
        if following_silence_ms is None:
            following_silence_ms = self.spacings.segment
        if folder is None:
            folder = self.paths.audio_snippets
        if text is None:
            text = f"{file_name.capitalize()}."
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=folder
        )
    
    def _add_title_by_author(self):
        self._add_recording(
            file_name="_TITLE",
            text=f"{self.play.title},",
            silence_ms=self.spacings.comma
        )
        self._add_words(
            file_name="by",
        )
        self._add_recording(
            file_name="_AUTHOR",
            text=f"{self.play.author}.",
            silence_ms=0
        )        

@dataclass
class LibrivoxPlayPlanDecorator(PlayPlanDecorator):
    preamble_leading_silence_ms = 1000
    epilog_trailing_silence_ms = 5000    
    librivox_snippets: Path = field(init=False)

    def __post_init__(self):
        self.librivox_snippets = self.paths.audio_snippets / 'librivox'

    def add_section_preamble(self, part_no: int):
        self.plan.add_silence(self.preamble_leading_silence_ms)
        self._add_words(f"section {part_no} of", sentence_start=True)
        self._add_title_by_author()
        self.plan.add_silence(self.spacings.segment)
        self._add_sentence(
            "this librivox recording is in the public domain",
            folder=self.librivox_snippets
        )        
        self.plan.add_silence(self.spacings.paragraph)
    
    def add_project_preamble(self, part_no: int):
        self.plan.add_silence(self.preamble_leading_silence_ms)
        self._add_words(f'section {part_no} of', sentence_start=True)
        self._add_recording(
            file_name="_TITLE",
            text=f"""{self.play.title}. """,
            silence_ms=self.spacings.segment,
        )
        self._add_sentence(
            "this is a LibriVox recording",
            folder=self.librivox_snippets
        )
        self._add_sentence(
            "all LibriVox recordings are in the public domain",
            folder=self.librivox_snippets
        )
        self._add_words(
            "for more information or to volunteer",
            sentence_start=True,
            phrase_end=True,
            folder=self.librivox_snippets
        )
        self._add_words(
            "please visit librivox dot org",
            sentence_end=True,
            folder=self.librivox_snippets
        )
        self._add_words(
            file_name="read by",
            sentence_start=True
        )
        self._add_recording(
            file_name="_READER",
            text="Phil Surette.",
            silence_ms=self.spacings.segment
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
    
@dataclass
class DefaultPlayPlanDecorator(PlayPlanDecorator):
    def add_section_preamble(self, part_no: int):
        return
    
    def add_project_preamble(self, part_no: int):
        self.plan.add_silence(self.preamble_leading_silence_ms)

    def add_section_epilog(self, part_no: int):
        return

    def add_project_epilog(self, part_no: int):
        self.plan.add_silence(self.epilogue_trailing_silence_ms)
