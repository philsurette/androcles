#!/usr/bin/env python3
import sys
from pathlib import Path
import csv
import re
import statistics
from typing import Dict, List, Optional, Tuple

# ---------------------------
# Tunables
# ---------------------------
SLOW_SPM = 190.0
NORMAL_SPM = 230.0
FAST_SPM = 275.0

PAUSE_MS_COMMA = 250
PAUSE_MS_SEMICOLON_COLON = 300
PAUSE_MS_DASH = 200
PAUSE_MS_SENTENCE_END = 600
PAUSE_MS_ELLIPSIS = 800

SHORT_SENT_WORDS = 7  # urgency threshold

# ---------------------------
# CMUdict
# ---------------------------
def load_pronouncing_dict():
    try:
        import cmudict
        return cmudict.dict()
    except Exception:
        pass
    try:
        from nltk.corpus import cmudict as nltk_cmudict
        return nltk_cmudict.dict()
    except Exception:
        return None

CMU = load_pronouncing_dict()

# ---------------------------
# Tokenization
# ---------------------------
WORD_RE = re.compile(r"[A-Za-z0-9']+")

def words_in_text(text: str) -> List[str]:
    return WORD_RE.findall(text)

def count_words(text: str) -> int:
    return len(words_in_text(text))

# ---------------------------
# Syllables
# ---------------------------
def heuristic_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    count = len(groups)
    if w.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)

def cmu_syllables(word: str) -> Optional[int]:
    if CMU is None:
        return None
    w = word.lower()
    if w not in CMU:
        return None
    prons = CMU[w]
    return min(sum(1 for p in pron if p[-1].isdigit()) for pron in prons)

def syllables_in_word(word: str) -> int:
    s = cmu_syllables(word)
    return s if s is not None else heuristic_syllables(word)

def count_syllables(text: str) -> int:
    return sum(syllables_in_word(w) for w in words_in_text(text))

def count_complex_words(text: str) -> int:
    return sum(1 for w in words_in_text(text) if syllables_in_word(w) >= 3)

# ---------------------------
# Speech blocks
# ---------------------------
def split_speeches(text: str) -> List[str]:
    norm = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not norm:
        return []
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", norm) if b.strip()]
    if len(blocks) <= 1:
        blocks = [ln.strip() for ln in norm.splitlines() if ln.strip()]
    return blocks

def speech_length_lists(text: str) -> Tuple[List[int], List[int]]:
    speeches = split_speeches(text)
    wcs = [count_words(s) for s in speeches]
    scs = [count_syllables(s) for s in speeches]
    return wcs, scs

def speech_stats(text: str) -> Tuple[int, float, float, int, int]:
    speeches = split_speeches(text)
    if not speeches:
        return (0, 0.0, 0.0, 0, 0)
    wcs, scs = speech_length_lists(text)
    return (
        len(speeches),
        sum(scs)/len(scs),
        sum(wcs)/len(wcs),
        max(scs),
        max(wcs)
    )

# ---------------------------
# Pauses + punctuation counts
# ---------------------------
def punctuation_counts(text: str) -> Tuple[int, int, int, int]:
    """
    Returns (ellipses, dashes, colons, exclamations)
    """
    ellipses = len(re.findall(r"\.\.\.+", text))
    dashes = len(re.findall(r"—|--", text))
    colons = text.count(":")
    excls = text.count("!")
    return ellipses, dashes, colons, excls

def punctuation_pause_ms(text: str) -> int:
    ellipses, dashes, colons, _excls = punctuation_counts(text)

    t_no_ell = re.sub(r"\.\.\.+", "", text)
    commas = t_no_ell.count(",")
    semicolons = t_no_ell.count(";")
    ends = len(re.findall(r"[.!?]+", t_no_ell))

    return (
        ellipses * PAUSE_MS_ELLIPSIS +
        commas * PAUSE_MS_COMMA +
        (semicolons + colons) * PAUSE_MS_SEMICOLON_COLON +
        dashes * PAUSE_MS_DASH +
        ends * PAUSE_MS_SENTENCE_END
    )

# ---------------------------
# Breath groups
# ---------------------------
BREATH_SPLIT_RE = re.compile(r"[,\.;:!?]+|\n")

def breath_group_texts(text: str) -> List[str]:
    return [g.strip() for g in BREATH_SPLIT_RE.split(text) if g.strip()]

def breath_group_stats(text: str) -> Tuple[int, float, int, float]:
    """
    Returns (count, avg_syllables, max_syllables, stddev_syllables)
    """
    groups = breath_group_texts(text)
    if not groups:
        return (0, 0.0, 0, 0.0)
    scs = [count_syllables(g) for g in groups]
    avg = sum(scs)/len(scs)
    mx = max(scs)
    std = statistics.pstdev(scs) if len(scs) > 1 else 0.0
    return (len(scs), avg, mx, std)

# ---------------------------
# Sentences
# ---------------------------
SENT_SPLIT_RE = re.compile(r"[.!?]+|\n")

def sentence_texts(text: str) -> List[str]:
    t = re.sub(r"\.\.\.+", "", text)
    return [p.strip() for p in SENT_SPLIT_RE.split(t) if p.strip()]

def count_sentences(text: str) -> int:
    sents = sentence_texts(text)
    return len(sents) if sents else 0

# ---------------------------
# Readability
# ---------------------------
def gunning_fog_index(words: int, sentences: int, complex_words: int) -> float:
    if words == 0:
        return 0.0
    s = max(1, sentences)
    return 0.4 * ((words/s) + 100*(complex_words/words))

def smog_index(sentences: int, complex_words: int) -> float:
    s = max(1, sentences)
    return 1.0430 * (complex_words*(30/s))**0.5 + 3.1291

# ---------------------------
# Pacing metrics helpers
# ---------------------------
def nonempty_line_count(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip())

def urgency_index(text: str) -> float:
    sents = sentence_texts(text)
    if not sents:
        return 0.0
    short = sum(1 for s in sents if count_words(s) < SHORT_SENT_WORDS)
    return short / len(sents)

def volatility_index(speech_syllables: List[int]) -> float:
    if not speech_syllables:
        return 0.0
    mean = sum(speech_syllables)/len(speech_syllables)
    if mean == 0:
        return 0.0
    std = statistics.pstdev(speech_syllables) if len(speech_syllables) > 1 else 0.0
    return std / mean

# ---------------------------
# Main
# ---------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: wordcount.py DIR [output.csv]")
        sys.exit(1)

    indir = Path(sys.argv[1])
    outfile = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("wordcount.csv")

    texts: Dict[str, str]
