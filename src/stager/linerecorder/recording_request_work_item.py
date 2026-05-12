from __future__ import annotations

from dataclasses import dataclass

from stager.domain.block import RoleBlock
from stager.domain.segment import SimultaneousSegment, SpeechSegment


@dataclass(frozen=True)
class RecordingRequestWorkItem:
    block: RoleBlock
    segment: SpeechSegment | SimultaneousSegment

