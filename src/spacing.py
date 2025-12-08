from dataclasses import dataclass, field
WORD_PAUSE_MS = 125
BLOCK_PAUSE_MS = 500
COMMA_PAUSE_MS = 250
PARAGRAPH_PAUSE_MS = 1000

SEGMENT_SPACING_MS=BLOCK_PAUSE_MS
CALLOUT_SPACING_MS=50

@dataclass
class Spacings:
    word: int = 125
    segment: int = 500
    comma: int = 250
    paragraph: int = 1000
    callout: int = 50
