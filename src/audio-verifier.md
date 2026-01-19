# Audio verifier and inline diffing

This document describes how the audio verifier works and how the inline text differ filters spurious differences. It points to the key classes so you can follow the implementation.

## Key classes and files

- `src/role_audio_verifier.py` (RoleAudioVerifier)
- `src/inline_text_differ.py` (InlineTextDiffer)
- `src/token_comparator.py` (TokenComparator)
- `src/homophone_matcher.py` (HomophoneMatcher)
- `src/equivalencies.py` (Equivalencies)
- `src/spelling_normalizer.py` (SpellingNormalizer)
- `src/audio_verifier_diff_builder.py` (AudioVerifierDiffBuilder)
- `src/unresolved_diffs.py` (UnresolvedDiffs)

## Audio verifier pipeline (RoleAudioVerifier)

1. Load the expected script segments for the role and build the ordered list of expected words per segment.
2. Load the role recording (WAV, mono, 16kHz) and transcribe the entire file using faster-whisper with VAD and word timestamps.
3. Normalize script words and recognized words for alignment: lowercase, strip punctuation, collapse whitespace, optionally remove filler words (configurable via `--remove-fillers`, default is keep fillers).
4. Align recognized words to script words using dynamic programming with match, skip audio, and skip text steps; the alignment uses rapidfuzz similarity scoring and is anchored to the script so it does not collapse after a single error.
5. Group matched words back into script segments and produce a result set with matched/missing/extra status, timestamps, and similarity.
6. Convert alignment results into human-facing diffs and Excel output with `AudioVerifierDiffBuilder`.

## Inline diffing pipeline (InlineTextDiffer)

Inline diffs are computed per matched segment by comparing the expected text from the script against the recognized text from audio. The differ keeps expected formatting while suppressing spurious differences.

1. Tokenize both strings into word, space, and punctuation tokens.
2. Normalize word tokens (TokenComparator.normalize_token): lowercase, convert curly apostrophes to straight, remove apostrophes, normalize numeric tokens (digits, ordinals, number words, roman numerals).
3. Encode normalized tokens into a compact string and run diff-match-patch to get a diff sequence.
4. Walk the diff sequence and build inline segments. Matches emit original expected tokens so punctuation and case are preserved in the inline diff text.
5. Inserts/deletes/replacements are formatted as inline diff markup: replacement `[heard/expected]`, insert (heard but not expected) `[+heard+]`, delete (expected but not heard) `[-expected-]`.
6. Windowed diffs are derived around diff regions for quick scanning.

## Spurious diff suppression

Inline diffing ignores or normalizes several kinds of differences so minor transcription variations do not surface as errors. These rules live primarily in `TokenComparator` and `Equivalencies`.

1. Punctuation is ignored; all punctuation tokens are treated as ignorable during diffing, including narration delimiters like `(_ ... _)`, dash runs, and quote styles, while expected punctuation is preserved in the output because matched tokens are copied from the expected text.
2. Case is ignored because word comparisons are lowercased.
3. Apostrophes are ignored; curly/straight apostrophes are normalized, then apostrophes are stripped, making `Here's` and `Heres` equivalent.
4. Numeric normalization unifies digits, ordinals, number words, and roman numerals to the same numeric token when possible; roman numerals are supported from I through C (1-100), and sequences such as "twenty first" are coalesced to "21".
5. Word joining/splitting is handled by treating two-word vs one-word forms as equivalent when the concatenation matches (`any one` == `anyone`, `vine wood` == `vinewood`).
6. Role and reader name relaxation compares known role/reader names with a fuzzy threshold (`name_similarity`) to reduce false diffs for proper nouns.
7. Spelling normalization (breame) treats British vs American spellings as equivalent when the variant map says they are (`honourable` == `honorable`).
8. User-defined equivalencies from `substitutions.yaml` can define global or per-segment variants using `@id`, and word-level equivalencies include a possessive fallback when both sides end with `s` (e.g., `spintho's` vs `spinto's`).
9. Homophone detection (HomophoneMatcher) treats words or short phrases with equivalent pronunciations as matches using CMUdict data, including number homophones like `to` vs `two` before numeric normalization.

## Substitutions and unresolved diffs

`Equivalencies` loads `plays/<play>/substitutions.yaml` and `plays/<play>/recordings/<ROLE>_substitutions.yaml` and merges them, supporting `equivalencies:` mappings and `ignorables:` phrases for suppressing extra-audio diffs. Unresolved word-level diffs (from matched segments only) are collected by `UnresolvedDiffs` and written to `build/<play>/<ROLE>_unresolved_diffs.yaml`, normalizing to word tokens with punctuation stripped, emitting flow-style lists (`key: [value]`), and quoting keys that contain spaces or punctuation other than `@` and `_`.

## Output artifacts

The verifier produces an in-memory alignment result with per-segment status, timestamps, and scores, an Excel report with per-segment rows and inline diff text, and a `*_unresolved_diffs.yaml` file with suggested equivalencies for unresolved word diffs.

## Libraries by step

- Transcription: `faster-whisper` provides word-level timestamps for the role audio.
- Alignment scoring: `rapidfuzz` computes similarity scores for word matching and name fuzzing.
- Inline diffing: `diff-match-patch` produces token-level diff sequences.
- Homophone detection: `cmudict` supplies pronunciations used by `HomophoneMatcher`.
- Spelling variants: `breame` provides British/American spelling equivalences via `SpellingNormalizer`.
- Output files: `openpyxl` writes the XLSX reports and `ruamel.yaml` writes `substitutions.yaml`/`*_unresolved_diffs.yaml`.
