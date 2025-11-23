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
# stats.csv writer
# ---------------------------
def write_stats_csv(stats_path: Path):
    rows = [
        ("Character",
         "Character name, taken from each .txt filename (stem)."),
        ("PerfMin",
         "Estimated total spoken time in minutes at the normal syllable rate, plus estimated punctuation pauses."),
        ("Syllables",
         "Estimated syllables spoken by the character, using CMUdict when available and a vowel-group heuristic as fallback."),
        ("WordCount",
         "Number of word tokens spoken by the character, based on a simple regex tokenizer."),
        ("Sentences",
         "Count of sentence-like units, split on . ! ? or line breaks (ellipses ignored for splitting)."),
        ("Speeches",
         "Number of speech blocks the character has. A block is a paragraph separated by blank lines; if none, each nonempty line counts as a block."),
        ("FogIndex",
         "Gunning Fog readability estimate using words per sentence and percent of 3+ syllable words."),
        ("SMOGIndex",
         "SMOG readability estimate based on polysyllabic word density across sentences."),
        ("SlowMin@190spm",
         "Reading time in minutes assuming 190 syllables per minute."),
        ("NormMin@230spm",
         "Reading time in minutes assuming 230 syllables per minute."),
        ("FastMin@275spm",
         "Reading time in minutes assuming 275 syllables per minute."),
        ("AvgSpeechSyllables",
         "Average syllables per speech block for the character."),
        ("AvgSpeechWords",
         "Average words per speech block for the character."),
        ("MaxSpeechSyllables",
         "Syllables in the character’s single longest speech block."),
        ("MaxSpeechWords",
         "Words in the character’s single longest speech block."),
        ("SyllablesPerWord",
         "Average syllables per word for the character (syllables ÷ words)."),
        ("PauseMin",
         "Estimated pause time in minutes from punctuation, using fixed weights for commas, dashes, ellipses, and sentence ends."),
        ("BreathGroups",
         "Number of breath groups, approximated by splitting on major punctuation and line breaks."),
        ("AvgSyllablesPerBreath",
         "Average syllables per breath group (a proxy for typical phrase length)."),
        ("MaxSyllablesPerBreath",
         "Maximum syllables in any breath group (proxy for the hardest single phrase)."),
        ("Choppiness",
         "Breath groups per speech block (BreathGroups ÷ Speeches). Higher means more stop-start delivery."),
        ("BreathDensityAvg",
         "Same as AvgSyllablesPerBreath, shown as a pacing-specific label."),
        ("BreathDensityMax",
         "Same as MaxSyllablesPerBreath, shown as a pacing-specific label."),
        ("Urgency",
         f"Fraction of sentences shorter than {SHORT_SENT_WORDS} words. Higher suggests more clipped or rapid exchanges."),
        ("Interruptibility",
         "Rate of dashes and ellipses per nonempty line. Higher suggests more hesitation or interruption-ready phrasing."),
        ("Blockiness",
         "Longest speech relative to typical speech (MaxSpeechWords ÷ AvgSpeechWords). Higher indicates monologues."),
        ("RhythmRegularity",
         "Standard deviation of breath-group syllable counts. Higher means more rhythmic variability."),
        ("HookFrequency",
         "Dashes, ellipses, and colons per 100 nonempty lines. Higher suggests more trailing or suspenseful line endings."),
        ("HeatIndex",
         "Exclamation marks per sentence. Higher suggests louder or more emotionally heated delivery."),
        ("Volatility",
         "Coefficient of variation of speech syllable lengths (std ÷ mean). Higher indicates more uneven speech size."),
    ]

    with stats_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "description"])
        w.writerows(rows)

# ---------------------------
# Main
# ---------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: wordcount.py DIR [output.csv]")
        sys.exit(1)

    indir = Path(sys.argv[1])
    outfile = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("wordcount.csv")

    texts: Dict[str, str] = {}
    data = []

    for txt in indir.glob("*.txt"):
        speaker = txt.stem
        text = txt.read_text(encoding="utf-8")
        texts[speaker] = text

        wc = count_words(text)
        syl = count_syllables(text)
        sentences = count_sentences(text)
        complex_wc = count_complex_words(text)

        fog = gunning_fog_index(wc, sentences, complex_wc)
        smog = smog_index(sentences, complex_wc)

        slow_min = syl / SLOW_SPM
        norm_min = syl / NORMAL_SPM
        fast_min = syl / FAST_SPM

        speeches, avg_ss, avg_sw, max_ss, max_sw = speech_stats(text)
        _speech_wcs, speech_scs = speech_length_lists(text)

        spw = syl / wc if wc else 0.0

        pause_ms = punctuation_pause_ms(text)
        pause_min = (pause_ms / 1000.0) / 60.0
        perf_min = norm_min + pause_min

        bg_n, bg_avg_syl, bg_max_syl, bg_std_syl = breath_group_stats(text)

        ellipses, dashes, colons, excls = punctuation_counts(text)
        lines_n = nonempty_line_count(text)

        choppiness = (bg_n / speeches) if speeches else 0.0
        breath_density_avg = bg_avg_syl
        breath_density_max = bg_max_syl
        urgency = urgency_index(text)
        interruptibility = ((dashes + ellipses) / lines_n) if lines_n else 0.0
        blockiness = (max_sw / avg_sw) if avg_sw else 0.0
        rhythm_regular = bg_std_syl
        hook_freq = ((dashes + ellipses + colons) / lines_n * 100.0) if lines_n else 0.0
        heat_index = (excls / sentences) if sentences else 0.0
        volatility = volatility_index(speech_scs)

        data.append((
            speaker,
            perf_min,
            syl,
            wc,
            sentences,
            speeches,
            fog,
            smog,
            slow_min, norm_min, fast_min,
            avg_ss, avg_sw, max_ss, max_sw,
            spw,
            pause_min,
            bg_n, bg_avg_syl, bg_max_syl,
            choppiness,
            breath_density_avg,
            breath_density_max,
            urgency,
            interruptibility,
            blockiness,
            rhythm_regular,
            hook_freq,
            heat_index,
            volatility
        ))

    if not data:
        print("No .txt files found.")
        sys.exit(1)

    # -------- Summary (your hybrid rules) --------
    n_chars = len(data)

    total_syl = sum(x[2] for x in data)
    total_words = sum(x[3] for x in data)
    total_sentences = sum(x[4] for x in data)
    total_speeches = sum(x[5] for x in data)

    all_text = "\n\n".join(texts.values())
    total_complex = count_complex_words(all_text)

    summary_fog = gunning_fog_index(total_words, total_sentences, total_complex)
    summary_smog = smog_index(total_sentences, total_complex)

    summary_slow_min = total_syl / SLOW_SPM
    summary_norm_min = total_syl / NORMAL_SPM
    summary_fast_min = total_syl / FAST_SPM

    summary_avg_ss = sum(x[11] for x in data) / n_chars
    summary_avg_sw = sum(x[12] for x in data) / n_chars
    summary_max_ss = sum(x[13] for x in data) / n_chars
    summary_max_sw = sum(x[14] for x in data) / n_chars

    summary_spw = total_syl / total_words if total_words else 0.0

    summary_pause_min = sum(x[16] for x in data)
    summary_perf_min = summary_norm_min + summary_pause_min

    summary_bg_n = sum(x[17] for x in data)
    summary_bg_avg_syl = sum(x[18] for x in data) / n_chars
    summary_bg_max_syl = sum(x[19] for x in data) / n_chars

    summary_choppiness       = sum(x[20] for x in data) / n_chars
    summary_bd_avg           = sum(x[21] for x in data) / n_chars
    summary_bd_max           = sum(x[22] for x in data) / n_chars
    summary_urgency          = sum(x[23] for x in data) / n_chars
    summary_interruptibility = sum(x[24] for x in data) / n_chars
    summary_blockiness       = sum(x[25] for x in data) / n_chars
    summary_rhythm_regular   = sum(x[26] for x in data) / n_chars
    summary_hook_freq        = sum(x[27] for x in data) / n_chars
    summary_heat_index       = sum(x[28] for x in data) / n_chars
    summary_volatility       = sum(x[29] for x in data) / n_chars

    # Sort by PerfMin descending
    data.sort(key=lambda x: x[1], reverse=True)

    with outfile.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "Character",
            "PerfMin",
            "Syllables",
            "WordCount",
            "Sentences",
            "Speeches",
            "FogIndex",
            "SMOGIndex",
            "SlowMin@190spm",
            "NormMin@230spm",
            "FastMin@275spm",
            "AvgSpeechSyllables",
            "AvgSpeechWords",
            "MaxSpeechSyllables",
            "MaxSpeechWords",
            "SyllablesPerWord",
            "PauseMin",
            "BreathGroups",
            "AvgSyllablesPerBreath",
            "MaxSyllablesPerBreath",
            "Choppiness",
            "BreathDensityAvg",
            "BreathDensityMax",
            "Urgency",
            "Interruptibility",
            "Blockiness",
            "RhythmRegularity",
            "HookFrequency",
            "HeatIndex",
            "Volatility",
        ])

        for row in data:
            (speaker, perf_min, syl, wc, sentences, speeches,
             fog, smog,
             slow_min, norm_min, fast_min,
             avg_ss, avg_sw, max_ss, max_sw,
             spw, pause_min,
             bg_n, bg_avg_syl, bg_max_syl,
             choppiness, bd_avg, bd_max, urgency, interruptibility,
             blockiness, rhythm_regular, hook_freq, heat_index, volatility) = row

            writer.writerow([
                speaker,
                f"{perf_min:.2f}",
                syl,
                wc,
                sentences,
                speeches,
                f"{fog:.2f}",
                f"{smog:.2f}",
                f"{slow_min:.2f}",
                f"{norm_min:.2f}",
                f"{fast_min:.2f}",
                f"{avg_ss:.2f}",
                f"{avg_sw:.2f}",
                max_ss,
                max_sw,
                f"{spw:.2f}",
                f"{pause_min:.2f}",
                bg_n,
                f"{bg_avg_syl:.2f}",
                bg_max_syl,
                f"{choppiness:.2f}",
                f"{bd_avg:.2f}",
                f"{bd_max:.2f}",
                f"{urgency:.2f}",
                f"{interruptibility:.2f}",
                f"{blockiness:.2f}",
                f"{rhythm_regular:.2f}",
                f"{hook_freq:.2f}",
                f"{heat_index:.2f}",
                f"{volatility:.2f}",
            ])

        writer.writerow([
            "Summary",
            f"{summary_perf_min:.2f}",
            total_syl,
            total_words,
            total_sentences,
            total_speeches,
            f"{summary_fog:.2f}",
            f"{summary_smog:.2f}",
            f"{summary_slow_min:.2f}",
            f"{summary_norm_min:.2f}",
            f"{summary_fast_min:.2f}",
            f"{summary_avg_ss:.2f}",
            f"{summary_avg_sw:.2f}",
            f"{summary_max_ss:.2f}",
            f"{summary_max_sw:.2f}",
            f"{summary_spw:.2f}",
            f"{summary_pause_min:.2f}",
            summary_bg_n,
            f"{summary_bg_avg_syl:.2f}",
            f"{summary_bg_max_syl:.2f}",
            f"{summary_choppiness:.2f}",
            f"{summary_bd_avg:.2f}",
            f"{summary_bd_max:.2f}",
            f"{summary_urgency:.2f}",
            f"{summary_interruptibility:.2f}",
            f"{summary_blockiness:.2f}",
            f"{summary_rhythm_regular:.2f}",
            f"{summary_hook_freq:.2f}",
            f"{summary_heat_index:.2f}",
            f"{summary_volatility:.2f}",
        ])

    # Write stats.csv in current directory
    write_stats_csv(Path("stats.csv"))

    print(f"Wrote {outfile} and stats.csv")

if __name__ == "__main__":
    main()
