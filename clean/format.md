# Format
The format of the source script is a series of 'paragraphs'... each paragraph is a number of lines
of text followed by a blank line, which is the separator between paragraphs. There are the
following types of paragraph:
- Meta
- Block
- Staging
- Description
- Commentary

Blocks contain two types of text: speech and inline staging.

## Part Titles ##
These give a number to id and then the name of an part. They are enclosed in '##'s and have the format 'id: actname'

Example for id:1, part:"ACT I":
```
## 1: ACT I ##
```

## Meta
Text that is not part of the performance: front matter, act titles, etc. are in blocks
that are enclosed in '::'

Example:
```
:: Act I ::
```

## Block
A block of speech associated with a character, which may include inline stage directions.
The character name, followed by a period, and then a block of text.

Example of a simple block (without directions)
```
CHARACTER.
A martyr, Lavinia, is a fool.
Your death will prove nothing.
```
### Direction
stage directions that are included within a block are enclosed in `(_` and `_)`

Example of a Block with two Directions:
```
CHARACTER.
(_sardonically__)I say something and then (_turning to 
another character_) say something else.
```

## Staging
Top-level stage instructions that do not involve a character speaking. 
These are on their own paragraph, enclosed in '_'s.

Example
```
_The Ox Driver arrives, wielding a whip and flashing his
terrible, toothy smile._
```

## Description
A paragraph that describes the look and feel of the play. These are
largely about set design and atmosphere.

Example:
```
[There is a stump in the corner of the stage, and jungle cries are 
audible in the distance.]
```

## Commentary
This is a kind of meta information that might be included in 
a "director's cut" of the play.

It is enclosed in double curly braces '{{' and '}}'.

Example:
```
{{In this play I have sought to reflect the nature of the
human condition without resorting to overly infantilizing
the audience.}}
```