# Column meanings
**Character**: Character name, taken from each .txt filename (stem).
**PerfMin**: Estimated total spoken time in minutes at the normal syllable rate, plus estimated punctuation pauses.
**Syllables**: Estimated syllables spoken by the character, using CMUdict when available and a vowel-group heuristic as fallback.
**WordCount**: Number of word tokens spoken by the character, based on a simple regex tokenizer.
**Sentences**: Count of sentence-like units, split on . ! ? or line breaks (ellipses ignored for splitting).
**Speeches**: Number of speech blocks the character has. A block is a paragraph separated by blank lines; if none, each nonempty line counts as a block.
**FogIndex**: Gunning Fog readability estimate using words per sentence and percent of 3+ syllable words.
**SMOGIndex**: SMOG readability estimate based on polysyllabic word density across sentences.
**SlowMin@190spm**: Reading time in minutes assuming 190 syllables per minute.
**NormMin@230spm**: Reading time in minutes assuming 230 syllables per minute.
**FastMin@275spm**: Reading time in minutes assuming 275 syllables per minute.
**AvgSpeechSyllables**: Average syllables per speech block for the character.
**AvgSpeechWords**: Average words per speech block for the character.
**MaxSpeechSyllables**: Syllables in the character’s single longest speech block.
**MaxSpeechWords**: Words in the character’s single longest speech block.
**SyllablesPerWord**: Average syllables per word for the character (syllables ÷ words).
**PauseMin**: Estimated pause time in minutes from punctuation, using fixed weights for commas, dashes, ellipses, and sentence ends.
**BreathGroups**: Number of breath groups, approximated by splitting on major punctuation and line breaks.
**AvgSyllablesPerBreath**: Average syllables per breath group (a proxy for typical phrase length).
**MaxSyllablesPerBreath**: Maximum syllables in any breath group (proxy for the hardest single phrase).
**Choppiness**: Breath groups per speech block (BreathGroups ÷ Speeches). Higher means more stop-start delivery.
**BreathDensityAvg**: Same as AvgSyllablesPerBreath, shown as a pacing-specific label.
**BreathDensityMax**: Same as MaxSyllablesPerBreath, shown as a pacing-specific label.
**Urgency**: Fraction of sentences shorter than 7 words. Higher suggests more clipped or rapid exchanges.
**Interruptibility**: Rate of dashes and ellipses per nonempty line. Higher suggests more hesitation or interruption-ready phrasing.
**Blockiness**: Longest speech relative to typical speech (MaxSpeechWords ÷ AvgSpeechWords). Higher indicates monologues.
**RhythmRegularity**: Standard deviation of breath-group syllable counts. Higher means more rhythmic variability.
**HookFrequency**: Dashes, ellipses, and colons per 100 nonempty lines. Higher suggests more trailing or suspenseful line endings.
**HeatIndex**: Exclamation marks per sentence. Higher suggests louder or more emotionally heated delivery.
**Volatility**: Coefficient of variation of speech syllable lengths (std ÷ mean). Higher indicates more uneven speech size.
