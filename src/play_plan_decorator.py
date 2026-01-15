from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path

from play import Play
from clip import SegmentClip
from audio_plan import AudioPlan
import paths
from paths import Paths
from spacing import Spacings

@dataclass
class PlayPlanDecorator(ABC):
    play: Play
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
    
    def _add_announcement(
        self,
        file_name: str,
        text: str,
        silence_ms: int,
    ) -> None:
        base = paths.SEGMENTS_DIR / "_ANNOUNCER"
        path = base / f"{file_name}.wav"
        if not path.exists():
            raise RuntimeError(f"Announcer recording not found at {path}")

        self.plan.addClip(
            SegmentClip(
                path=path,
                text=text,
                role=None,
                clip_id=None,
                length_ms=self.paths.get_audio_length_ms(path),
            ),
            silence_ms,
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
        self._add_announcement(
            file_name="title",
            text=f"{self.play.title},",
            silence_ms=self.spacings.comma
        )
        self._add_words(
            file_name="by",
        )
        self._add_announcement(
            file_name="author",
            text=f"{self.play.author}.",
            silence_ms=0
        )        

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
