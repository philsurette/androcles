from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.play import Play
from stager.domain.segment import DescriptionSegment, DirectionSegment, Segment, SimultaneousSegment, SpeechSegment
from stager.audio.cleaned_audio_selector import CleanedAudioSelector
from stager.playbook.cue_selection import CueSelection
from stager.shared import paths


@dataclass
class PlaybookCueSelector:
    play: Play
    paths: paths.PathConfig
    audio_selector: CleanedAudioSelector | None = None

    def select_for_block(self, block: RoleBlock) -> CueSelection:
        preceding = []
        for candidate in self.play.blocks:
            if candidate is block:
                break
            if candidate.block_id.part_id != block.block_id.part_id:
                continue
            preceding.append(candidate)
        for candidate in reversed(preceding):
            selection = self._selection_for_candidate(candidate)
            if selection is not None:
                return selection
        return self._first_line_selection(block)

    def _selection_for_candidate(self, block) -> CueSelection | None:
        if isinstance(block, (TitleBlock, DescriptionBlock, DirectionBlock)):
            segment = self._first_narrator_segment(block.segments)
            if segment is None:
                return None
            return self._narrator_selection(text=self._display_text_for_block(block), segment=segment)
        if isinstance(block, RoleBlock):
            spoken = self._last_spoken_segment(block)
            if spoken is not None:
                return spoken
            narrator_segment = self._first_narrator_segment(block.segments)
            if narrator_segment is not None:
                return self._narrator_selection(text=narrator_segment.text, segment=narrator_segment)
        return None

    def _last_spoken_segment(self, block: RoleBlock) -> CueSelection | None:
        for segment in reversed(block.segments):
            if isinstance(segment, SpeechSegment) and not segment.role.startswith("_"):
                return CueSelection(
                    speaker=segment.role,
                    source_role=segment.role,
                    text=segment.text,
                    audio_path=self._segment_path(segment.role, str(segment.segment_id)),
                )
            if isinstance(segment, SimultaneousSegment):
                source_role = segment.roles[0]
                return CueSelection(
                    speaker=block.callout or ", ".join(segment.roles),
                    source_role=source_role,
                    text=segment.text,
                    audio_path=self._segment_path(source_role, str(segment.segment_id)),
                )
        return None

    def _first_narrator_segment(self, segments: list[Segment]) -> Segment | None:
        for segment in segments:
            if isinstance(segment, (DescriptionSegment, DirectionSegment)):
                return segment
            if isinstance(segment, SpeechSegment) and segment.role == "_NARRATOR":
                return segment
        return None

    def _first_line_selection(self, block: RoleBlock) -> CueSelection:
        part = self.play.getPart(block.block_id.part_id)
        if part and part.title:
            title_block = next((candidate for candidate in part.blocks if isinstance(candidate, TitleBlock)), None)
            if title_block is not None and title_block.segments:
                return self._narrator_selection(
                    text=part.title,
                    segment=title_block.segments[0],
                )
        return CueSelection(
            speaker="_NARRATOR",
            source_role="_NARRATOR",
            text=self.play.title,
            audio_path=self.paths.segments_dir / "_NARRATOR" / "title.wav",
        )

    def _narrator_selection(self, text: str, segment: Segment) -> CueSelection:
        return CueSelection(
            speaker="_NARRATOR",
            source_role="_NARRATOR",
            text=text,
            audio_path=self._segment_path("_NARRATOR", str(segment.segment_id)),
        )

    def _display_text_for_block(self, block: TitleBlock | DescriptionBlock | DirectionBlock) -> str:
        if isinstance(block, TitleBlock):
            return block.heading
        return block.text

    def _segment_path(self, role: str, segment_id: str) -> Path:
        if self.audio_selector is None:
            return self.paths.segments_dir / role / f"{segment_id}.wav"
        return self.audio_selector.segment_path(role, segment_id)
