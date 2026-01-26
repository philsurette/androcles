# glossary
producer:
* the script that will split the recorded parts and blend themtogether to produce one audio file per act

## terms referring to the source text
script:
* the text of the source play we want to produce an audio recording of

section: 
* a major division of the script
* has a title
* Androcles and the Lion has four sections titled: "Introduction", "Prologue", "Act 1", "Act 2"

title:
* the text for the name of a section

character:
* a person who appears in the play 
* a character has a name "Androcles", "Megaera", "Lavinia", "a Christian"

narrator:
* a person who doesn't appear in the play, who gives stage directions

speaker:
* a character or the narrator

utterance:
* an uninterrupted stretch of speech made by a speaker

line:
* a block of text associated with a speaker
* it is a mix of stage directions and/or utterances 
* a line has "speaker" and "text" attributes
* e.g. "centurion: [shocked] Silence!" 
    * speaker: centurion
    * text: "[shocked] Silence!" 
        * includes the stage direction, 'shocked' 
        * includes the utterance, 'silence'
* e.g. "The Christians laugh again heartily" 
    * speaker: narrator
    * text: "The Christians laugh again heartily" 

text:
* a mix of stage directions and/or utterances
* e.g. this text has two utterances interrupted by a stage direction: "Yes: insult me, do. [ Rising ] Oh!"

stage direction:
* a line associated with the narrator
* a block of text describing stage direction that is not associated with a character's bit
* e.g. "The Christians laugh again heartily" 

argument: 
* all of the lines associated with a character in one section of the play
* e.g. Megaera has one argument in one section, the prologue, which consists of many lines; androcles has has arguments in all sections of the play 

role: 
* all of a character's arguments

argument index:
* a sequential numbering, starting at, of the lines associated with an argument

line index:
* a sequential numbering of the lines associated with a section

## terms referring to the inputs
section file:
* a source text file containing the title and lines associated with a section

track:
* a source audio file
* .wav format for fast processing
* tracks are named using the format "<type>_<discriminator>" where the type can be "title", "prefix", or, if neither of those, a character name

argument track: 
* an audio recording of an argment
* argument tracks include the character name and the section name in the filename
    * e.g. shaw_introduction.wav, direction_prologue.wav, megaera_prologue.wav, androcles_prologue.wav, androcles_act1.wav, androcles_act2.wav, a-christian_act1.wav
    * direction tracks are special in that there is no character associated with them... they contain only recorded directions

title track:
* an audio recording of a title
* title tracks are named after the section
    * e.g. title_prologue.wav

speech prefix track:
* an audio recording of the name of a character to be used as a prefix
* prefix tracks are named after the character
    * e.g. prefix_androcles.wav

## terms referring to the production process
bits:
* intermediate audio files used in production
* uses .wav format for quicker processing

speech bit:
* an audio file representing the text part of a recorded line
* the producer creates speech bits by splitting an argument track
* speech bits are named "<speaker>_<section>_~speech_<argument_index>.wav" 
* e.g. "androcles_act1_~speech-1.wav", "androcles_act1~speech-2.wav" etc

line bit:
* an audio file representing a recorded line
* line bits include an optional prefix track concatenated with a speech bit 
* they are named like this "<speaker>_<section>_~line_<line_index>.wav"
* e.g. "narrator_prologue~line_1.wav", "narrator_prologue~line_2.wav", "narrator_prologue~line_3.wav", "narrator_prologue~line_4.wav", "megaera_prologue~line_5.wav", "androcles_prologue_line_6.wav", "megaera_prologue~line_7.wav"

title bit:
* a copy of a title track
* named "<title>~title_<section_no>.wav

mix:
* a produced audio file ready for audiences
* mp3 format for distribution
* named "<title>~mix.mp3"

section mix:
* a produced section ready for listening
* named "<title>~mix_<section_no>.mp3"

play mix:
* a produced play ready for listening, the concatenation of all sections
* named "<title>~mix_<section_no>.mp3"

# formats

## section file format
The section file is named after the title of the section, "<title>~section.txt"
- e.g. "prologue~section.txt", "act1~section.txt"

The format is one line in the section file represents one line in the section. The files line numbers implicitly map to the line indexes

Each line is simply "<speaker_prefix>: <text>". The colon separator is always present but the speaker prefix is omitted for stage directions.
``` 
A CHRISTIAN: (cheerfully) God bless you, Captain.
THE CENTURION: (scandalised) Silence!
: The Captain, a patrician, handsome, about thirty-five, very cold and distinguished, very superior and authoritative, steps up on a stone seat at the west side of the square, behind the centurion, so as to dominate the others more effectually.
THE CAPTAIN: Centurion.
THE CENTURION: (standing at attention and saluting) Sir?
```

```
:A CHRISTIAN 
(cheerfully)
God bless you, Captain.
:THE CENTURION 
(scandalised)
Silence!
:
The Captain, a patrician, handsome, about thirty-five, very cold and distinguished, very superior and authoritative, steps up on a stone seat at the west side of the square, behind the centurion, so as to dominate the others more effectually.
:THE CAPTAIN 
Centurion.
:THE CENTURION 
(standing at attention and saluting)
Sir?
```

# programs

## editor
The editor converts a play source into the section file format.

## normalizer
Creates tracks from audacity files using a 1-1 mapping from .aup3 files to .wav files... also loudness nomralizes each argument file. 

## producer
The producer converts tracks into
- bits (intermediate audio outputs)
- mixes (final audo outputs)