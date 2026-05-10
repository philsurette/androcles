from dataclasses import dataclass
@dataclass(frozen=False)
class Chapter:
    block_id: str
    title: str
    offset_ms: int | None = None
