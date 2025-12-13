The format of the script is a series of 'blocks'... each block is a one or more lines of text followed by a blank line: blank lines are block separators. The different types of blocks are defined in the following sections:

## Meta block
A meta block contains meta information that contains "front matter" for the script - `TITLE`, `SUBTITLE`, `AUTHOR`, `YEAR_OF_PUBLICATION`. The meta tag is all caps placed on the leading line between underscores and backtick delimiters, and the associated text is placed on the following line(s).

This is an example of a `TITLE` meta block with the text, `The People of the Black Circle`. 
```

_`TITLE`_:
The People of the Black Circle
```

BREAK blocks are a kind of meta block that represent a break in the text, typically indicated by a blank line with a series of `*` or `_` characters in the source text. Here's an example:

```
_`BREAK`_
       *       *       *       *       *
```

## Heading block
A heading block has an optional section number followed by a heading. It is enclosed in 

```
## [section_no: ]TITLE ##
```

## Speech block
A speech block is a block of text that is prefixed by a speaker. It contains one or more snippets of speech from that speaker, possibly interspersed with narration. Be careful to distinguish between single quotes used as quotes and as apostrophes for contractions etc. The name of the speaker is in all caps delimited by '_*' and '*_' and is placed on its own, leading line. Narration is delimited by `_(` and `)_`

```
_*YASMINA*_.
The priests and their clamor! _(she exclaimed.)_ They are no wiser than the leeches who are helpless!
```

## Narration
A narration block is unmarked text that does not contain any speech. 

```
She threw up her head in a gusty gesture of wrath and despair as the
thunder of the distant drums reached her ears.
```



