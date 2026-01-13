## Project context
This project is a python command-line application used for creating audio plays. The key functions are:
- convert the text of a play in a custom text format (defined src/format.md) into a set of 'role' markdown files, one per role in the play + Narrator, Caller, and Announcer roles
- take audio files that contain all audio segments (spoken lines) for each part of the play, separated by silence, split them into constituent identifiable files, and rejoin them together in their order of occurence in the play

## Coding style
Use python object-oriented code style: use classes rather than functions.

Default to using dataclasses whenever creating a new class.

Create one file per class.

## Defensive programming
Do not program defensively. If an unexpected condition occurs, raise an exception. In some cases I will change exceptions to logging. If you see an error condition being logged, do not change it back.

## logging
Each class that need to log python's logging mechanism (logging.getLogger(__name__)) for output. Do not use print() statements.